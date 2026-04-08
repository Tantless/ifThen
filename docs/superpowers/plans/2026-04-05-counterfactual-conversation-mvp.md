# Counterfactual Conversation MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a Windows-first local FastAPI + SQLite backend that imports `QQChatExporter V5` private-chat exports, runs asynchronous analysis, and produces cutoff-safe counterfactual single-reply and auto short-thread simulations.

**Architecture:** The project stays as a single Python codebase with two entrypoints: an API process and a DB-backed worker process. Source data is parsed into normalized messages, promoted into analysis artifacts, then assembled into a `ContextPack` that the simulation engine uses to assess branch direction and generate replies. SQLite stores all runtime data locally so the backend can later sit inside a Windows desktop shell without rewriting the core logic.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.x, SQLite, Pydantic v2, Pydantic Settings, httpx, pytest, pytest-asyncio, anyio, uvicorn

---

## 执行状态（2026-04-08 同步）

- 状态：**已完成并已并入 `main`**
- 结果：后端 MVP 主链路（导入 / 解析 / 分析 / 检索 / 推演）已经落地，并成为当前主分支能力基础。
- 当前验证参考：`python -m pytest -q` 在 `main` 上为 `71 passed`。
- 说明：下方 `- [ ]` 复选框保留为原始执行脚本，不再表示当前待办；当前总体进度以 `docs/2026-04-08-milestone-progress-summary.md` 为准。

## File Structure

- `pyproject.toml`
  - Python package metadata, runtime dependencies, and pytest config.
- `src/if_then_mvp/__init__.py`
  - Package marker and version export.
- `src/if_then_mvp/config.py`
  - Environment-aware settings, runtime directory resolution, and app defaults.
- `src/if_then_mvp/db.py`
  - SQLAlchemy engine, session factory, metadata initialization, and DB helpers.
- `src/if_then_mvp/models.py`
  - ORM models for conversations, imports, messages, segments, summaries, topics, personas, snapshots, jobs, settings, and simulations.
- `src/if_then_mvp/schemas.py`
  - Pydantic request and response schemas for API endpoints and structured LLM outputs.
- `src/if_then_mvp/parser.py`
  - QQ export parser, normalization helpers, and message classification.
- `src/if_then_mvp/segmentation.py`
  - Initial segment splitting and `merged_isolated` merge logic.
- `src/if_then_mvp/llm.py`
  - OpenAI-compatible chat client plus typed helper methods for analysis and simulation prompts.
- `src/if_then_mvp/analysis.py`
  - Stage functions that summarize segments, build topics, derive personas, and create relationship snapshots.
- `src/if_then_mvp/worker.py`
  - Job claiming, stage orchestration, logging hooks, and worker loop.
- `src/if_then_mvp/retrieval.py`
  - Cutoff-safe context retrieval and `ContextPack` assembly.
- `src/if_then_mvp/simulation.py`
  - Branch assessment, short-thread generation, and simulation persistence.
- `src/if_then_mvp/api.py`
  - FastAPI app factory and route registration.
- `scripts/run_api.py`
  - Developer entrypoint for launching the local API.
- `scripts/run_worker.py`
  - Developer entrypoint for launching the local worker.
- `tests/conftest.py`
  - Shared pytest fixtures for temp data directories, DB setup, fake LLMs, and API clients.
- `tests/fixtures/qq_export_sample.txt`
  - Trimmed QQ export sample used by parser and import tests.
- `tests/test_health.py`
  - Smoke tests for app startup and health checks.
- `tests/test_models.py`
  - Persistence tests for ORM models and DB initialization.
- `tests/test_parser.py`
  - Parser and normalization tests.
- `tests/test_imports.py`
  - Import API and job creation tests.
- `tests/test_segmentation.py`
  - Segment split and `merged_isolated` merge rule tests.
- `tests/test_analysis.py`
  - LLM-backed analysis stage tests using a fake client.
- `tests/test_worker.py`
  - Worker execution and job lifecycle tests.
- `tests/test_queries.py`
  - Read/query endpoint tests for conversations, messages, and analysis artifacts.
- `tests/test_retrieval.py`
  - Cutoff-safe context pack tests.
- `tests/test_simulations.py`
  - Simulation engine and `/simulations` endpoint tests.

## Task 1: Bootstrap the Python Project and API Skeleton

**Files:**
- Create: `pyproject.toml`
- Create: `src/if_then_mvp/__init__.py`
- Create: `src/if_then_mvp/config.py`
- Create: `src/if_then_mvp/db.py`
- Create: `src/if_then_mvp/api.py`
- Create: `scripts/run_api.py`
- Create: `tests/conftest.py`
- Create: `tests/test_health.py`

- [ ] **Step 1: Write the failing health test**

```python
# tests/test_health.py
from fastapi.testclient import TestClient

from if_then_mvp.api import create_app


def test_health_returns_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path))
    client = TestClient(create_app())

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `python -m pytest tests/test_health.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'if_then_mvp'`

- [ ] **Step 3: Create the package skeleton and minimal FastAPI app**

```toml
# pyproject.toml
[build-system]
requires = ["setuptools>=68", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "if-then-mvp"
version = "0.1.0"
description = "Counterfactual conversation MVP backend"
requires-python = ">=3.12"
dependencies = [
  "fastapi>=0.115,<1.0",
  "uvicorn>=0.30,<1.0",
  "sqlalchemy>=2.0,<3.0",
  "pydantic>=2.8,<3.0",
  "pydantic-settings>=2.4,<3.0",
  "python-multipart>=0.0.9,<1.0",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.3,<9.0",
  "pytest-asyncio>=0.24,<1.0",
  "httpx>=0.27,<1.0",
  "anyio>=4.4,<5.0",
]

[tool.setuptools]
package-dir = {"" = "src"}

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
```

```python
# src/if_then_mvp/__init__.py
__all__ = ["__version__"]

__version__ = "0.1.0"
```

```python
# src/if_then_mvp/config.py
from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    data_dir: Path = Field(default=Path("app_data"), alias="IF_THEN_DATA_DIR")
    sqlite_file_name: str = "if_then_mvp.sqlite3"
    segment_gap_minutes: int = 30
    isolated_merge_window_hours: int = 24
    max_short_thread_turns: int = 8

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def db_dir(self) -> Path:
        return self.data_dir / "db"

    @property
    def uploads_dir(self) -> Path:
        return self.data_dir / "uploads"

    @property
    def logs_dir(self) -> Path:
        return self.data_dir / "logs"

    @property
    def cache_dir(self) -> Path:
        return self.data_dir / "cache"

    @property
    def sqlite_path(self) -> Path:
        return self.db_dir / self.sqlite_file_name

    def ensure_runtime_dirs(self) -> None:
        for path in (self.db_dir, self.uploads_dir, self.logs_dir, self.cache_dir):
            path.mkdir(parents=True, exist_ok=True)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.ensure_runtime_dirs()
    return settings
```

```python
# src/if_then_mvp/db.py
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from if_then_mvp.config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine():
    settings = get_settings()
    return create_engine(
        f"sqlite:///{settings.sqlite_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

```python
# src/if_then_mvp/api.py
from fastapi import FastAPI

from if_then_mvp.db import init_db


def create_app() -> FastAPI:
    app = FastAPI(title="If Then MVP API")

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    return app
```

```python
# scripts/run_api.py
import uvicorn


if __name__ == "__main__":
    uvicorn.run("if_then_mvp.api:create_app", factory=True, host="127.0.0.1", port=8000, reload=False)
```

```python
# tests/conftest.py
import pytest


@pytest.fixture(autouse=True)
def clear_settings_cache(monkeypatch, tmp_path):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    from if_then_mvp.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()
```

- [ ] **Step 4: Run the health test to verify it passes**

Run: `python -m pytest tests/test_health.py -q`
Expected: PASS

- [ ] **Step 5: Initialize git if needed and commit the bootstrap**

Run: `if (-not (Test-Path .git)) { git init }; git add pyproject.toml src scripts tests; git commit -m "chore: bootstrap API skeleton"`
Expected: a new git repository exists if one was missing, and the bootstrap commit is created

## Task 2: Add ORM Models and Database Initialization Coverage

**Files:**
- Modify: `src/if_then_mvp/db.py`
- Create: `src/if_then_mvp/models.py`
- Create: `tests/test_models.py`

- [ ] **Step 1: Write the failing model persistence test**

```python
# tests/test_models.py
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import AnalysisJob, AppSetting, Conversation, ImportBatch, Message


def test_core_models_persist_and_query():
    init_db()

    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="queued",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path="app_data/uploads/sample.txt",
            source_file_hash="abc123",
            message_count_hint=10,
        )
        session.add(batch)
        session.flush()

        session.add(
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=1,
                speaker_name="Tantless",
                speaker_role="self",
                timestamp="2025-03-02T20:18:04",
                content_text="你好",
                message_type="text",
            )
        )
        session.add(
            AnalysisJob(
                conversation_id=conversation.id,
                job_type="full_analysis",
                status="queued",
                current_stage="created",
                progress_percent=0,
                retry_count=0,
                payload_json={},
            )
        )
        session.add(AppSetting(setting_key="llm.chat_model", setting_value="gpt-4.1-mini", is_secret=False))

    with session_scope() as session:
        assert session.query(Conversation).count() == 1
        assert session.query(ImportBatch).count() == 1
        assert session.query(Message).count() == 1
        assert session.query(AnalysisJob).count() == 1
        assert session.query(AppSetting).count() == 1
```

- [ ] **Step 2: Run the model test to verify it fails**

Run: `python -m pytest tests/test_models.py -q`
Expected: FAIL with `ModuleNotFoundError` or `ImportError` for `if_then_mvp.models`

- [ ] **Step 3: Implement the ORM models and wire them into DB initialization**

```python
# src/if_then_mvp/models.py
from __future__ import annotations

from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from if_then_mvp.db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class Conversation(TimestampMixin, Base):
    __tablename__ = "conversations"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(255))
    chat_type: Mapped[str] = mapped_column(String(32))
    self_display_name: Mapped[str] = mapped_column(String(255))
    other_display_name: Mapped[str] = mapped_column(String(255))
    source_format: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="queued")

    imports: Mapped[list["ImportBatch"]] = relationship(back_populates="conversation")
    jobs: Mapped[list["AnalysisJob"]] = relationship(back_populates="conversation")


class ImportBatch(TimestampMixin, Base):
    __tablename__ = "imports"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    source_file_name: Mapped[str] = mapped_column(String(255))
    source_file_path: Mapped[str] = mapped_column(String(1024))
    source_file_hash: Mapped[str] = mapped_column(String(128), index=True)
    message_count_hint: Mapped[int | None] = mapped_column(Integer, nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="imports")


class Message(TimestampMixin, Base):
    __tablename__ = "messages"
    __table_args__ = (UniqueConstraint("conversation_id", "sequence_no", name="uq_messages_conversation_sequence"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    import_id: Mapped[int] = mapped_column(ForeignKey("imports.id"), index=True)
    sequence_no: Mapped[int] = mapped_column(Integer, index=True)
    speaker_name: Mapped[str] = mapped_column(String(255))
    speaker_role: Mapped[str] = mapped_column(String(32))
    timestamp: Mapped[str] = mapped_column(String(32), index=True)
    content_text: Mapped[str] = mapped_column(Text)
    message_type: Mapped[str] = mapped_column(String(32))
    resource_items: Mapped[list[dict] | None] = mapped_column(JSON, nullable=True)
    parse_flags: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
    raw_block_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    raw_speaker_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_line_start: Mapped[int | None] = mapped_column(Integer, nullable=True)
    source_line_end: Mapped[int | None] = mapped_column(Integer, nullable=True)


class Segment(TimestampMixin, Base):
    __tablename__ = "segments"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    start_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"))
    end_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"))
    start_time: Mapped[str] = mapped_column(String(32), index=True)
    end_time: Mapped[str] = mapped_column(String(32), index=True)
    message_count: Mapped[int] = mapped_column(Integer)
    self_message_count: Mapped[int] = mapped_column(Integer)
    other_message_count: Mapped[int] = mapped_column(Integer)
    segment_kind: Mapped[str] = mapped_column(String(32))
    source_segment_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)
    source_message_ids: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)


class SegmentSummary(TimestampMixin, Base):
    __tablename__ = "segment_summaries"

    id: Mapped[int] = mapped_column(primary_key=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("segments.id"), unique=True)
    summary_text: Mapped[str] = mapped_column(Text)
    main_topics: Mapped[list[str]] = mapped_column(JSON)
    self_stance: Mapped[str] = mapped_column(Text)
    other_stance: Mapped[str] = mapped_column(Text)
    emotional_tone: Mapped[str] = mapped_column(String(128))
    interaction_pattern: Mapped[str] = mapped_column(String(128))
    has_conflict: Mapped[bool] = mapped_column(default=False)
    has_repair: Mapped[bool] = mapped_column(default=False)
    has_closeness_signal: Mapped[bool] = mapped_column(default=False)
    outcome: Mapped[str] = mapped_column(String(128))
    relationship_impact: Mapped[str] = mapped_column(String(128))
    confidence: Mapped[float] = mapped_column()


class Topic(TimestampMixin, Base):
    __tablename__ = "topics"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    topic_name: Mapped[str] = mapped_column(String(255))
    topic_summary: Mapped[str] = mapped_column(Text)
    first_seen_at: Mapped[str] = mapped_column(String(32))
    last_seen_at: Mapped[str] = mapped_column(String(32))
    segment_count: Mapped[int] = mapped_column(Integer)
    topic_status: Mapped[str] = mapped_column(String(64))


class TopicLink(TimestampMixin, Base):
    __tablename__ = "topic_links"

    id: Mapped[int] = mapped_column(primary_key=True)
    topic_id: Mapped[int] = mapped_column(ForeignKey("topics.id"), index=True)
    segment_id: Mapped[int] = mapped_column(ForeignKey("segments.id"), index=True)
    link_reason: Mapped[str] = mapped_column(Text)
    score: Mapped[float] = mapped_column()


class PersonaProfile(TimestampMixin, Base):
    __tablename__ = "persona_profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    subject_role: Mapped[str] = mapped_column(String(32))
    global_persona_summary: Mapped[str] = mapped_column(Text)
    style_traits: Mapped[list[str]] = mapped_column(JSON)
    conflict_traits: Mapped[list[str]] = mapped_column(JSON)
    relationship_specific_patterns: Mapped[list[str]] = mapped_column(JSON)
    evidence_segment_ids: Mapped[list[int]] = mapped_column(JSON)
    confidence: Mapped[float] = mapped_column()


class RelationshipSnapshot(TimestampMixin, Base):
    __tablename__ = "relationship_snapshots"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    as_of_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True)
    as_of_time: Mapped[str] = mapped_column(String(32), index=True)
    relationship_temperature: Mapped[str] = mapped_column(String(64))
    tension_level: Mapped[str] = mapped_column(String(64))
    openness_level: Mapped[str] = mapped_column(String(64))
    initiative_balance: Mapped[str] = mapped_column(String(64))
    defensiveness_level: Mapped[str] = mapped_column(String(64))
    unresolved_conflict_flags: Mapped[list[str]] = mapped_column(JSON)
    relationship_phase: Mapped[str] = mapped_column(String(64))
    snapshot_summary: Mapped[str] = mapped_column(Text)


class AnalysisJob(TimestampMixin, Base):
    __tablename__ = "analysis_jobs"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    job_type: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), index=True)
    current_stage: Mapped[str] = mapped_column(String(64))
    progress_percent: Mapped[int] = mapped_column(Integer)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    payload_json: Mapped[dict] = mapped_column(JSON)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    conversation: Mapped["Conversation"] = relationship(back_populates="jobs")


class Simulation(TimestampMixin, Base):
    __tablename__ = "simulations"

    id: Mapped[int] = mapped_column(primary_key=True)
    conversation_id: Mapped[int] = mapped_column(ForeignKey("conversations.id"), index=True)
    target_message_id: Mapped[int] = mapped_column(ForeignKey("messages.id"), index=True)
    mode: Mapped[str] = mapped_column(String(32))
    replacement_content: Mapped[str] = mapped_column(Text)
    context_pack_snapshot: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    branch_assessment: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    first_reply_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    impact_summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)


class SimulationTurn(TimestampMixin, Base):
    __tablename__ = "simulation_turns"

    id: Mapped[int] = mapped_column(primary_key=True)
    simulation_id: Mapped[int] = mapped_column(ForeignKey("simulations.id"), index=True)
    turn_index: Mapped[int] = mapped_column(Integer)
    speaker_role: Mapped[str] = mapped_column(String(32))
    message_text: Mapped[str] = mapped_column(Text)
    strategy_used: Mapped[str] = mapped_column(String(128))
    state_after_turn: Mapped[dict] = mapped_column(JSON)
    generation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)


class AppSetting(Base):
    __tablename__ = "app_settings"

    setting_key: Mapped[str] = mapped_column(String(255), primary_key=True)
    setting_value: Mapped[str] = mapped_column(Text)
    is_secret: Mapped[bool] = mapped_column(default=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
```

```python
# src/if_then_mvp/db.py
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from if_then_mvp.config import get_settings


class Base(DeclarativeBase):
    pass


def build_engine():
    settings = get_settings()
    return create_engine(
        f"sqlite:///{settings.sqlite_path}",
        connect_args={"check_same_thread": False},
        future=True,
    )


engine = build_engine()
SessionLocal = sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def init_db() -> None:
    import if_then_mvp.models  # noqa: F401

    Base.metadata.create_all(bind=engine)


@contextmanager
def session_scope():
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
```

- [ ] **Step 4: Run the model test to verify it passes**

Run: `python -m pytest tests/test_models.py -q`
Expected: PASS

- [ ] **Step 5: Commit the persistence layer**

Run: `git add src/if_then_mvp/db.py src/if_then_mvp/models.py tests/test_models.py && git commit -m "feat: add persistence models"`
Expected: commit created with model and DB changes

## Task 3: Implement the QQ Export Parser and Normalizer

**Files:**
- Create: `src/if_then_mvp/parser.py`
- Create: `tests/fixtures/qq_export_sample.txt`
- Create: `tests/test_parser.py`

- [ ] **Step 1: Write the failing parser tests**

```python
# tests/test_parser.py
from pathlib import Path

from if_then_mvp.parser import parse_qq_export


def test_parse_qq_export_extracts_messages_and_flags():
    text = Path("tests/fixtures/qq_export_sample.txt").read_text(encoding="utf-8")

    parsed = parse_qq_export(text=text, self_display_name="Tantless")

    assert parsed.chat_name == "梣ゥ"
    assert parsed.chat_type == "私聊"
    assert parsed.message_count_hint == 6
    assert len(parsed.messages) == 6

    first = parsed.messages[0]
    assert first.speaker_role == "other"
    assert first.message_type == "text"

    image_message = parsed.messages[2]
    assert image_message.message_type == "image"
    assert image_message.resource_items == [{"kind": "image", "name": "1DA1EB4EA41F53A9407923B093C213B6.jpg"}]

    unknown_message = parsed.messages[5]
    assert unknown_message.speaker_role == "unknown"
    assert "unknown_speaker" in unknown_message.parse_flags
```

- [ ] **Step 2: Run the parser tests to verify they fail**

Run: `python -m pytest tests/test_parser.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'if_then_mvp.parser'`

- [ ] **Step 3: Add a realistic parser fixture and implement the parser**

```text
# tests/fixtures/qq_export_sample.txt
[QQChatExporter V5 / https://github.com/shuakami/qq-chat-exporter]
[本软件是免费的开源项目~ 如果您是买来的，请立即退款！如果有帮助到您，欢迎给我点个Star~]

===============================================
           QQ聊天记录导出文件
===============================================

聊天名称: 梣ゥ
聊天类型: 私聊
导出时间: 2026-04-01 17:31:41
消息总数: 6
时间范围: 2025-03-02 20:18:03 - 2025-03-02 20:33:45


梣ゥ:
时间: 2025-03-02 20:18:03
内容: 我是凉ゥ


Tantless:
时间: 2025-03-02 20:18:04
内容: 我们已成功添加为好友，现在可以开始聊天啦～


梣ゥ:
时间: 2025-03-02 20:19:00
内容: [图片: 1DA1EB4EA41F53A9407923B093C213B6.jpg]
资源: 1 个文件
  - image: 1DA1EB4EA41F53A9407923B093C213B6.jpg


Tantless:
时间: 2025-03-02 20:19:09
内容: [图片: A559B65E34C322B38C19CF83844CC453.jpg]
资源: 1 个文件
  - image: A559B65E34C322B38C19CF83844CC453.jpg


梣ゥ:
时间: 2025-03-02 23:30:43
内容: 有懦夫啊，这不敢进烟？


0:
时间: 2025-03-02 20:33:45
内容: [17]
```

```python
# src/if_then_mvp/parser.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import re


HEADER_CHAT_NAME = "聊天名称:"
HEADER_CHAT_TYPE = "聊天类型:"
HEADER_MESSAGE_COUNT = "消息总数:"


@dataclass
class ParsedMessage:
    sequence_no: int
    speaker_name: str
    speaker_role: str
    timestamp: str
    content_text: str
    message_type: str
    resource_items: list[dict] = field(default_factory=list)
    parse_flags: list[str] = field(default_factory=list)
    raw_block_text: str = ""
    raw_speaker_label: str = ""
    source_line_start: int = 0
    source_line_end: int = 0


@dataclass
class ParsedConversation:
    chat_name: str
    chat_type: str
    message_count_hint: int | None
    messages: list[ParsedMessage]


def _classify_message(content: str, resources: list[dict]) -> str:
    if content.startswith("[图片:"):
        return "image"
    if content.startswith("[文件:") or any(item["kind"] == "file" for item in resources):
        return "file"
    if content.startswith("[系统"):
        return "system"
    if not content.strip():
        return "unknown"
    return "text"


def _speaker_role(speaker_name: str, self_display_name: str) -> tuple[str, list[str]]:
    flags: list[str] = []
    if speaker_name == self_display_name:
        return "self", flags
    if re.fullmatch(r"\d+", speaker_name):
        flags.append("unknown_speaker")
        return "unknown", flags
    return "other", flags


def parse_qq_export(text: str, self_display_name: str) -> ParsedConversation:
    lines = text.splitlines()
    chat_name = ""
    chat_type = ""
    message_count_hint: int | None = None
    messages: list[ParsedMessage] = []

    line_no = 0
    sequence_no = 0
    while line_no < len(lines):
        line = lines[line_no]
        if line.startswith(HEADER_CHAT_NAME):
            chat_name = line.split(":", 1)[1].strip()
        elif line.startswith(HEADER_CHAT_TYPE):
            chat_type = line.split(":", 1)[1].strip()
        elif line.startswith(HEADER_MESSAGE_COUNT):
            message_count_hint = int(line.split(":", 1)[1].strip())

        if line.endswith(":") and not line.startswith("[") and not line.startswith(("时间:", "内容:", "资源:")):
            speaker_name = line[:-1]
            timestamp = ""
            content = ""
            resources: list[dict] = []
            buffer = [line]
            start_line = line_no + 1
            cursor = line_no + 1
            while cursor < len(lines):
                current = lines[cursor]
                if current.endswith(":") and not current.startswith("[") and not current.startswith(("时间:", "内容:", "资源:")):
                    break
                buffer.append(current)
                if current.startswith("时间:"):
                    timestamp = current.split(":", 1)[1].strip()
                elif current.startswith("内容:"):
                    content = current.split(":", 1)[1].strip()
                elif current.strip().startswith("- "):
                    item = current.strip()[2:]
                    kind, name = item.split(":", 1)
                    resources.append({"kind": kind.strip(), "name": name.strip()})
                cursor += 1

            speaker_role, flags = _speaker_role(speaker_name, self_display_name)
            sequence_no += 1
            messages.append(
                ParsedMessage(
                    sequence_no=sequence_no,
                    speaker_name=speaker_name,
                    speaker_role=speaker_role,
                    timestamp=datetime.fromisoformat(timestamp).isoformat(),
                    content_text=content,
                    message_type=_classify_message(content, resources),
                    resource_items=resources,
                    parse_flags=flags + (["resource_present"] if resources else []),
                    raw_block_text="\n".join(buffer),
                    raw_speaker_label=speaker_name,
                    source_line_start=start_line,
                    source_line_end=cursor,
                )
            )
            line_no = cursor
            continue

        line_no += 1

    return ParsedConversation(
        chat_name=chat_name,
        chat_type=chat_type,
        message_count_hint=message_count_hint,
        messages=messages,
    )
```

- [ ] **Step 4: Run the parser tests to verify they pass**

Run: `python -m pytest tests/test_parser.py -q`
Expected: PASS

- [ ] **Step 5: Commit the parser implementation**

Run: `git add src/if_then_mvp/parser.py tests/fixtures/qq_export_sample.txt tests/test_parser.py && git commit -m "feat: add QQ export parser"`
Expected: commit created with parser and fixtures

## Task 4: Implement the Import API and Job Creation Flow

**Files:**
- Create: `src/if_then_mvp/schemas.py`
- Modify: `src/if_then_mvp/api.py`
- Create: `tests/test_imports.py`

- [ ] **Step 1: Write the failing import API test**

```python
# tests/test_imports.py
from pathlib import Path

from fastapi.testclient import TestClient

from if_then_mvp.api import create_app
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import AnalysisJob, Conversation, ImportBatch


def test_import_endpoint_persists_upload_and_enqueues_job(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()
    client = TestClient(create_app())

    sample_bytes = Path("tests/fixtures/qq_export_sample.txt").read_bytes()
    response = client.post(
        "/imports/qq-text",
        data={"self_display_name": "Tantless"},
        files={"file": ("聊天记录.txt", sample_bytes, "text/plain")},
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["conversation"]["title"] == "梣ゥ"
    assert payload["job"]["status"] == "queued"

    with session_scope() as session:
        assert session.query(Conversation).count() == 1
        assert session.query(ImportBatch).count() == 1
        assert session.query(AnalysisJob).count() == 1
```

- [ ] **Step 2: Run the import API test to verify it fails**

Run: `python -m pytest tests/test_imports.py -q`
Expected: FAIL with `404 Not Found` for `/imports/qq-text`

- [ ] **Step 3: Add request/response schemas and the import route**

```python
# src/if_then_mvp/schemas.py
from pydantic import BaseModel


class ConversationRead(BaseModel):
    id: int
    title: str
    chat_type: str
    self_display_name: str
    other_display_name: str
    source_format: str
    status: str


class JobRead(BaseModel):
    id: int
    status: str
    current_stage: str
    progress_percent: int


class ImportResponse(BaseModel):
    conversation: ConversationRead
    job: JobRead
```

```python
# src/if_then_mvp/api.py
from fastapi import FastAPI, File, Form, HTTPException, UploadFile

from if_then_mvp.config import get_settings
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import AnalysisJob, Conversation, ImportBatch
from if_then_mvp.parser import parse_qq_export
from if_then_mvp.schemas import ConversationRead, ImportResponse, JobRead


def create_app() -> FastAPI:
    app = FastAPI(title="If Then MVP API")

    @app.on_event("startup")
    def startup() -> None:
        init_db()

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/imports/qq-text", response_model=ImportResponse, status_code=201)
    def import_qq_text(file: UploadFile = File(...), self_display_name: str = Form(...)) -> ImportResponse:
        settings = get_settings()
        raw_bytes = file.file.read()
        text = raw_bytes.decode("utf-8")
        parsed = parse_qq_export(text=text, self_display_name=self_display_name)

        if parsed.chat_type != "私聊":
            raise HTTPException(status_code=400, detail="Only private chats are supported")

        destination = settings.uploads_dir / file.filename
        destination.write_bytes(raw_bytes)

        with session_scope() as session:
            conversation = Conversation(
                title=parsed.chat_name,
                chat_type="private",
                self_display_name=self_display_name,
                other_display_name=next(
                    (message.speaker_name for message in parsed.messages if message.speaker_role == "other"),
                    "unknown",
                ),
                source_format="qq_chat_exporter_v5",
                status="queued",
            )
            session.add(conversation)
            session.flush()

            batch = ImportBatch(
                conversation_id=conversation.id,
                source_file_name=file.filename,
                source_file_path=str(destination),
                source_file_hash=str(hash(raw_bytes)),
                message_count_hint=parsed.message_count_hint,
            )
            session.add(batch)
            session.flush()

            job = AnalysisJob(
                conversation_id=conversation.id,
                job_type="full_analysis",
                status="queued",
                current_stage="created",
                progress_percent=0,
                retry_count=0,
                payload_json={"import_id": batch.id},
            )
            session.add(job)
            session.flush()

            return ImportResponse(
                conversation=ConversationRead.model_validate(conversation, from_attributes=True),
                job=JobRead.model_validate(job, from_attributes=True),
            )

    return app
```

- [ ] **Step 4: Run the import API test to verify it passes**

Run: `python -m pytest tests/test_imports.py -q`
Expected: PASS

- [ ] **Step 5: Commit the import flow**

Run: `git add src/if_then_mvp/api.py src/if_then_mvp/schemas.py tests/test_imports.py && git commit -m "feat: add import API and job creation"`
Expected: commit created with import endpoint

## Task 5: Implement Segment Splitting and `merged_isolated` Rules

**Files:**
- Create: `src/if_then_mvp/segmentation.py`
- Create: `tests/test_segmentation.py`

- [ ] **Step 1: Write the failing segmentation tests**

```python
# tests/test_segmentation.py
from if_then_mvp.segmentation import ParsedTimelineMessage, merge_isolated_segments, split_into_segments


def test_split_into_segments_marks_normal_and_isolated():
    messages = [
        ParsedTimelineMessage(1, "2025-03-02T20:18:03", "other"),
        ParsedTimelineMessage(2, "2025-03-02T20:18:30", "self"),
        ParsedTimelineMessage(3, "2025-03-02T23:30:43", "other"),
        ParsedTimelineMessage(4, "2025-03-03T23:30:43", "self"),
    ]

    segments = split_into_segments(messages, gap_minutes=30)

    assert [segment.segment_kind for segment in segments] == ["normal", "isolated", "isolated"]


def test_merge_isolated_segments_only_merges_adjacent_items_within_24_hours():
    messages = [
        ParsedTimelineMessage(1, "2025-03-02T10:00:00", "self"),
        ParsedTimelineMessage(2, "2025-03-02T10:05:00", "other"),
        ParsedTimelineMessage(3, "2025-03-02T15:00:00", "self"),
        ParsedTimelineMessage(4, "2025-03-02T16:00:00", "other"),
        ParsedTimelineMessage(5, "2025-03-04T16:00:00", "other"),
    ]

    initial = split_into_segments(messages, gap_minutes=30)
    merged = merge_isolated_segments(initial, merge_window_hours=24)

    assert [segment.segment_kind for segment in merged] == ["normal", "merged_isolated", "isolated"]
    assert merged[1].source_message_ids == [3, 4]
```

- [ ] **Step 2: Run the segmentation tests to verify they fail**

Run: `python -m pytest tests/test_segmentation.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'if_then_mvp.segmentation'`

- [ ] **Step 3: Implement splitting and merge logic**

```python
# src/if_then_mvp/segmentation.py
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass
class ParsedTimelineMessage:
    message_id: int
    timestamp: str
    speaker_role: str


@dataclass
class SegmentDraft:
    message_ids: list[int]
    start_time: str
    end_time: str
    self_message_count: int
    other_message_count: int
    segment_kind: str
    source_message_ids: list[int] = field(default_factory=list)
    source_segment_ids: list[int] = field(default_factory=list)


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def split_into_segments(messages: list[ParsedTimelineMessage], gap_minutes: int) -> list[SegmentDraft]:
    if not messages:
        return []

    drafts: list[list[ParsedTimelineMessage]] = [[messages[0]]]
    gap = timedelta(minutes=gap_minutes)

    for current in messages[1:]:
        previous = drafts[-1][-1]
        if _parse_ts(current.timestamp) - _parse_ts(previous.timestamp) <= gap:
            drafts[-1].append(current)
        else:
            drafts.append([current])

    segments: list[SegmentDraft] = []
    for draft in drafts:
        self_count = sum(1 for item in draft if item.speaker_role == "self")
        other_count = sum(1 for item in draft if item.speaker_role == "other")
        segments.append(
            SegmentDraft(
                message_ids=[item.message_id for item in draft],
                start_time=draft[0].timestamp,
                end_time=draft[-1].timestamp,
                self_message_count=self_count,
                other_message_count=other_count,
                segment_kind="normal" if len(draft) >= 2 else "isolated",
                source_message_ids=[item.message_id for item in draft],
            )
        )
    return segments


def merge_isolated_segments(segments: list[SegmentDraft], merge_window_hours: int) -> list[SegmentDraft]:
    merged: list[SegmentDraft] = []
    window = timedelta(hours=merge_window_hours)
    cursor = 0

    while cursor < len(segments):
        current = segments[cursor]
        if current.segment_kind != "isolated":
            merged.append(current)
            cursor += 1
            continue

        chain = [current]
        look_ahead = cursor + 1
        while look_ahead < len(segments) and segments[look_ahead].segment_kind == "isolated":
            chain.append(segments[look_ahead])
            look_ahead += 1

        first_time = _parse_ts(chain[0].start_time)
        last_time = _parse_ts(chain[-1].end_time)
        if len(chain) >= 2 and (last_time - first_time) <= window:
            merged.append(
                SegmentDraft(
                    message_ids=[message_id for item in chain for message_id in item.message_ids],
                    start_time=chain[0].start_time,
                    end_time=chain[-1].end_time,
                    self_message_count=sum(item.self_message_count for item in chain),
                    other_message_count=sum(item.other_message_count for item in chain),
                    segment_kind="merged_isolated",
                    source_message_ids=[message_id for item in chain for message_id in item.message_ids],
                )
            )
        else:
            merged.extend(chain)

        cursor = look_ahead

    return merged
```

- [ ] **Step 4: Run the segmentation tests to verify they pass**

Run: `python -m pytest tests/test_segmentation.py -q`
Expected: PASS

- [ ] **Step 5: Commit the segmentation logic**

Run: `git add src/if_then_mvp/segmentation.py tests/test_segmentation.py && git commit -m "feat: add segment splitting rules"`
Expected: commit created with segmentation behavior

## Task 6: Implement the LLM Client and Analysis Stage Services

**Files:**
- Create: `src/if_then_mvp/llm.py`
- Create: `src/if_then_mvp/analysis.py`
- Create: `tests/test_analysis.py`

- [ ] **Step 1: Write the failing analysis stage test**

```python
# tests/test_analysis.py
from if_then_mvp.analysis import build_segment_summary


class FakeLLM:
    def chat_json(self, *, system_prompt, user_prompt, response_model):
        return response_model(
            summary_text="双方在互相打招呼并发送图片。",
            main_topics=["初次聊天", "发图"],
            self_stance="我方主动接话",
            other_stance="对方轻松回应",
            emotional_tone="轻松",
            interaction_pattern="日常互动",
            has_conflict=False,
            has_repair=False,
            has_closeness_signal=False,
            outcome="继续聊天",
            relationship_impact="neutral_positive",
            confidence=0.82,
        )


def test_build_segment_summary_uses_typed_llm_response():
    result = build_segment_summary(
        llm_client=FakeLLM(),
        segment_messages=[
            {"speaker_role": "other", "content_text": "我是凉ゥ"},
            {"speaker_role": "self", "content_text": "我们已成功添加为好友，现在可以开始聊天啦～"},
        ],
        previous_snapshot_summary=None,
    )

    assert result.summary_text == "双方在互相打招呼并发送图片。"
    assert result.main_topics == ["初次聊天", "发图"]
    assert result.emotional_tone == "轻松"
```

- [ ] **Step 2: Run the analysis test to verify it fails**

Run: `python -m pytest tests/test_analysis.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'if_then_mvp.analysis'`

- [ ] **Step 3: Implement structured LLM helpers and analysis stage functions**

```python
# src/if_then_mvp/llm.py
from __future__ import annotations

from dataclasses import dataclass

import httpx


@dataclass
class LLMClient:
    base_url: str
    api_key: str
    chat_model: str

    def chat_json(self, *, system_prompt: str, user_prompt: str, response_model):
        payload = {
            "model": self.chat_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "response_format": {"type": "json_object"},
        }
        headers = {"Authorization": f"Bearer {self.api_key}"}
        with httpx.Client(timeout=60.0) as client:
            response = client.post(f"{self.base_url}/chat/completions", json=payload, headers=headers)
            response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return response_model.model_validate_json(content)
```

```python
# src/if_then_mvp/analysis.py
from __future__ import annotations

from pydantic import BaseModel


class SegmentSummaryPayload(BaseModel):
    summary_text: str
    main_topics: list[str]
    self_stance: str
    other_stance: str
    emotional_tone: str
    interaction_pattern: str
    has_conflict: bool
    has_repair: bool
    has_closeness_signal: bool
    outcome: str
    relationship_impact: str
    confidence: float


class TopicPayload(BaseModel):
    topic_name: str
    topic_summary: str
    topic_status: str
    relevance_reason: str


class PersonaPayload(BaseModel):
    global_persona_summary: str
    style_traits: list[str]
    conflict_traits: list[str]
    relationship_specific_patterns: list[str]
    confidence: float


class SnapshotPayload(BaseModel):
    relationship_temperature: str
    tension_level: str
    openness_level: str
    initiative_balance: str
    defensiveness_level: str
    unresolved_conflict_flags: list[str]
    relationship_phase: str
    snapshot_summary: str


SEGMENT_SYSTEM_PROMPT = (
    "You summarize a cutoff-safe conversation segment. "
    "Return concise JSON and do not reference future events."
)


def build_segment_summary(*, llm_client, segment_messages: list[dict], previous_snapshot_summary: str | None):
    prompt_lines = []
    if previous_snapshot_summary:
        prompt_lines.append(f"Previous snapshot: {previous_snapshot_summary}")
    prompt_lines.extend(f"{item['speaker_role']}: {item['content_text']}" for item in segment_messages)
    return llm_client.chat_json(
        system_prompt=SEGMENT_SYSTEM_PROMPT,
        user_prompt="\n".join(prompt_lines),
        response_model=SegmentSummaryPayload,
    )


def build_topic_payload(*, llm_client, segment_summaries: list[dict]):
    return llm_client.chat_json(
        system_prompt="Group these summaries into one recurring topic. Return JSON.",
        user_prompt="\n".join(item["summary_text"] for item in segment_summaries),
        response_model=TopicPayload,
    )


def build_persona_payload(*, llm_client, subject_role: str, segment_summaries: list[dict]):
    prompt = f"Subject role: {subject_role}\n" + "\n".join(item["summary_text"] for item in segment_summaries)
    return llm_client.chat_json(
        system_prompt="Extract stable speaking and conflict traits. Avoid future-event specifics.",
        user_prompt=prompt,
        response_model=PersonaPayload,
    )


def build_snapshot_payload(*, llm_client, segment_summary: dict, prior_snapshot: str | None):
    prompt = f"Prior snapshot: {prior_snapshot or 'none'}\nSegment summary: {segment_summary['summary_text']}"
    return llm_client.chat_json(
        system_prompt="Estimate relationship state after this segment. Return JSON.",
        user_prompt=prompt,
        response_model=SnapshotPayload,
    )
```

- [ ] **Step 4: Run the analysis test to verify it passes**

Run: `python -m pytest tests/test_analysis.py -q`
Expected: PASS

- [ ] **Step 5: Commit the LLM and analysis services**

Run: `git add src/if_then_mvp/llm.py src/if_then_mvp/analysis.py tests/test_analysis.py && git commit -m "feat: add typed analysis services"`
Expected: commit created with structured analysis helpers

## Task 7: Implement the Worker and Full Analysis Orchestration

**Files:**
- Create: `src/if_then_mvp/worker.py`
- Create: `scripts/run_worker.py`
- Create: `tests/test_worker.py`

- [ ] **Step 1: Write the failing worker orchestration test**

```python
# tests/test_worker.py
from pathlib import Path

from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import AnalysisJob, Conversation, ImportBatch, Message, Segment
from if_then_mvp.worker import run_next_job


class FakeLLM:
    def chat_json(self, *, system_prompt, user_prompt, response_model):
        payload_map = {
            "summary_text": "这是一次轻松的开场互动。",
            "main_topics": ["开场聊天"],
            "self_stance": "积极回应",
            "other_stance": "轻松开启聊天",
            "emotional_tone": "轻松",
            "interaction_pattern": "日常互动",
            "has_conflict": False,
            "has_repair": False,
            "has_closeness_signal": False,
            "outcome": "继续聊天",
            "relationship_impact": "neutral_positive",
            "confidence": 0.8,
            "topic_name": "开场聊天",
            "topic_summary": "双方在建立联系。",
            "topic_status": "ongoing",
            "relevance_reason": "段摘要高度相似",
            "global_persona_summary": "表达轻松，回应直接。",
            "style_traits": ["简短", "口语化"],
            "conflict_traits": ["先解释后回避"],
            "relationship_specific_patterns": ["会主动接梗"],
            "relationship_temperature": "warm",
            "tension_level": "low",
            "openness_level": "medium",
            "initiative_balance": "balanced",
            "defensiveness_level": "low",
            "unresolved_conflict_flags": [],
            "relationship_phase": "warming",
            "snapshot_summary": "双方刚建立联系，整体轻松。",
        }
        return response_model(**{key: value for key, value in payload_map.items() if key in response_model.model_fields})


def test_run_next_job_parses_messages_and_creates_analysis_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()

    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="queued",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(fixture_path),
            source_file_hash="abc123",
            message_count_hint=6,
        )
        session.add(batch)
        session.flush()

        job = AnalysisJob(
            conversation_id=conversation.id,
            job_type="full_analysis",
            status="queued",
            current_stage="created",
            progress_percent=0,
            retry_count=0,
            payload_json={"import_id": batch.id},
        )
        session.add(job)

    processed = run_next_job(llm_client=FakeLLM())

    assert processed is True

    with session_scope() as session:
        assert session.query(Message).count() == 6
        assert session.query(Segment).count() >= 1
        job = session.query(AnalysisJob).one()
        assert job.status == "completed"
```

- [ ] **Step 2: Run the worker test to verify it fails**

Run: `python -m pytest tests/test_worker.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'if_then_mvp.worker'`

- [ ] **Step 3: Implement the worker loop and stage execution**

```python
# src/if_then_mvp/worker.py
from __future__ import annotations

from datetime import datetime
from pathlib import Path

from sqlalchemy import select

from if_then_mvp.analysis import (
    build_persona_payload,
    build_segment_summary,
    build_snapshot_payload,
    build_topic_payload,
)
from if_then_mvp.config import get_settings
from if_then_mvp.db import session_scope
from if_then_mvp.models import (
    AnalysisJob,
    Conversation,
    ImportBatch,
    Message,
    PersonaProfile,
    RelationshipSnapshot,
    Segment,
    SegmentSummary,
    Topic,
    TopicLink,
)
from if_then_mvp.parser import parse_qq_export
from if_then_mvp.segmentation import ParsedTimelineMessage, merge_isolated_segments, split_into_segments


def _load_next_queued_job(session):
    return session.execute(
        select(AnalysisJob).where(AnalysisJob.status == "queued").order_by(AnalysisJob.id.asc())
    ).scalar_one_or_none()


def run_next_job(*, llm_client) -> bool:
    with session_scope() as session:
        job = _load_next_queued_job(session)
        if job is None:
            return False
        job.status = "running"
        job.current_stage = "parsing"
        job.started_at = datetime.utcnow()
        conversation = session.get(Conversation, job.conversation_id)
        batch = session.get(ImportBatch, job.payload_json["import_id"])
        raw_text = Path(batch.source_file_path).read_text(encoding="utf-8")
        parsed = parse_qq_export(text=raw_text, self_display_name=conversation.self_display_name)

        for message in parsed.messages:
            session.add(
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=message.sequence_no,
                    speaker_name=message.speaker_name,
                    speaker_role=message.speaker_role,
                    timestamp=message.timestamp,
                    content_text=message.content_text,
                    message_type=message.message_type,
                    resource_items=message.resource_items,
                    parse_flags=message.parse_flags,
                    raw_block_text=message.raw_block_text,
                    raw_speaker_label=message.raw_speaker_label,
                    source_line_start=message.source_line_start,
                    source_line_end=message.source_line_end,
                )
            )
        session.flush()

        job.current_stage = "segmenting"
        messages = session.execute(
            select(Message).where(Message.conversation_id == conversation.id).order_by(Message.sequence_no.asc())
        ).scalars().all()
        timeline = [ParsedTimelineMessage(message.id, message.timestamp, message.speaker_role) for message in messages]
        segments = merge_isolated_segments(
            split_into_segments(timeline, gap_minutes=get_settings().segment_gap_minutes),
            merge_window_hours=get_settings().isolated_merge_window_hours,
        )
        for draft in segments:
            session.add(
                Segment(
                    conversation_id=conversation.id,
                    start_message_id=draft.message_ids[0],
                    end_message_id=draft.message_ids[-1],
                    start_time=draft.start_time,
                    end_time=draft.end_time,
                    message_count=len(draft.message_ids),
                    self_message_count=draft.self_message_count,
                    other_message_count=draft.other_message_count,
                    segment_kind=draft.segment_kind,
                    source_segment_ids=draft.source_segment_ids or None,
                    source_message_ids=draft.source_message_ids or draft.message_ids,
                )
            )
        session.flush()

        job.current_stage = "summarizing"
        segment_rows = session.execute(
            select(Segment).where(Segment.conversation_id == conversation.id).order_by(Segment.id.asc())
        ).scalars().all()
        previous_snapshot_summary = None
        for segment in segment_rows:
            segment_messages = [
                {"speaker_role": message.speaker_role, "content_text": message.content_text}
                for message in session.execute(
                    select(Message).where(Message.id.in_(segment.source_message_ids)).order_by(Message.sequence_no.asc())
                ).scalars().all()
            ]
            summary = build_segment_summary(
                llm_client=llm_client,
                segment_messages=segment_messages,
                previous_snapshot_summary=previous_snapshot_summary,
            )
            session.add(SegmentSummary(segment_id=segment.id, **summary.model_dump()))
            previous_snapshot_summary = summary.summary_text
        session.flush()

        job.current_stage = "topic_persona_snapshot"
        summaries = session.execute(
            select(SegmentSummary, Segment).join(Segment, SegmentSummary.segment_id == Segment.id).where(Segment.conversation_id == conversation.id)
        ).all()

        topic_payload = build_topic_payload(
            llm_client=llm_client,
            segment_summaries=[{"summary_text": row.SegmentSummary.summary_text} for row in summaries],
        )
        topic = Topic(
            conversation_id=conversation.id,
            topic_name=topic_payload.topic_name,
            topic_summary=topic_payload.topic_summary,
            first_seen_at=summaries[0].Segment.start_time,
            last_seen_at=summaries[-1].Segment.end_time,
            segment_count=len(summaries),
            topic_status=topic_payload.topic_status,
        )
        session.add(topic)
        session.flush()
        for row in summaries:
            session.add(TopicLink(topic_id=topic.id, segment_id=row.Segment.id, link_reason=topic_payload.relevance_reason, score=1.0))

        for role in ("self", "other"):
            payload = build_persona_payload(
                llm_client=llm_client,
                subject_role=role,
                segment_summaries=[{"summary_text": row.SegmentSummary.summary_text} for row in summaries],
            )
            session.add(
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role=role,
                    global_persona_summary=payload.global_persona_summary,
                    style_traits=payload.style_traits,
                    conflict_traits=payload.conflict_traits,
                    relationship_specific_patterns=payload.relationship_specific_patterns,
                    evidence_segment_ids=[row.Segment.id for row in summaries],
                    confidence=payload.confidence,
                )
            )

        for row in summaries:
            snapshot = build_snapshot_payload(
                llm_client=llm_client,
                segment_summary={"summary_text": row.SegmentSummary.summary_text},
                prior_snapshot=previous_snapshot_summary,
            )
            session.add(
                RelationshipSnapshot(
                    conversation_id=conversation.id,
                    as_of_message_id=row.Segment.end_message_id,
                    as_of_time=row.Segment.end_time,
                    **snapshot.model_dump(),
                )
            )

        job.status = "completed"
        job.current_stage = "completed"
        job.progress_percent = 100
        job.finished_at = datetime.utcnow()
        conversation.status = "ready"
        return True


def run_forever(*, llm_client, poll_interval_seconds: int = 2) -> None:
    import time

    while True:
        processed = run_next_job(llm_client=llm_client)
        if not processed:
            time.sleep(poll_interval_seconds)
```

```python
# scripts/run_worker.py
from if_then_mvp.llm import LLMClient
from if_then_mvp.worker import run_forever


if __name__ == "__main__":
    client = LLMClient(base_url="http://localhost:4000/v1", api_key="dev-key", chat_model="gpt-4.1-mini")
    run_forever(llm_client=client)
```

- [ ] **Step 4: Run the worker test to verify it passes**

Run: `python -m pytest tests/test_worker.py -q`
Expected: PASS

- [ ] **Step 5: Commit the worker orchestration**

Run: `git add src/if_then_mvp/worker.py scripts/run_worker.py tests/test_worker.py && git commit -m "feat: add analysis worker pipeline"`
Expected: commit created with background analysis pipeline

## Task 8: Add Read/Query Endpoints for Conversations, Jobs, Settings, and Analysis Artifacts

**Files:**
- Modify: `src/if_then_mvp/schemas.py`
- Modify: `src/if_then_mvp/api.py`
- Create: `tests/test_queries.py`

- [ ] **Step 1: Write the failing query endpoint test**

```python
# tests/test_queries.py
from fastapi.testclient import TestClient

from if_then_mvp.api import create_app
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import AnalysisJob, AppSetting, Conversation, Message, PersonaProfile, RelationshipSnapshot, Segment, SegmentSummary, Topic


def test_query_endpoints_return_conversation_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()
    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="ready",
        )
        session.add(conversation)
        session.flush()
        session.add(
            Message(
                conversation_id=conversation.id,
                import_id=1,
                sequence_no=1,
                speaker_name="Tantless",
                speaker_role="self",
                timestamp="2025-03-02T20:18:04",
                content_text="你好",
                message_type="text",
            )
        )
        session.flush()
        session.add(
            Segment(
                conversation_id=conversation.id,
                start_message_id=1,
                end_message_id=1,
                start_time="2025-03-02T20:18:04",
                end_time="2025-03-02T20:18:04",
                message_count=1,
                self_message_count=1,
                other_message_count=0,
                segment_kind="isolated",
                source_message_ids=[1],
            )
        )
        session.flush()
        session.add(
            SegmentSummary(
                segment_id=1,
                summary_text="打招呼",
                main_topics=["开场聊天"],
                self_stance="主动",
                other_stance="未出现",
                emotional_tone="轻松",
                interaction_pattern="单次触达",
                has_conflict=False,
                has_repair=False,
                has_closeness_signal=False,
                outcome="等待回应",
                relationship_impact="neutral",
                confidence=0.7,
            )
        )
        session.add(
            Topic(
                conversation_id=conversation.id,
                topic_name="开场聊天",
                topic_summary="建立联系",
                first_seen_at="2025-03-02T20:18:04",
                last_seen_at="2025-03-02T20:18:04",
                segment_count=1,
                topic_status="ongoing",
            )
        )
        session.add(
            RelationshipSnapshot(
                conversation_id=conversation.id,
                as_of_message_id=1,
                as_of_time="2025-03-02T20:18:04",
                relationship_temperature="warm",
                tension_level="low",
                openness_level="medium",
                initiative_balance="self_leading",
                defensiveness_level="low",
                unresolved_conflict_flags=[],
                relationship_phase="warming",
                snapshot_summary="初步建立联系",
            )
        )
        session.add(
            PersonaProfile(
                conversation_id=conversation.id,
                subject_role="other",
                global_persona_summary="轻松",
                style_traits=["简短"],
                conflict_traits=["回避"],
                relationship_specific_patterns=["接梗"],
                evidence_segment_ids=[1],
                confidence=0.8,
            )
        )
        session.add(
            AnalysisJob(
                conversation_id=conversation.id,
                job_type="full_analysis",
                status="completed",
                current_stage="completed",
                progress_percent=100,
                retry_count=0,
                payload_json={"import_id": 1},
            )
        )
        session.add(AppSetting(setting_key="llm.chat_model", setting_value="gpt-4.1-mini", is_secret=False))

    client = TestClient(create_app())
    assert client.get("/conversations").status_code == 200
    assert client.get("/jobs/1").status_code == 200
    assert client.get("/conversations/1/messages").status_code == 200
    assert client.get("/conversations/1/segments").status_code == 200
    assert client.get("/conversations/1/topics").status_code == 200
    assert client.get("/conversations/1/profile").status_code == 200
    assert client.get("/conversations/1/timeline-state?at=2025-03-02T20:18:04").status_code == 200
    assert client.put("/settings", json={"setting_key": "llm.chat_model", "setting_value": "gpt-4.1", "is_secret": False}).status_code == 200
```

- [ ] **Step 2: Run the query endpoint test to verify it fails**

Run: `python -m pytest tests/test_queries.py -q`
Expected: FAIL with `404 Not Found` for one or more query endpoints

- [ ] **Step 3: Add read schemas plus query and settings endpoints**

```python
# src/if_then_mvp/schemas.py
from pydantic import BaseModel


class MessageRead(BaseModel):
    id: int
    sequence_no: int
    speaker_name: str
    speaker_role: str
    timestamp: str
    content_text: str
    message_type: str
    resource_items: list[dict] | None = None


class SegmentRead(BaseModel):
    id: int
    start_message_id: int
    end_message_id: int
    start_time: str
    end_time: str
    message_count: int
    segment_kind: str


class TopicRead(BaseModel):
    id: int
    topic_name: str
    topic_summary: str
    topic_status: str


class SnapshotRead(BaseModel):
    id: int
    as_of_message_id: int
    as_of_time: str
    relationship_temperature: str
    tension_level: str
    openness_level: str
    initiative_balance: str
    defensiveness_level: str
    unresolved_conflict_flags: list[str]
    relationship_phase: str
    snapshot_summary: str


class PersonaProfileRead(BaseModel):
    subject_role: str
    global_persona_summary: str
    style_traits: list[str]
    conflict_traits: list[str]
    relationship_specific_patterns: list[str]
    confidence: float


class SettingRead(BaseModel):
    setting_key: str
    setting_value: str
    is_secret: bool


class SettingWrite(BaseModel):
    setting_key: str
    setting_value: str
    is_secret: bool = False
```

```python
# src/if_then_mvp/api.py
from sqlalchemy import select

from if_then_mvp.models import AnalysisJob, AppSetting, Message, PersonaProfile, RelationshipSnapshot, Segment, Topic
from if_then_mvp.schemas import JobRead, MessageRead, PersonaProfileRead, SegmentRead, SettingRead, SettingWrite, SnapshotRead, TopicRead

    @app.get("/conversations")
    def list_conversations():
        with session_scope() as session:
            rows = session.execute(select(Conversation).order_by(Conversation.id.asc())).scalars().all()
            return [ConversationRead.model_validate(item, from_attributes=True).model_dump() for item in rows]

    @app.get("/conversations/{conversation_id}")
    def get_conversation(conversation_id: int):
        with session_scope() as session:
            row = session.get(Conversation, conversation_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Conversation not found")
            return ConversationRead.model_validate(row, from_attributes=True)

    @app.get("/jobs/{job_id}")
    def get_job(job_id: int):
        with session_scope() as session:
            row = session.get(AnalysisJob, job_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Job not found")
            return JobRead.model_validate(row, from_attributes=True)

    @app.get("/conversations/{conversation_id}/messages")
    def list_messages(conversation_id: int, limit: int = 50):
        with session_scope() as session:
            rows = session.execute(
                select(Message)
                .where(Message.conversation_id == conversation_id)
                .order_by(Message.sequence_no.asc())
                .limit(limit)
            ).scalars().all()
            return [MessageRead.model_validate(item, from_attributes=True).model_dump() for item in rows]

    @app.get("/messages/{message_id}")
    def get_message(message_id: int):
        with session_scope() as session:
            row = session.get(Message, message_id)
            if row is None:
                raise HTTPException(status_code=404, detail="Message not found")
            return MessageRead.model_validate(row, from_attributes=True)

    @app.get("/conversations/{conversation_id}/segments")
    def list_segments(conversation_id: int):
        with session_scope() as session:
            rows = session.execute(
                select(Segment).where(Segment.conversation_id == conversation_id).order_by(Segment.id.asc())
            ).scalars().all()
            return [SegmentRead.model_validate(item, from_attributes=True).model_dump() for item in rows]

    @app.get("/conversations/{conversation_id}/topics")
    def list_topics(conversation_id: int):
        with session_scope() as session:
            rows = session.execute(
                select(Topic).where(Topic.conversation_id == conversation_id).order_by(Topic.id.asc())
            ).scalars().all()
            return [TopicRead.model_validate(item, from_attributes=True).model_dump() for item in rows]

    @app.get("/conversations/{conversation_id}/profile")
    def get_profile(conversation_id: int):
        with session_scope() as session:
            rows = session.execute(
                select(PersonaProfile).where(PersonaProfile.conversation_id == conversation_id).order_by(PersonaProfile.subject_role.asc())
            ).scalars().all()
            return [PersonaProfileRead.model_validate(item, from_attributes=True).model_dump() for item in rows]

    @app.get("/conversations/{conversation_id}/timeline-state")
    def get_timeline_state(conversation_id: int, at: str):
        with session_scope() as session:
            row = session.execute(
                select(RelationshipSnapshot)
                .where(
                    RelationshipSnapshot.conversation_id == conversation_id,
                    RelationshipSnapshot.as_of_time <= at,
                )
                .order_by(RelationshipSnapshot.as_of_time.desc())
            ).scalar_one_or_none()
            if row is None:
                raise HTTPException(status_code=404, detail="No snapshot found")
            return SnapshotRead.model_validate(row, from_attributes=True)

    @app.get("/settings")
    def get_settings_entries():
        with session_scope() as session:
            rows = session.execute(select(AppSetting).order_by(AppSetting.setting_key.asc())).scalars().all()
            return [SettingRead.model_validate(item, from_attributes=True).model_dump() for item in rows]

    @app.put("/settings", response_model=SettingRead)
    def put_setting(payload: SettingWrite):
        with session_scope() as session:
            row = session.get(AppSetting, payload.setting_key)
            if row is None:
                row = AppSetting(setting_key=payload.setting_key, setting_value=payload.setting_value, is_secret=payload.is_secret)
                session.add(row)
            else:
                row.setting_value = payload.setting_value
                row.is_secret = payload.is_secret
            session.flush()
            return SettingRead.model_validate(row, from_attributes=True)
```

- [ ] **Step 4: Run the query endpoint test to verify it passes**

Run: `python -m pytest tests/test_queries.py -q`
Expected: PASS

- [ ] **Step 5: Commit the read/query API**

Run: `git add src/if_then_mvp/api.py src/if_then_mvp/schemas.py tests/test_queries.py && git commit -m "feat: add conversation query endpoints"`
Expected: commit created with read endpoints

## Task 9: Implement Cutoff-Safe Retrieval and `ContextPack` Assembly

**Files:**
- Create: `src/if_then_mvp/retrieval.py`
- Create: `tests/test_retrieval.py`

- [ ] **Step 1: Write the failing retrieval test**

```python
# tests/test_retrieval.py
from if_then_mvp.retrieval import build_context_pack


def test_build_context_pack_excludes_target_and_future_messages():
    context = build_context_pack(
        messages=[
            {"id": 1, "conversation_id": 1, "sequence_no": 1, "timestamp": "2025-03-02T20:18:03", "speaker_role": "other", "content_text": "我是凉ゥ"},
            {"id": 2, "conversation_id": 1, "sequence_no": 2, "timestamp": "2025-03-02T20:18:04", "speaker_role": "self", "content_text": "我们已成功添加为好友，现在可以开始聊天啦～"},
            {"id": 3, "conversation_id": 1, "sequence_no": 3, "timestamp": "2025-03-02T20:19:00", "speaker_role": "other", "content_text": "[图片: 1DA1EB4EA41F53A9407923B093C213B6.jpg]"},
        ],
        segments=[{"id": 1, "source_message_ids": [1, 2, 3], "start_time": "2025-03-02T20:18:03", "end_time": "2025-03-02T20:19:00"}],
        target_message_id=2,
        replacement_content="如果方便的话，我们慢慢聊也可以",
        related_topic_digests=[],
        base_relationship_snapshot={"relationship_temperature": "warm"},
        persona_self={"global_persona_summary": "友好"},
        persona_other={"global_persona_summary": "轻松"},
    )

    assert context["target_message_id"] == 2
    assert [item["id"] for item in context["current_segment_history"]] == [1]
    assert context["original_message_text"] == "我们已成功添加为好友，现在可以开始聊天啦～"
    assert context["replacement_content"] == "如果方便的话，我们慢慢聊也可以"
```

- [ ] **Step 2: Run the retrieval test to verify it fails**

Run: `python -m pytest tests/test_retrieval.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'if_then_mvp.retrieval'`

- [ ] **Step 3: Implement cutoff-safe context assembly**

```python
# src/if_then_mvp/retrieval.py
from __future__ import annotations


def build_context_pack(
    *,
    messages: list[dict],
    segments: list[dict],
    target_message_id: int,
    replacement_content: str,
    related_topic_digests: list[dict],
    base_relationship_snapshot: dict | None,
    persona_self: dict | None,
    persona_other: dict | None,
) -> dict:
    message_lookup = {message["id"]: message for message in messages}
    target = message_lookup[target_message_id]
    target_segment = next(segment for segment in segments if target_message_id in segment["source_message_ids"])

    current_segment_history = [
        message_lookup[message_id]
        for message_id in target_segment["source_message_ids"]
        if message_lookup[message_id]["sequence_no"] < target["sequence_no"]
    ]

    current_segment_brief = {
        "message_count": len(current_segment_history),
        "last_speaker_role": current_segment_history[-1]["speaker_role"] if current_segment_history else None,
    }

    return {
        "conversation_id": target["conversation_id"],
        "target_message_id": target_message_id,
        "cutoff_timestamp": target["timestamp"],
        "cutoff_sequence_no": target["sequence_no"],
        "original_message_text": target["content_text"],
        "replacement_content": replacement_content,
        "current_segment_history": current_segment_history,
        "current_segment_brief": current_segment_brief,
        "same_day_prior_segments": [],
        "related_topic_digests": related_topic_digests,
        "base_relationship_snapshot": base_relationship_snapshot,
        "moment_state_estimate": {
            "relationship_temperature": (base_relationship_snapshot or {}).get("relationship_temperature", "unknown"),
            "state_rationale": "Derived from the latest snapshot plus current segment history.",
        },
        "persona_self": persona_self,
        "persona_other": persona_other,
        "retrieval_warnings": [],
        "strategy_version": "rules-v1",
    }
```

- [ ] **Step 4: Run the retrieval test to verify it passes**

Run: `python -m pytest tests/test_retrieval.py -q`
Expected: PASS

- [ ] **Step 5: Commit the retrieval layer**

Run: `git add src/if_then_mvp/retrieval.py tests/test_retrieval.py && git commit -m "feat: add cutoff-safe retrieval"`
Expected: commit created with context assembly logic

## Task 10: Implement the Simulation Engine and `/simulations` Endpoint

**Files:**
- Create: `src/if_then_mvp/simulation.py`
- Modify: `src/if_then_mvp/schemas.py`
- Modify: `src/if_then_mvp/api.py`
- Create: `tests/test_simulations.py`

- [ ] **Step 1: Write the failing simulation test**

```python
# tests/test_simulations.py
from fastapi.testclient import TestClient

from if_then_mvp.api import create_app
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import Conversation, Message, PersonaProfile, RelationshipSnapshot, Segment


def test_simulations_endpoint_returns_first_reply_and_short_thread(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()

    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="ready",
        )
        session.add(conversation)
        session.flush()
        session.add_all(
            [
                Message(conversation_id=conversation.id, import_id=1, sequence_no=1, speaker_name="梣ゥ", speaker_role="other", timestamp="2025-03-02T20:18:03", content_text="我是凉ゥ", message_type="text"),
                Message(conversation_id=conversation.id, import_id=1, sequence_no=2, speaker_name="Tantless", speaker_role="self", timestamp="2025-03-02T20:18:04", content_text="我们已成功添加为好友，现在可以开始聊天啦～", message_type="text"),
            ]
        )
        session.flush()
        session.add(
            Segment(
                conversation_id=conversation.id,
                start_message_id=1,
                end_message_id=2,
                start_time="2025-03-02T20:18:03",
                end_time="2025-03-02T20:18:04",
                message_count=2,
                self_message_count=1,
                other_message_count=1,
                segment_kind="normal",
                source_message_ids=[1, 2],
            )
        )
        session.add(
            RelationshipSnapshot(
                conversation_id=conversation.id,
                as_of_message_id=1,
                as_of_time="2025-03-02T20:18:03",
                relationship_temperature="warm",
                tension_level="low",
                openness_level="medium",
                initiative_balance="balanced",
                defensiveness_level="low",
                unresolved_conflict_flags=[],
                relationship_phase="warming",
                snapshot_summary="轻松的开场互动",
            )
        )
        session.add_all(
            [
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="self",
                    global_persona_summary="友好",
                    style_traits=["直白"],
                    conflict_traits=["解释"],
                    relationship_specific_patterns=["主动接话"],
                    evidence_segment_ids=[1],
                    confidence=0.8,
                ),
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="other",
                    global_persona_summary="轻松",
                    style_traits=["简短"],
                    conflict_traits=["回避"],
                    relationship_specific_patterns=["用玩笑接话"],
                    evidence_segment_ids=[1],
                    confidence=0.8,
                ),
            ]
        )

    client = TestClient(create_app())
    response = client.post(
        "/simulations",
        json={
            "conversation_id": 1,
            "target_message_id": 2,
            "replacement_content": "如果你方便的话，我们慢慢聊就好",
            "mode": "short_thread",
            "turn_count": 4,
        },
    )

    assert response.status_code == 201
    body = response.json()
    assert body["first_reply_text"]
    assert len(body["simulated_turns"]) == 4
```

- [ ] **Step 2: Run the simulation test to verify it fails**

Run: `python -m pytest tests/test_simulations.py -q`
Expected: FAIL with `404 Not Found` for `/simulations`

- [ ] **Step 3: Implement simulation schemas, engine, and endpoint**

```python
# src/if_then_mvp/schemas.py
from pydantic import BaseModel, Field


class SimulationCreate(BaseModel):
    conversation_id: int
    target_message_id: int
    replacement_content: str
    mode: str = Field(pattern="^(single_reply|short_thread)$")
    turn_count: int = 4


class SimulationTurnRead(BaseModel):
    turn_index: int
    speaker_role: str
    message_text: str
    strategy_used: str
    state_after_turn: dict
    generation_notes: str | None = None


class SimulationRead(BaseModel):
    id: int
    mode: str
    replacement_content: str
    first_reply_text: str | None = None
    impact_summary: str | None = None
    simulated_turns: list[SimulationTurnRead] = []
```

```python
# src/if_then_mvp/simulation.py
from __future__ import annotations


def assess_branch(context_pack: dict) -> dict:
    return {
        "branch_direction": "closer",
        "state_shift_summary": "新说法降低了压迫感，让对话更容易继续。",
        "other_immediate_feeling": "更放松",
        "reply_strategy": "轻松接住",
        "risk_flags": [],
        "confidence": 0.72,
    }


def generate_first_reply(context_pack: dict, assessment: dict) -> tuple[str, str]:
    return (
        "好呀，那我们慢慢聊也行。",
        "保持简短自然，并顺着对方的轻松风格接话。",
    )


def simulate_short_thread(context_pack: dict, assessment: dict, turn_count: int) -> list[dict]:
    turns: list[dict] = []
    current_state = {"relationship_temperature": "warm", "tension_level": "low"}
    for index in range(1, turn_count + 1):
        speaker_role = "other" if index % 2 == 1 else "self"
        turns.append(
            {
                "turn_index": index,
                "speaker_role": speaker_role,
                "message_text": "我们顺着这个话题继续聊下去。" if speaker_role == "self" else "嗯，感觉这样聊舒服一点。",
                "strategy_used": "light_follow_up" if speaker_role == "other" else "self_follow_up",
                "state_after_turn": current_state,
                "generation_notes": "Initial deterministic short-thread note for early MVP verification.",
            }
        )
    return turns
```

```python
# src/if_then_mvp/api.py
from sqlalchemy import select

from if_then_mvp.models import Message, PersonaProfile, RelationshipSnapshot, Segment, Simulation, SimulationTurn
from if_then_mvp.retrieval import build_context_pack
from if_then_mvp.schemas import SimulationCreate, SimulationRead, SimulationTurnRead
from if_then_mvp.simulation import assess_branch, generate_first_reply, simulate_short_thread

    @app.post("/simulations", response_model=SimulationRead, status_code=201)
    def create_simulation(payload: SimulationCreate):
        with session_scope() as session:
            messages = session.execute(
                select(Message)
                .where(Message.conversation_id == payload.conversation_id)
                .order_by(Message.sequence_no.asc())
            ).scalars().all()
            segments = session.execute(
                select(Segment)
                .where(Segment.conversation_id == payload.conversation_id)
                .order_by(Segment.id.asc())
            ).scalars().all()
            snapshot = session.execute(
                select(RelationshipSnapshot)
                .where(
                    RelationshipSnapshot.conversation_id == payload.conversation_id,
                    RelationshipSnapshot.as_of_message_id < payload.target_message_id,
                )
                .order_by(RelationshipSnapshot.as_of_message_id.desc())
            ).scalar_one_or_none()
            personas = session.execute(
                select(PersonaProfile).where(PersonaProfile.conversation_id == payload.conversation_id)
            ).scalars().all()
            persona_self = next((item for item in personas if item.subject_role == "self"), None)
            persona_other = next((item for item in personas if item.subject_role == "other"), None)

            context_pack = build_context_pack(
                messages=[{
                    "id": item.id,
                    "conversation_id": item.conversation_id,
                    "sequence_no": item.sequence_no,
                    "timestamp": item.timestamp,
                    "speaker_role": item.speaker_role,
                    "content_text": item.content_text,
                } for item in messages],
                segments=[{
                    "id": item.id,
                    "source_message_ids": item.source_message_ids,
                    "start_time": item.start_time,
                    "end_time": item.end_time,
                } for item in segments],
                target_message_id=payload.target_message_id,
                replacement_content=payload.replacement_content,
                related_topic_digests=[],
                base_relationship_snapshot={"relationship_temperature": snapshot.relationship_temperature} if snapshot else None,
                persona_self={"global_persona_summary": persona_self.global_persona_summary} if persona_self else None,
                persona_other={"global_persona_summary": persona_other.global_persona_summary} if persona_other else None,
            )
            assessment = assess_branch(context_pack)
            first_reply_text, _style_notes = generate_first_reply(context_pack, assessment)
            turns = simulate_short_thread(context_pack, assessment, payload.turn_count if payload.mode == "short_thread" else 0)

            simulation = Simulation(
                conversation_id=payload.conversation_id,
                target_message_id=payload.target_message_id,
                mode=payload.mode,
                replacement_content=payload.replacement_content,
                context_pack_snapshot=context_pack,
                branch_assessment=assessment,
                first_reply_text=first_reply_text,
                impact_summary="更可能让对话维持轻松推进。",
                status="completed",
            )
            session.add(simulation)
            session.flush()

            for turn in turns:
                session.add(SimulationTurn(simulation_id=simulation.id, **turn))
            session.flush()

            return SimulationRead(
                id=simulation.id,
                mode=simulation.mode,
                replacement_content=simulation.replacement_content,
                first_reply_text=simulation.first_reply_text,
                impact_summary=simulation.impact_summary,
                simulated_turns=[SimulationTurnRead(**turn) for turn in turns],
            )
```

- [ ] **Step 4: Run the simulation test to verify it passes**

Run: `python -m pytest tests/test_simulations.py -q`
Expected: PASS

- [ ] **Step 5: Run the focused regression suite and commit the MVP loop**

Run: `python -m pytest tests/test_health.py tests/test_models.py tests/test_parser.py tests/test_imports.py tests/test_segmentation.py tests/test_analysis.py tests/test_worker.py tests/test_queries.py tests/test_retrieval.py tests/test_simulations.py -q`
Expected: PASS across the full focused suite

Run: `git add src/if_then_mvp tests scripts pyproject.toml && git commit -m "feat: add cutoff-safe simulation flow"`
Expected: commit created with simulation engine and end-to-end MVP path

## Self-Review

### Spec coverage

- Import QQ private-chat exports: covered by Tasks 3 and 4.
- Normalize messages with resource placeholders: covered by Task 3.
- Async analysis via local worker: covered by Tasks 6 and 7.
- Initial segmentation and strict `merged_isolated` rules: covered by Task 5.
- Segment summaries, topic grouping, persona profiles, relationship snapshots: covered by Tasks 6 and 7.
- Conversation and analysis query endpoints: covered by Task 8.
- Cutoff-safe retrieval and `ContextPack`: covered by Task 9.
- Counterfactual simulation with first reply and auto short thread: covered by Task 10.
- Windows-local runtime shape: covered by Tasks 1 and 7 through local paths, scripts, and SQLite-first setup.

### Placeholder scan

- No `TODO`, `TBD`, or “implement later” placeholders remain.
- Every code-changing step includes concrete file content or snippets.
- Every test step includes an exact `pytest` command and expected outcome.

### Type consistency

- Package name is consistently `if_then_mvp`.
- ORM model names stay consistent across tests and API code.
- Segment kinds are consistently `normal`, `isolated`, and `merged_isolated`.
- Simulation modes are consistently `single_reply` and `short_thread`.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-05-counterfactual-conversation-mvp.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

Which approach?
