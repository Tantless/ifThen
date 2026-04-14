from fastapi.testclient import TestClient

from if_then_mvp.api import create_app
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import (
    AnalysisJob,
    AppSetting,
    Conversation,
    ImportBatch,
    Message,
    PersonaProfile,
    RelationshipSnapshot,
    Segment,
    SegmentSummary,
    Simulation,
    SimulationJob,
    SimulationTurn,
    Topic,
    TopicLink,
)


def _seed_analysis_settings() -> None:
    with session_scope() as session:
        session.add_all(
            [
                AppSetting(setting_key="llm.base_url", setting_value="https://example.test/v1", is_secret=False),
                AppSetting(setting_key="llm.api_key", setting_value="secret-key", is_secret=True),
                AppSetting(setting_key="llm.chat_model", setting_value="gpt-5.4-mini", is_secret=False),
            ]
        )


def test_delete_conversation_removes_rows_and_upload_file(tmp_path, monkeypatch):
    data_root = tmp_path / "app_data"
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(data_root))
    init_db()

    upload_path = data_root / "uploads" / "seed.txt"
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    upload_path.write_text("seed", encoding="utf-8")

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

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(upload_path),
            source_file_hash="abc123",
            message_count_hint=1,
        )
        session.add(batch)
        session.flush()

        message = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=1,
            speaker_name="Tantless",
            speaker_role="self",
            timestamp="2025-03-02T20:18:04",
            content_text="你好",
            message_type="text",
        )
        session.add(message)
        session.flush()

        segment = Segment(
            conversation_id=conversation.id,
            start_message_id=message.id,
            end_message_id=message.id,
            start_time=message.timestamp,
            end_time=message.timestamp,
            message_count=1,
            self_message_count=1,
            other_message_count=0,
            segment_kind="isolated",
            source_message_ids=[message.id],
        )
        session.add(segment)
        session.flush()

        session.add(
            SegmentSummary(
                segment_id=segment.id,
                summary_text="打招呼",
                main_topics=["开场"],
                self_stance="主动",
                other_stance="未出现",
                emotional_tone="轻松",
                interaction_pattern="单次触达",
                has_conflict=False,
                has_repair=False,
                has_closeness_signal=False,
                outcome="等待回应",
                relationship_impact="neutral",
                confidence=0.8,
            )
        )
        topic = Topic(
            conversation_id=conversation.id,
            topic_name="开场",
            topic_summary="建立联系",
            first_seen_at=message.timestamp,
            last_seen_at=message.timestamp,
            segment_count=1,
            topic_status="ongoing",
        )
        session.add(topic)
        session.flush()
        session.add(TopicLink(topic_id=topic.id, segment_id=segment.id, link_reason="匹配", score=1.0))
        session.add(
            PersonaProfile(
                conversation_id=conversation.id,
                subject_role="other",
                global_persona_summary="轻松",
                style_traits=["简短"],
                conflict_traits=["回避"],
                relationship_specific_patterns=["接话"],
                evidence_segment_ids=[segment.id],
                confidence=0.8,
            )
        )
        session.add(
            RelationshipSnapshot(
                conversation_id=conversation.id,
                as_of_message_id=message.id,
                as_of_time=message.timestamp,
                relationship_temperature="warm",
                tension_level="low",
                openness_level="medium",
                initiative_balance="balanced",
                defensiveness_level="low",
                unresolved_conflict_flags=[],
                relationship_phase="warming",
                snapshot_summary="初步建立联系",
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
                payload_json={"import_id": batch.id},
            )
        )
        simulation = Simulation(
            conversation_id=conversation.id,
            target_message_id=message.id,
            mode="single_reply",
            replacement_content="换个说法",
            context_pack_snapshot={},
            branch_assessment={},
            first_reply_text="好的",
            impact_summary="更柔和",
            status="completed",
        )
        session.add(simulation)
        session.flush()
        session.add(
            SimulationJob(
                conversation_id=conversation.id,
                target_message_id=message.id,
                mode="short_thread",
                turn_count=4,
                replacement_content="如果你不忙，我们慢慢说也可以",
                status="queued",
                current_stage="queued",
                progress_percent=0,
                payload_json={
                    "queued_at": "2025-03-02T20:18:04Z",
                    "request": {
                        "conversation_id": conversation.id,
                        "target_message_id": message.id,
                        "mode": "short_thread",
                        "turn_count": 4,
                        "replacement_content": "如果你不忙，我们慢慢说也可以",
                    },
                },
                result_simulation_id=None,
            )
        )
        session.add(
            SimulationTurn(
                simulation_id=simulation.id,
                turn_index=1,
                speaker_role="other",
                message_text="好的",
                strategy_used="light_follow_up",
                state_after_turn={"openness_level": "medium"},
                generation_notes="seed",
            )
        )

    with TestClient(create_app()) as client:
        response = client.delete("/conversations/1")

    assert response.status_code == 204
    assert not upload_path.exists()

    with session_scope() as session:
        assert session.query(Conversation).count() == 0
        assert session.query(ImportBatch).count() == 0
        assert session.query(Message).count() == 0
        assert session.query(Segment).count() == 0
        assert session.query(SegmentSummary).count() == 0
        assert session.query(Topic).count() == 0
        assert session.query(TopicLink).count() == 0
        assert session.query(PersonaProfile).count() == 0
        assert session.query(RelationshipSnapshot).count() == 0
        assert session.query(AnalysisJob).count() == 0
        assert session.query(SimulationJob).count() == 0
        assert session.query(Simulation).count() == 0
        assert session.query(SimulationTurn).count() == 0


def test_delete_conversation_ignores_paths_outside_managed_uploads(tmp_path, monkeypatch):
    data_root = tmp_path / "app_data"
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(data_root))
    init_db()

    outside_path = tmp_path / "outside.txt"
    outside_path.write_text("do-not-delete", encoding="utf-8")

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

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(outside_path),
            source_file_hash="abc123",
            message_count_hint=0,
        )
        session.add(batch)

    with TestClient(create_app()) as client:
        response = client.delete("/conversations/1")

    assert response.status_code == 204
    assert outside_path.exists()


def test_delete_conversation_returns_404_for_missing_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()

    with TestClient(create_app()) as client:
        response = client.delete("/conversations/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found"}


def test_rerun_analysis_queues_new_job_and_clears_stale_simulations(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()
    _seed_analysis_settings()

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

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=1,
        )
        session.add(batch)
        session.flush()

        message = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=1,
            speaker_name="Tantless",
            speaker_role="self",
            timestamp="2025-03-02T20:18:04",
            content_text="你好",
            message_type="text",
        )
        session.add(message)
        session.flush()

        session.add(
            AnalysisJob(
                conversation_id=conversation.id,
                job_type="full_analysis",
                status="completed",
                current_stage="completed",
                progress_percent=100,
                retry_count=0,
                payload_json={"import_id": batch.id},
            )
        )
        simulation = Simulation(
            conversation_id=conversation.id,
            target_message_id=message.id,
            mode="single_reply",
            replacement_content="换个说法",
            context_pack_snapshot={},
            branch_assessment={},
            first_reply_text="好的",
            impact_summary="更柔和",
            status="completed",
        )
        session.add(simulation)
        session.flush()
        session.add(
            SimulationTurn(
                simulation_id=simulation.id,
                turn_index=1,
                speaker_role="other",
                message_text="好的",
                strategy_used="light_follow_up",
                state_after_turn={"openness_level": "medium"},
                generation_notes="seed",
            )
        )

    with TestClient(create_app()) as client:
        response = client.post("/conversations/1/rerun-analysis")

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["current_stage"] == "created"

    with session_scope() as session:
        assert session.query(AnalysisJob).count() == 2
        assert session.get(Conversation, 1).status == "queued"
        assert session.query(Simulation).count() == 0
        assert session.query(SimulationTurn).count() == 0


def test_start_analysis_queues_new_full_analysis_job_for_imported_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()
    _seed_analysis_settings()

    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="imported",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=1,
        )
        session.add(batch)
        session.flush()

        session.add(
            AnalysisJob(
                conversation_id=conversation.id,
                job_type="import_only",
                status="completed",
                current_stage="completed",
                progress_percent=100,
                retry_count=0,
                payload_json={"import_id": batch.id},
            )
        )

    with TestClient(create_app()) as client:
        response = client.post("/conversations/1/start-analysis")

    assert response.status_code == 202
    assert response.json()["status"] == "queued"
    assert response.json()["current_stage"] == "created"

    with session_scope() as session:
        jobs = session.query(AnalysisJob).order_by(AnalysisJob.id.asc()).all()
        assert [job.job_type for job in jobs] == ["import_only", "full_analysis"]
        assert jobs[-1].payload_json["import_id"] == 1
        assert session.get(Conversation, 1).status == "queued"


def test_start_analysis_rejects_queueing_when_model_settings_are_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()

    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="imported",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=1,
        )
        session.add(batch)
        session.flush()

        session.add(
            AnalysisJob(
                conversation_id=conversation.id,
                job_type="import_only",
                status="completed",
                current_stage="completed",
                progress_percent=100,
                retry_count=0,
                payload_json={"import_id": batch.id},
            )
        )

    with TestClient(create_app()) as client:
        response = client.post("/conversations/1/start-analysis")

    assert response.status_code == 400
    assert response.json() == {"detail": "Analysis model settings are incomplete"}

    with session_scope() as session:
        jobs = session.query(AnalysisJob).order_by(AnalysisJob.id.asc()).all()
        assert [job.job_type for job in jobs] == ["import_only"]
        assert session.get(Conversation, 1).status == "imported"


def test_rerun_analysis_returns_409_when_job_is_already_active(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()
    _seed_analysis_settings()

    with session_scope() as session:
        conversation = Conversation(
            title="梣ゥ",
            chat_type="private",
            self_display_name="Tantless",
            other_display_name="梣ゥ",
            source_format="qq_chat_exporter_v5",
            status="analyzing",
        )
        session.add(conversation)
        session.flush()

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=1,
        )
        session.add(batch)
        session.flush()

        session.add(
            AnalysisJob(
                conversation_id=conversation.id,
                job_type="full_analysis",
                status="running",
                current_stage="parsing",
                progress_percent=5,
                retry_count=0,
                payload_json={"import_id": batch.id},
            )
        )

    with TestClient(create_app()) as client:
        response = client.post("/conversations/1/rerun-analysis")

    assert response.status_code == 409
    assert response.json() == {"detail": "Analysis already queued or running"}


def test_rerun_analysis_uses_latest_import_batch(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()
    _seed_analysis_settings()

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

        first_batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="old.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "old.txt"),
            source_file_hash="old-hash",
            message_count_hint=1,
        )
        second_batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="new.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "new.txt"),
            source_file_hash="new-hash",
            message_count_hint=1,
        )
        session.add_all([first_batch, second_batch])

    with TestClient(create_app()) as client:
        response = client.post("/conversations/1/rerun-analysis")

    assert response.status_code == 202

    with session_scope() as session:
        latest_job = session.query(AnalysisJob).order_by(AnalysisJob.id.desc()).first()
        assert latest_job is not None
        assert latest_job.payload_json["import_id"] == 2


def test_rerun_analysis_returns_400_when_no_import_batch_exists(tmp_path, monkeypatch):
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

    with TestClient(create_app()) as client:
        response = client.post("/conversations/1/rerun-analysis")

    assert response.status_code == 400
    assert response.json() == {"detail": "Conversation has no import batch"}
