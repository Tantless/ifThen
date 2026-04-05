from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from .config import get_settings
from .models import MODEL_REGISTRY, FieldSpec, Model

_DB_FILENAME = "if_then_mvp.sqlite3"
_CONNECTION: sqlite3.Connection | None = None


def get_data_dir() -> Path:
    return get_settings().data_dir


def get_db_path() -> Path:
    return get_data_dir() / _DB_FILENAME


def _connect() -> sqlite3.Connection:
    path = get_db_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def _get_connection() -> sqlite3.Connection:
    global _CONNECTION
    if _CONNECTION is None:
        _CONNECTION = _connect()
    return _CONNECTION


def _serialize(field: FieldSpec, value: Any) -> Any:
    if value is None:
        return None
    if field.json:
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, bool):
        return int(value)
    return value


def _deserialize(field: FieldSpec, value: Any) -> Any:
    if value is None:
        return None
    if field.json:
        return json.loads(value)
    if field.sql_type == "INTEGER" and field.name != "id" and isinstance(value, int):
        return bool(value) if field.default in (True, False) else value
    return value


def _create_table_sql(model: type[Model]) -> str:
    column_sql = []
    for field in model.__fields__:
        parts = [field.name, field.sql_type]
        if field.primary_key:
            if field.name == "id":
                parts.append("PRIMARY KEY AUTOINCREMENT")
            else:
                parts.append("PRIMARY KEY")
        if not field.nullable and not field.primary_key:
            parts.append("NOT NULL")
        if field.unique:
            parts.append("UNIQUE")
        column_sql.append(" ".join(parts))
    return f"CREATE TABLE IF NOT EXISTS {model.__tablename__} ({', '.join(column_sql)})"


def init_db() -> None:
    connection = _get_connection()
    cursor = connection.cursor()
    for model in reversed(MODEL_REGISTRY):
        cursor.execute(f"DROP TABLE IF EXISTS {model.__tablename__}")
    for model in MODEL_REGISTRY:
        cursor.execute(_create_table_sql(model))
    connection.commit()


class Query:
    def __init__(self, connection: sqlite3.Connection, model: type[Model]):
        self._connection = connection
        self._model = model

    def count(self) -> int:
        row = self._connection.execute(f"SELECT COUNT(*) AS count FROM {self._model.__tablename__}").fetchone()
        return int(row["count"])

    def all(self) -> list[Model]:
        rows = self._connection.execute(f"SELECT * FROM {self._model.__tablename__}").fetchall()
        return [self._row_to_model(row) for row in rows]

    def first(self) -> Model | None:
        row = self._connection.execute(f"SELECT * FROM {self._model.__tablename__} LIMIT 1").fetchone()
        return None if row is None else self._row_to_model(row)

    def _row_to_model(self, row: sqlite3.Row) -> Model:
        payload = {}
        for field in self._model.__fields__:
            payload[field.name] = _deserialize(field, row[field.name])
        return self._model(**payload)


class Session:
    def __init__(self, connection: sqlite3.Connection):
        self._connection = connection
        self._pending: list[Model] = []

    def add(self, instance: Model) -> None:
        self._pending.append(instance)

    def flush(self) -> None:
        while self._pending:
            instance = self._pending.pop(0)
            self._insert(instance)

    def query(self, model: type[Model]) -> Query:
        return Query(self._connection, model)

    def get(self, model: type[Model], identity: Any) -> Model | None:
        pk = model.pk_field().name
        row = self._connection.execute(
            f"SELECT * FROM {model.__tablename__} WHERE {pk} = ?",
            (identity,),
        ).fetchone()
        if row is None:
            return None
        payload = {field.name: _deserialize(field, row[field.name]) for field in model.__fields__}
        return model(**payload)

    def commit(self) -> None:
        self.flush()
        self._connection.commit()

    def rollback(self) -> None:
        self._pending.clear()
        self._connection.rollback()

    def close(self) -> None:
        self._pending.clear()

    def _insert(self, instance: Model) -> None:
        model = type(instance)
        fields = []
        values = []
        pk_field = model.pk_field().name
        for field in model.__fields__:
            value = getattr(instance, field.name, field.default)
            if field.primary_key and field.name == "id" and value is None:
                continue
            fields.append(field.name)
            values.append(_serialize(field, value))
        placeholders = ", ".join(["?"] * len(fields))
        column_sql = ", ".join(fields)
        self._connection.execute(
            f"INSERT INTO {model.__tablename__} ({column_sql}) VALUES ({placeholders})",
            values,
        )
        if pk_field == "id":
            instance.id = self._connection.execute("SELECT last_insert_rowid()").fetchone()[0]


@contextmanager
def session_scope():
    session = Session(_get_connection())
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
