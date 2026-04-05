from pathlib import Path

from if_then_mvp.db import init_db, session_scope
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
)
from if_then_mvp.worker import _claim_next_job, run_next_job


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


class ExplodingLLM:
    def chat_json(self, *, system_prompt, user_prompt, response_model):
        raise RuntimeError("boom")


def _seed_job(*, fixture_path: Path):
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


def test_run_next_job_parses_messages_and_creates_analysis_artifacts(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path)

    processed = run_next_job(llm_client=FakeLLM())

    assert processed is True

    with session_scope() as session:
        assert session.query(Message).count() == 6
        sequence_numbers = [message.sequence_no for message in session.query(Message).order_by(Message.sequence_no.asc()).all()]
        assert sequence_numbers == [1, 2, 3, 4, 5, 6]
        assert all(message.import_id == 1 for message in session.query(Message).all())
        assert session.query(Segment).count() >= 1
        assert session.query(SegmentSummary).count() >= 1
        assert session.query(Topic).count() == 1
        assert session.query(PersonaProfile).count() == 2
        assert session.query(RelationshipSnapshot).count() >= 1
        job = session.query(AnalysisJob).one()
        assert job.status == "completed"
        assert job.current_stage == "completed"
        assert job.progress_percent == 100
        conversation = session.query(Conversation).one()
        assert conversation.status == "ready"


def test_run_next_job_marks_job_failed_when_stage_raises(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path)

    processed = run_next_job(llm_client=ExplodingLLM())

    assert processed is True

    with session_scope() as session:
        job = session.query(AnalysisJob).one()
        assert job.status == "failed"
        assert job.current_stage == "failed"
        assert job.progress_percent > 0
        assert "boom" in job.error_message
        assert session.query(Message).count() == 0
        assert session.query(Segment).count() == 0
        assert session.query(SegmentSummary).count() == 0
        assert session.query(Topic).count() == 0
        assert session.query(PersonaProfile).count() == 0
        assert session.query(RelationshipSnapshot).count() == 0
        conversation = session.query(Conversation).one()
        assert conversation.status == "failed"


def test_claim_next_job_is_single_use_and_marks_conversation_analyzing(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    fixture_path = Path("tests/fixtures/qq_export_sample.txt")
    init_db()
    _seed_job(fixture_path=fixture_path)

    first_claim = _claim_next_job()
    second_claim = _claim_next_job()

    assert first_claim == (1, 1)
    assert second_claim is None

    with session_scope() as session:
        job = session.query(AnalysisJob).one()
        assert job.status == "running"
        assert job.current_stage == "parsing"
        assert job.progress_percent == 10
        conversation = session.query(Conversation).one()
        assert conversation.status == "analyzing"
