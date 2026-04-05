from fastapi.testclient import TestClient

from if_then_mvp.api import create_app
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import (
    Conversation,
    ImportBatch,
    Message,
    PersonaProfile,
    RelationshipSnapshot,
    Segment,
    SegmentSummary,
    Simulation,
    SimulationTurn,
    Topic,
    TopicLink,
)


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

        batch = ImportBatch(
            conversation_id=conversation.id,
            source_file_name="聊天记录.txt",
            source_file_path=str(tmp_path / "app_data" / "uploads" / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=2,
        )
        session.add(batch)
        session.flush()

        prior_other = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=1,
            speaker_name="梣ゥ",
            speaker_role="other",
            timestamp="2025-03-02T20:17:00",
            content_text="先聊两句",
            message_type="text",
        )
        prior_self = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=2,
            speaker_name="Tantless",
            speaker_role="self",
            timestamp="2025-03-02T20:17:30",
            content_text="好呀",
            message_type="text",
        )
        target_other = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=3,
            speaker_name="梣ゥ",
            speaker_role="other",
            timestamp="2025-03-02T20:18:03",
            content_text="我是凉ゥ",
            message_type="text",
        )
        target_self = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=4,
            speaker_name="Tantless",
            speaker_role="self",
            timestamp="2025-03-02T20:18:04",
            content_text="我们已成功添加为好友，现在可以开始聊天啦～",
            message_type="text",
        )
        session.add_all([prior_other, prior_self, target_other, target_self])
        session.flush()

        prior_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=prior_other.id,
            end_message_id=prior_self.id,
            start_time="2025-03-02T20:17:00",
            end_time="2025-03-02T20:17:30",
            message_count=2,
            self_message_count=1,
            other_message_count=1,
            segment_kind="normal",
            source_message_ids=[prior_other.id, prior_self.id],
        )
        target_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=target_other.id,
            end_message_id=target_self.id,
            start_time="2025-03-02T20:18:03",
            end_time="2025-03-02T20:18:04",
            message_count=2,
            self_message_count=1,
            other_message_count=1,
            segment_kind="normal",
            source_message_ids=[target_other.id, target_self.id],
        )
        session.add_all([prior_segment, target_segment])
        session.flush()

        session.add(
            SegmentSummary(
                segment_id=prior_segment.id,
                summary_text="这是一次轻松的开场互动。",
                main_topics=["开场聊天"],
                self_stance="积极回应",
                other_stance="轻松开启聊天",
                emotional_tone="轻松",
                interaction_pattern="日常互动",
                has_conflict=False,
                has_repair=False,
                has_closeness_signal=False,
                outcome="继续聊天",
                relationship_impact="neutral_positive",
                confidence=0.8,
            )
        )
        session.add(
            Topic(
                conversation_id=conversation.id,
                topic_name="开场聊天",
                topic_summary="双方在建立联系。",
                first_seen_at="2025-03-02T20:18:03",
                last_seen_at="2025-03-02T20:18:04",
                segment_count=1,
                topic_status="ongoing",
            )
        )
        session.flush()
        session.add(
            TopicLink(
                topic_id=1,
                segment_id=prior_segment.id,
                link_reason="段摘要高度相似",
                score=1.0,
            )
        )
        session.add(
            RelationshipSnapshot(
                conversation_id=conversation.id,
                as_of_message_id=prior_self.id,
                as_of_time="2025-03-02T20:17:30",
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
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.8,
                ),
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="other",
                    global_persona_summary="轻松",
                    style_traits=["简短"],
                    conflict_traits=["回避"],
                    relationship_specific_patterns=["用玩笑接话"],
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.8,
                ),
            ]
        )

    with TestClient(create_app()) as client:
        response = client.post(
            "/simulations",
            json={
                "conversation_id": 1,
                "target_message_id": 4,
                "replacement_content": "如果你方便的话，我们慢慢聊就好",
                "mode": "short_thread",
                "turn_count": 4,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["first_reply_text"]
    assert len(body["simulated_turns"]) == 4
    assert [turn["turn_index"] for turn in body["simulated_turns"]] == [1, 2, 3, 4]

    with session_scope() as session:
        simulation = session.query(Simulation).one()
        turns = session.query(SimulationTurn).order_by(SimulationTurn.turn_index.asc()).all()
        assert simulation.first_reply_text == body["first_reply_text"]
        assert simulation.context_pack_snapshot["related_topic_digests"]
        assert len(turns) == 4


def test_simulations_endpoint_supports_single_reply_mode(tmp_path, monkeypatch):
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

        session.add_all(
            [
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=1,
                    speaker_name="梣ゥ",
                    speaker_role="other",
                    timestamp="2025-03-02T20:18:03",
                    content_text="在吗",
                    message_type="text",
                ),
                Message(
                    conversation_id=conversation.id,
                    import_id=batch.id,
                    sequence_no=2,
                    speaker_name="Tantless",
                    speaker_role="self",
                    timestamp="2025-03-02T20:18:04",
                    content_text="在的",
                    message_type="text",
                ),
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

    with TestClient(create_app()) as client:
        response = client.post(
            "/simulations",
            json={
                "conversation_id": 1,
                "target_message_id": 2,
                "replacement_content": "如果你现在忙，晚点聊也可以",
                "mode": "single_reply",
                "turn_count": 4,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert body["first_reply_text"]
    assert body["simulated_turns"] == []


def test_simulations_endpoint_returns_400_when_target_is_not_covered_by_segments(tmp_path, monkeypatch):
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

        session.add(
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=1,
                speaker_name="Tantless",
                speaker_role="self",
                timestamp="2025-03-02T20:18:04",
                content_text="没有段覆盖我",
                message_type="text",
            )
        )

    with TestClient(create_app()) as client:
        response = client.post(
            "/simulations",
            json={
                "conversation_id": 1,
                "target_message_id": 1,
                "replacement_content": "换个说法",
                "mode": "single_reply",
                "turn_count": 0,
            },
        )

    assert response.status_code == 400
    assert "not covered by any segment" in response.json()["detail"]
