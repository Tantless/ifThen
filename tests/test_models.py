from pathlib import Path

import pytest
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as SASession, sessionmaker


def test_core_models_persist_and_are_mapped_with_sqlalchemy(tmp_path, monkeypatch):
    first_data_dir = tmp_path / "app_data_first"
    second_data_dir = tmp_path / "app_data_second"

    monkeypatch.setenv("IF_THEN_DATA_DIR", str(first_data_dir))

    from if_then_mvp.db import Base, get_engine, init_db, session_scope
    from if_then_mvp.models import AnalysisJob, AppSetting, Conversation, ImportBatch, Message

    first_engine = get_engine()
    first_db_path = Path(first_engine.url.database)
    assert first_db_path == first_data_dir / "db" / "if_then_mvp.sqlite3"

    init_db()
    assert "conversations" in Base.metadata.tables
    assert Conversation.__table__.name == "conversations"
    assert ImportBatch.__table__.name == "imports"
    assert Message.__table__.name == "messages"
    assert AnalysisJob.__table__.name == "analysis_jobs"
    assert AppSetting.__table__.name == "app_settings"

    with session_scope() as session:
        assert isinstance(session, SASession)

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
        with pytest.raises(IntegrityError):
            session.add(
                ImportBatch(
                    conversation_id=999999,
                    source_file_name="broken.txt",
                    source_file_path="app_data/uploads/broken.txt",
                    source_file_hash="broken",
                    message_count_hint=1,
                )
            )
            session.flush()
        session.rollback()

    first_verify_session = sessionmaker(bind=first_engine, class_=SASession, expire_on_commit=False)
    with first_verify_session() as verify_session:
        assert verify_session.query(Conversation).count() == 1
        assert verify_session.query(ImportBatch).count() == 1
        assert verify_session.query(Message).count() == 1
        assert verify_session.query(AnalysisJob).count() == 1
        assert verify_session.query(AppSetting).count() == 1

    monkeypatch.setenv("IF_THEN_DATA_DIR", str(second_data_dir))

    second_engine = get_engine()
    assert second_engine is not first_engine
    assert Path(second_engine.url.database) == second_data_dir / "db" / "if_then_mvp.sqlite3"

    init_db()

    with session_scope() as session:
        session.add(
            Conversation(
                title="第二组",
                chat_type="private",
                self_display_name="Tantless",
                other_display_name="第二组",
                source_format="qq_chat_exporter_v5",
                status="queued",
            )
        )

    second_verify_session = sessionmaker(bind=second_engine, class_=SASession, expire_on_commit=False)
    with second_verify_session() as verify_session:
        assert verify_session.query(Conversation).count() == 1

    with first_verify_session() as verify_session:
        assert verify_session.query(Conversation).count() == 1


def test_sqlite_engine_enables_wal_and_busy_timeout(tmp_path, monkeypatch):
    data_dir = tmp_path / "app_data"
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(data_dir))

    from if_then_mvp.db import get_engine

    engine = get_engine()

    with engine.connect() as connection:
        journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()
        busy_timeout = connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()
        foreign_keys = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()

    assert str(journal_mode).lower() == "wal"
    assert int(busy_timeout) >= 5000
    assert int(foreign_keys) == 1
