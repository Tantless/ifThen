from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from if_then_mvp.config import get_settings


class Base(DeclarativeBase):
    pass


_engine = None
_sessionmaker = None
_engine_path: Path | None = None


def _enable_sqlite_foreign_keys(dbapi_connection, connection_record) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.execute("PRAGMA busy_timeout=5000")
    cursor.close()


def build_engine():
    settings = get_settings()
    db_path = settings.data_dir / "db" / "if_then_mvp.sqlite3"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(
        f"sqlite:///{db_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )
    event.listen(engine, "connect", _enable_sqlite_foreign_keys)
    return engine


def get_engine():
    global _engine, _engine_path, _sessionmaker
    current_path = get_settings().data_dir / "db" / "if_then_mvp.sqlite3"
    if _engine is None or _engine_path != current_path:
        _engine = build_engine()
        _engine_path = current_path
        _sessionmaker = sessionmaker(bind=_engine, class_=Session, expire_on_commit=False)
    return _engine


def get_sessionmaker():
    get_engine()
    return _sessionmaker


def init_db() -> None:
    from . import models  # noqa: F401

    Base.metadata.create_all(bind=get_engine())


@contextmanager
def session_scope():
    session = get_sessionmaker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
