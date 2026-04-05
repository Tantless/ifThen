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
