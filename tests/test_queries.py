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
    Topic,
)


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
            resource_items=[{"kind": "emoji", "value": "wave"}],
        )
        session.add(message)
        session.flush()

        segment = Segment(
            conversation_id=conversation.id,
            start_message_id=message.id,
            end_message_id=message.id,
            start_time="2025-03-02T20:18:04",
            end_time="2025-03-02T20:18:04",
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
                as_of_message_id=message.id,
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
                evidence_segment_ids=[segment.id],
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
                payload_json={
                    "import_id": batch.id,
                    "progress": {
                        "overall_total_units": 11,
                        "overall_completed_units": 11,
                        "current_stage_total_units": 11,
                        "current_stage_completed_units": 11,
                        "status_message": "completed 11/11 units",
                    },
                },
            )
        )
        session.add(AppSetting(setting_key="llm.chat_model", setting_value="gpt-4.1-mini", is_secret=False))

    with TestClient(create_app()) as client:
        conversations_response = client.get("/conversations")
        assert conversations_response.status_code == 200
        assert conversations_response.json() == [
            {
                "id": 1,
                "title": "梣ゥ",
                "chat_type": "private",
                "self_display_name": "Tantless",
                "other_display_name": "梣ゥ",
                "source_format": "qq_chat_exporter_v5",
                "status": "ready",
            }
        ]

        conversation_response = client.get("/conversations/1")
        assert conversation_response.status_code == 200
        assert conversation_response.json()["title"] == "梣ゥ"

        job_response = client.get("/jobs/1")
        assert job_response.status_code == 200
        assert job_response.json() == {
            "id": 1,
            "status": "completed",
            "current_stage": "completed",
            "progress_percent": 100,
            "current_stage_percent": 100,
            "current_stage_total_units": 11,
            "current_stage_completed_units": 11,
            "overall_total_units": 11,
            "overall_completed_units": 11,
            "status_message": "completed 11/11 units",
        }

        messages_response = client.get("/conversations/1/messages")
        assert messages_response.status_code == 200
        assert messages_response.json() == [
            {
                "id": 1,
                "sequence_no": 1,
                "speaker_name": "Tantless",
                "speaker_role": "self",
                "timestamp": "2025-03-02T20:18:04",
                "content_text": "你好",
                "message_type": "text",
                "resource_items": [{"kind": "emoji", "value": "wave"}],
            }
        ]

        message_response = client.get("/messages/1")
        assert message_response.status_code == 200
        assert message_response.json()["content_text"] == "你好"

        segments_response = client.get("/conversations/1/segments")
        assert segments_response.status_code == 200
        assert segments_response.json() == [
            {
                "id": 1,
                "start_message_id": 1,
                "end_message_id": 1,
                "start_time": "2025-03-02T20:18:04",
                "end_time": "2025-03-02T20:18:04",
                "message_count": 1,
                "segment_kind": "isolated",
            }
        ]

        topics_response = client.get("/conversations/1/topics")
        assert topics_response.status_code == 200
        assert topics_response.json() == [
            {
                "id": 1,
                "topic_name": "开场聊天",
                "topic_summary": "建立联系",
                "topic_status": "ongoing",
            }
        ]

        profile_response = client.get("/conversations/1/profile")
        assert profile_response.status_code == 200
        assert profile_response.json() == [
            {
                "subject_role": "other",
                "global_persona_summary": "轻松",
                "style_traits": ["简短"],
                "conflict_traits": ["回避"],
                "relationship_specific_patterns": ["接梗"],
                "confidence": 0.8,
            }
        ]

        timeline_response = client.get("/conversations/1/timeline-state?at=2025-03-02T20:18:04")
        assert timeline_response.status_code == 200
        assert timeline_response.json() == {
            "id": 1,
            "as_of_message_id": 1,
            "as_of_time": "2025-03-02T20:18:04",
            "relationship_temperature": "warm",
            "tension_level": "low",
            "openness_level": "medium",
            "initiative_balance": "self_leading",
            "defensiveness_level": "low",
            "unresolved_conflict_flags": [],
            "relationship_phase": "warming",
            "snapshot_summary": "初步建立联系",
        }

        settings_response = client.get("/settings")
        assert settings_response.status_code == 200
        assert settings_response.json() == [
            {
                "setting_key": "llm.chat_model",
                "setting_value": "gpt-4.1-mini",
                "is_secret": False,
            }
        ]

        put_response = client.put(
            "/settings",
            json={"setting_key": "llm.chat_model", "setting_value": "gpt-4.1", "is_secret": False},
        )
        assert put_response.status_code == 200
        assert put_response.json() == {
            "setting_key": "llm.chat_model",
            "setting_value": "gpt-4.1",
            "is_secret": False,
        }

        settings_after_put = client.get("/settings")
        assert settings_after_put.status_code == 200
        assert settings_after_put.json() == [
            {
                "setting_key": "llm.chat_model",
                "setting_value": "gpt-4.1",
                "is_secret": False,
            }
        ]


def test_message_queries_validate_pagination_and_missing_conversation(tmp_path, monkeypatch):
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

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=3,
        )
        session.add(batch)
        session.flush()

        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=1,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:03",
                    content_text="第一句",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=2,
                    speaker_name="Tantless",
                    speaker_role="self",
                    timestamp="2025-03-02T20:18:04",
                    content_text="第二句 关键词",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=3,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:05",
                    content_text="第三句",
                    message_type="text",
                ),
            ]
        )

    with TestClient(create_app()) as client:
        response = client.get("/conversations/1/messages?after=1&limit=1")
        assert response.status_code == 200
        assert [item["sequence_no"] for item in response.json()] == [2]

        response = client.get("/conversations/1/messages?before=3&keyword=关键词")
        assert response.status_code == 200
        assert [item["sequence_no"] for item in response.json()] == [2]

        response = client.get("/conversations/1/messages?limit=-1")
        assert response.status_code == 422

        response = client.get("/conversations/1/messages?before=-1")
        assert response.status_code == 422

        response = client.get("/conversations/1/messages?after=-1")
        assert response.status_code == 422

        for path in (
            "/conversations/999/messages",
            "/conversations/999/segments",
            "/conversations/999/topics",
            "/conversations/999/profile",
            "/conversations/999/timeline-state?at=2025-03-02T20:18:04",
        ):
            response = client.get(path)
            assert response.status_code == 404
            assert response.json() == {"detail": "Conversation not found"}


def test_conversation_jobs_endpoint_returns_latest_jobs_first(tmp_path, monkeypatch):
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
                AnalysisJob(
                    conversation_id=conversation.id,
                    job_type="full_analysis",
                    status="completed",
                    current_stage="completed",
                    progress_percent=100,
                    retry_count=0,
                    payload_json={
                        "progress": {
                            "overall_total_units": 4,
                            "overall_completed_units": 4,
                            "current_stage_total_units": 4,
                            "current_stage_completed_units": 4,
                            "status_message": "job 1 done",
                        }
                    },
                ),
                AnalysisJob(
                    conversation_id=conversation.id,
                    job_type="full_analysis",
                    status="running",
                    current_stage="topics",
                    progress_percent=60,
                    retry_count=0,
                    payload_json={
                        "progress": {
                            "overall_total_units": 10,
                            "overall_completed_units": 6,
                            "current_stage_total_units": 5,
                            "current_stage_completed_units": 3,
                            "status_message": "job 2 running",
                        }
                    },
                ),
                AnalysisJob(
                    conversation_id=conversation.id,
                    job_type="full_analysis",
                    status="queued",
                    current_stage="queued",
                    progress_percent=0,
                    retry_count=0,
                    payload_json={
                        "progress": {
                            "overall_total_units": 10,
                            "overall_completed_units": 0,
                            "current_stage_total_units": 1,
                            "current_stage_completed_units": 0,
                            "status_message": "job 3 queued",
                        }
                    },
                ),
            ]
        )

    with TestClient(create_app()) as client:
        response = client.get("/conversations/1/jobs?limit=2")

    assert response.status_code == 200
    assert response.json() == [
        {
            "id": 3,
            "status": "queued",
            "current_stage": "queued",
            "progress_percent": 0,
            "current_stage_percent": 0,
            "current_stage_total_units": 1,
            "current_stage_completed_units": 0,
            "overall_total_units": 10,
            "overall_completed_units": 0,
            "status_message": "job 3 queued",
        },
        {
            "id": 2,
            "status": "running",
            "current_stage": "topics",
            "progress_percent": 60,
            "current_stage_percent": 60,
            "current_stage_total_units": 5,
            "current_stage_completed_units": 3,
            "overall_total_units": 10,
            "overall_completed_units": 6,
            "status_message": "job 2 running",
        },
    ]


def test_conversation_jobs_endpoint_returns_404_for_missing_conversation(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()

    with TestClient(create_app()) as client:
        response = client.get("/conversations/999/jobs")

    assert response.status_code == 404
    assert response.json() == {"detail": "Conversation not found"}


def test_conversation_jobs_endpoint_validates_limit_bounds(tmp_path, monkeypatch):
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
        response = client.get("/conversations/1/jobs?limit=0")
        assert response.status_code == 422

        response = client.get("/conversations/1/jobs?limit=51")
        assert response.status_code == 422


def test_conversation_jobs_endpoint_returns_empty_list_for_conversation_without_jobs(tmp_path, monkeypatch):
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
        response = client.get("/conversations/1/jobs")

    assert response.status_code == 200
    assert response.json() == []


def test_message_queries_support_descending_order_and_context_lookup(tmp_path, monkeypatch):
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

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=4,
        )
        session.add(batch)
        session.flush()

        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=1,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:01",
                    content_text="第一句",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=2,
                    speaker_name="Tantless",
                    speaker_role="self",
                    timestamp="2025-03-02T20:18:02",
                    content_text="第二句",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=3,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:03",
                    content_text="第三句",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=4,
                    speaker_name="Tantless",
                    speaker_role="self",
                    timestamp="2025-03-02T20:18:04",
                    content_text="第四句",
                    message_type="text",
                ),
            ]
        )

    with TestClient(create_app()) as client:
        response = client.get("/conversations/1/messages?limit=2&order=desc")
        assert response.status_code == 200
        assert [item["sequence_no"] for item in response.json()] == [4, 3]

        context_response = client.get("/messages/3/context?radius=1")
        assert context_response.status_code == 200
        assert context_response.json()["target"]["sequence_no"] == 3
        assert [item["sequence_no"] for item in context_response.json()["before"]] == [2]
        assert [item["sequence_no"] for item in context_response.json()["after"]] == [4]


def test_timeline_state_prefers_latest_same_second_snapshot(tmp_path, monkeypatch):
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

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=2,
        )
        session.add(batch)
        session.flush()

        second_message = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=2,
            speaker_name="Tantless",
            speaker_role="self",
            timestamp="2025-03-02T20:18:04",
            content_text="同秒第二句",
            message_type="text",
        )
        first_message = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=1,
            speaker_name="梣ゥ",
            speaker_role="other",
            timestamp="2025-03-02T20:18:04",
            content_text="先说一句",
            message_type="text",
        )
        session.add_all([first_message, second_message])
        session.flush()

        session.add_all(
            [
                RelationshipSnapshot(
                    conversation_id=conversation.id,
                    as_of_message_id=first_message.id,
                    as_of_time="2025-03-02T20:18:04",
                    relationship_temperature="warm",
                    tension_level="low",
                    openness_level="medium",
                    initiative_balance="balanced",
                    defensiveness_level="low",
                    unresolved_conflict_flags=[],
                    relationship_phase="warming",
                    snapshot_summary="第一条快照",
                ),
                RelationshipSnapshot(
                    conversation_id=conversation.id,
                    as_of_message_id=second_message.id,
                    as_of_time="2025-03-02T20:18:04",
                    relationship_temperature="warmer",
                    tension_level="low",
                    openness_level="high",
                    initiative_balance="balanced",
                    defensiveness_level="low",
                    unresolved_conflict_flags=[],
                    relationship_phase="warming",
                    snapshot_summary="第二条快照",
                ),
            ]
        )

    with TestClient(create_app()) as client:
        response = client.get("/conversations/1/timeline-state?at=2025-03-02T20:18:04")
        assert response.status_code == 200
        assert response.json()["as_of_message_id"] == 2
        assert response.json()["snapshot_summary"] == "第二条快照"
