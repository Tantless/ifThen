from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import BaseModel
from sqlalchemy import select

from if_then_mvp.api import (
    _load_related_topic_digests,
    _message_to_context_dict,
    _persona_to_context_dict,
    _segment_to_context_dict,
    _snapshot_to_context_dict,
    create_app,
)
from if_then_mvp.context_builder import build_conversation_context_pack
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import (
    Conversation,
    ImportBatch,
    Message,
    PersonaProfile,
    RelationshipSnapshot,
    Segment,
    SegmentSummary,
    SimulationJob,
    Topic,
    TopicLink,
)
from if_then_mvp.retrieval import build_context_pack
from if_then_mvp.simulation import (
    BRANCH_SYSTEM_PROMPT,
    FIRST_REPLY_SYSTEM_PROMPT,
    NEXT_TURN_SYSTEM_PROMPT,
    BranchAssessmentPayload,
    FirstReplyPayload,
    NextTurnPayload,
    TurnStatePayload,
    assess_branch,
    generate_first_reply,
    simulate_short_thread,
)
from if_then_mvp.worker import run_next_simulation_job


def _state_payload(
    *,
    relationship_temperature: str = "warm",
    tension_level: str = "low",
    openness_level: str = "medium",
    initiative_balance: str = "balanced",
    defensiveness_level: str = "low",
    relationship_phase: str = "warming",
    active_sensitive_topics: list[str] | None = None,
    state_rationale: str = "基于当前分支对话更新。",
) -> dict:
    return {
        "relationship_temperature": relationship_temperature,
        "tension_level": tension_level,
        "openness_level": openness_level,
        "initiative_balance": initiative_balance,
        "defensiveness_level": defensiveness_level,
        "relationship_phase": relationship_phase,
        "active_sensitive_topics": active_sensitive_topics or [],
        "state_rationale": state_rationale,
    }


class FakeSimulationLLM:
    def __init__(self, responses: list[BaseModel]) -> None:
        self._responses = responses
        self.calls: list[dict] = []

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        response = self._responses[len(self.calls) - 1]
        assert isinstance(response, response_model)
        return response


def _seed_engine_context_pack(
    tmp_path,
    monkeypatch,
    *,
    replacement_content: str,
) -> dict:
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
        topic = Topic(
            conversation_id=conversation.id,
            topic_name="开场聊天",
            topic_summary="双方在建立联系。",
            first_seen_at="2025-03-02T20:18:03",
            last_seen_at="2025-03-02T20:18:04",
            segment_count=1,
            topic_status="ongoing",
        )
        session.add(topic)
        session.flush()
        session.add(
            TopicLink(
                topic_id=topic.id,
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

        target_message = session.get(Message, target_self.id)
        return build_conversation_context_pack(
            session,
            conversation_id=conversation.id,
            target_message=target_message,
            replacement_content=replacement_content,
        )


def _seed_uncovered_target_case(tmp_path, monkeypatch) -> None:
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


def test_context_builder_prioritizes_sensitive_future_evidence_on_target_topic(tmp_path, monkeypatch):
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
            source_file_path=str(tmp_path / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=7,
        )
        session.add(batch)
        session.flush()

        messages = [
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=1,
                speaker_name="梣ゥ",
                speaker_role="other",
                timestamp="2025-03-02T20:15:00",
                content_text="我们先随便聊聊",
                message_type="text",
            ),
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=2,
                speaker_name="Tantless",
                speaker_role="self",
                timestamp="2025-03-02T20:16:00",
                content_text="我想问下你会不会觉得我太急",
                message_type="text",
            ),
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=3,
                speaker_name="梣ゥ",
                speaker_role="other",
                timestamp="2025-03-02T20:17:00",
                content_text="先别太快推进吧",
                message_type="text",
            ),
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=4,
                speaker_name="Tantless",
                speaker_role="self",
                timestamp="2025-03-02T20:18:00",
                content_text="目标消息",
                message_type="text",
            ),
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=5,
                speaker_name="梣ゥ",
                speaker_role="other",
                timestamp="2025-03-02T20:22:00",
                content_text="我还是想慢一点，不太适合现在说这个",
                message_type="text",
            ),
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=6,
                speaker_name="梣ゥ",
                speaker_role="other",
                timestamp="2025-03-02T20:24:00",
                content_text="刚刚路上看到一只猫",
                message_type="text",
            ),
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=7,
                speaker_name="梣ゥ",
                speaker_role="other",
                timestamp="2025-03-02T20:25:00",
                content_text="天气也还行",
                message_type="text",
            ),
        ]
        session.add_all(messages)
        session.flush()

        prior_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=messages[0].id,
            end_message_id=messages[2].id,
            start_time="2025-03-02T20:15:00",
            end_time="2025-03-02T20:17:00",
            message_count=3,
            self_message_count=1,
            other_message_count=2,
            segment_kind="normal",
            source_message_ids=[messages[0].id, messages[1].id, messages[2].id],
        )
        target_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=messages[3].id,
            end_message_id=messages[3].id,
            start_time="2025-03-02T20:18:00",
            end_time="2025-03-02T20:18:00",
            message_count=1,
            self_message_count=1,
            other_message_count=0,
            segment_kind="normal",
            source_message_ids=[messages[3].id],
        )
        future_sensitive_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=messages[4].id,
            end_message_id=messages[4].id,
            start_time="2025-03-02T20:22:00",
            end_time="2025-03-02T20:22:00",
            message_count=1,
            self_message_count=0,
            other_message_count=1,
            segment_kind="normal",
            source_message_ids=[messages[4].id],
        )
        future_smalltalk_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=messages[5].id,
            end_message_id=messages[5].id,
            start_time="2025-03-02T20:24:00",
            end_time="2025-03-02T20:24:00",
            message_count=1,
            self_message_count=0,
            other_message_count=1,
            segment_kind="normal",
            source_message_ids=[messages[5].id],
        )
        future_weather_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=messages[6].id,
            end_message_id=messages[6].id,
            start_time="2025-03-02T20:25:00",
            end_time="2025-03-02T20:25:00",
            message_count=1,
            self_message_count=0,
            other_message_count=1,
            segment_kind="normal",
            source_message_ids=[messages[6].id],
        )
        session.add_all(
            [
                prior_segment,
                target_segment,
                future_sensitive_segment,
                future_smalltalk_segment,
                future_weather_segment,
            ]
        )
        session.flush()

        session.add_all(
            [
                SegmentSummary(
                    segment_id=prior_segment.id,
                    summary_text="之前已经出现推进节奏和边界感的试探。",
                    main_topics=["推进节奏"],
                    self_stance="想靠近",
                    other_stance="提醒慢一点",
                    emotional_tone="谨慎",
                    interaction_pattern="边界试探",
                    has_conflict=False,
                    has_repair=False,
                    has_closeness_signal=False,
                    outcome="暂时缓和",
                    relationship_impact="mixed",
                    confidence=0.8,
                ),
                SegmentSummary(
                    segment_id=future_sensitive_segment.id,
                    summary_text="对方明确表示想慢一点，暂时不适合推进。",
                    main_topics=["推进节奏", "边界"],
                    self_stance="未出现",
                    other_stance="明确保留",
                    emotional_tone="克制",
                    interaction_pattern="边界确认",
                    has_conflict=True,
                    has_repair=False,
                    has_closeness_signal=False,
                    outcome="保持边界",
                    relationship_impact="negative",
                    confidence=0.9,
                ),
                SegmentSummary(
                    segment_id=future_smalltalk_segment.id,
                    summary_text="后续只是轻松闲聊，没有关系推进。",
                    main_topics=["日常闲聊"],
                    self_stance="未出现",
                    other_stance="闲聊",
                    emotional_tone="轻松",
                    interaction_pattern="日常互动",
                    has_conflict=False,
                    has_repair=False,
                    has_closeness_signal=False,
                    outcome="继续聊天",
                    relationship_impact="neutral",
                    confidence=0.7,
                ),
                SegmentSummary(
                    segment_id=future_weather_segment.id,
                    summary_text="天气话题继续延伸。",
                    main_topics=["天气"],
                    self_stance="未出现",
                    other_stance="闲聊",
                    emotional_tone="轻松",
                    interaction_pattern="日常互动",
                    has_conflict=False,
                    has_repair=False,
                    has_closeness_signal=False,
                    outcome="继续聊天",
                    relationship_impact="neutral",
                    confidence=0.6,
                ),
            ]
        )

        target_topic = Topic(
            conversation_id=conversation.id,
            topic_name="推进节奏",
            topic_summary="围绕聊天推进速度与边界的讨论。",
            first_seen_at="2025-03-02T20:15:00",
            last_seen_at="2025-03-02T20:22:00",
            segment_count=3,
            topic_status="ongoing",
        )
        smalltalk_topic = Topic(
            conversation_id=conversation.id,
            topic_name="日常闲聊",
            topic_summary="轻松过渡话题。",
            first_seen_at="2025-03-02T20:24:00",
            last_seen_at="2025-03-02T20:24:00",
            segment_count=1,
            topic_status="ongoing",
        )
        weather_topic = Topic(
            conversation_id=conversation.id,
            topic_name="天气",
            topic_summary="无关紧要的天气闲聊。",
            first_seen_at="2025-03-02T20:25:00",
            last_seen_at="2025-03-02T20:25:00",
            segment_count=1,
            topic_status="ongoing",
        )
        session.add_all([target_topic, smalltalk_topic, weather_topic])
        session.flush()

        session.add_all(
            [
                TopicLink(topic_id=target_topic.id, segment_id=prior_segment.id, link_reason="同一边界主题", score=0.91),
                TopicLink(topic_id=target_topic.id, segment_id=target_segment.id, link_reason="目标段仍在试探推进速度", score=0.95),
                TopicLink(topic_id=target_topic.id, segment_id=future_sensitive_segment.id, link_reason="后续明确拒绝推进，属于同主题强约束", score=0.66),
                TopicLink(topic_id=smalltalk_topic.id, segment_id=future_smalltalk_segment.id, link_reason="后续闲聊", score=0.99),
                TopicLink(topic_id=weather_topic.id, segment_id=future_weather_segment.id, link_reason="无关天气闲聊", score=0.98),
            ]
        )
        session.add(
            RelationshipSnapshot(
                conversation_id=conversation.id,
                as_of_message_id=messages[2].id,
                as_of_time="2025-03-02T20:17:00",
                relationship_temperature="neutral",
                tension_level="medium",
                openness_level="low",
                initiative_balance="self_leading",
                defensiveness_level="medium",
                unresolved_conflict_flags=["推进节奏"],
                relationship_phase="uncertain",
                snapshot_summary="推进速度仍是敏感点。",
            )
        )

        session.add_all(
            [
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="self",
                    global_persona_summary="会主动补充解释",
                    style_traits=["直白"],
                    conflict_traits=["解释"],
                    relationship_specific_patterns=["急于确认"],
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.8,
                ),
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="other",
                    global_persona_summary="会在有压力时保留边界",
                    style_traits=["简短"],
                    conflict_traits=["回避"],
                    relationship_specific_patterns=["先降速"],
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.8,
                ),
            ]
        )

        target_message = session.get(Message, messages[3].id)
        context_pack = build_conversation_context_pack(
            session,
            conversation_id=conversation.id,
            target_message=target_message,
            replacement_content="如果你方便，我们慢慢聊也可以",
        )

    assert context_pack["future_evidence_digests"][0]["supporting_segment_id"] == future_sensitive_segment.id
    assert context_pack["future_evidence_digests"][0]["topic_name"] == "推进节奏"
    assert context_pack["retrieval_budget"]["future_evidence_digests"] == {
        "limit": 3,
        "candidate_count": 3,
        "selected_count": 3,
        "overflow_count": 0,
    }
    assert context_pack["retrieval_trace"]["future_evidence_digests"][0]["selection_reasons"] == [
        "target_topic_overlap",
        "sensitive_future_constraint",
        "stable_topic_recurrence",
        "future_time_proximity",
    ]
    assert context_pack["retrieval_trace"]["future_evidence_digests"][0]["selected"] is True
    assert context_pack["retrieval_trace"]["future_evidence_digests"][0]["supporting_segment_id"] == future_sensitive_segment.id
    assert context_pack["related_topic_digests"][0]["topic_name"] == "推进节奏"
    assert context_pack["retrieval_trace"]["related_topic_digests"][0]["selection_reasons"][0] == "target_topic_overlap"


def test_context_builder_keeps_snapshot_and_prior_segment_when_topic_links_missing(tmp_path, monkeypatch):
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
            source_file_path=str(tmp_path / "seed.txt"),
            source_file_hash="abc123",
            message_count_hint=3,
        )
        session.add(batch)
        session.flush()

        messages = [
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=1,
                speaker_name="梣ゥ",
                speaker_role="other",
                timestamp="2025-03-02T20:10:00",
                content_text="先随便说两句",
                message_type="text",
            ),
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=2,
                speaker_name="梣ゥ",
                speaker_role="other",
                timestamp="2025-03-02T20:12:00",
                content_text="晚点再看也行",
                message_type="text",
            ),
            Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=3,
                speaker_name="Tantless",
                speaker_role="self",
                timestamp="2025-03-02T20:13:00",
                content_text="目标消息",
                message_type="text",
            ),
        ]
        session.add_all(messages)
        session.flush()

        prior_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=messages[0].id,
            end_message_id=messages[1].id,
            start_time="2025-03-02T20:10:00",
            end_time="2025-03-02T20:12:00",
            message_count=2,
            self_message_count=0,
            other_message_count=2,
            segment_kind="normal",
            source_message_ids=[messages[0].id, messages[1].id],
        )
        target_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=messages[2].id,
            end_message_id=messages[2].id,
            start_time="2025-03-02T20:13:00",
            end_time="2025-03-02T20:13:00",
            message_count=1,
            self_message_count=1,
            other_message_count=0,
            segment_kind="normal",
            source_message_ids=[messages[2].id],
        )
        session.add_all([prior_segment, target_segment])
        session.flush()

        session.add(
            RelationshipSnapshot(
                conversation_id=conversation.id,
                as_of_message_id=messages[1].id,
                as_of_time="2025-03-02T20:12:00",
                relationship_temperature="neutral",
                tension_level="low",
                openness_level="medium",
                initiative_balance="balanced",
                defensiveness_level="low",
                unresolved_conflict_flags=[],
                relationship_phase="warming",
                snapshot_summary="还在正常聊天。",
            )
        )
        session.add_all(
            [
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="self",
                    global_persona_summary="正常沟通",
                    style_traits=["短句"],
                    conflict_traits=["解释"],
                    relationship_specific_patterns=["顺着聊"],
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.7,
                ),
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="other",
                    global_persona_summary="偏轻松",
                    style_traits=["短句"],
                    conflict_traits=["回避"],
                    relationship_specific_patterns=["先回应一下"],
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.7,
                ),
            ]
        )

        target_message = session.get(Message, messages[2].id)
        context_pack = build_conversation_context_pack(
            session,
            conversation_id=conversation.id,
            target_message=target_message,
            replacement_content="如果你方便，我们慢慢聊",
        )

    assert context_pack["related_topic_digests"] == []
    assert context_pack["future_evidence_digests"] == []
    assert context_pack["same_day_prior_segments"][0]["segment_id"] == prior_segment.id
    assert context_pack["base_relationship_snapshot"]["relationship_phase"] == "warming"
    assert context_pack["retrieval_budget"]["related_topic_digests"]["candidate_count"] == 0
    assert context_pack["retrieval_trace"]["related_topic_digests"] == []
    assert context_pack["retrieval_warnings"] == ["related_topic_digests_empty", "future_evidence_digests_empty"]


def test_post_simulations_returns_queued_job_and_latest_job_list(tmp_path, monkeypatch):
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
            source_file_path=str(tmp_path / "seed.txt"),
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

    with TestClient(create_app()) as client:
        create_response = client.post(
            "/simulations",
            json={
                "conversation_id": 1,
                "target_message_id": 2,
                "replacement_content": "如果你不忙，我们慢慢说也可以",
                "mode": "short_thread",
                "turn_count": 4,
            },
        )
        list_response = client.get("/conversations/1/simulation-jobs?limit=1")

    assert create_response.status_code == 202
    body = create_response.json()
    assert body["status"] == "queued"
    assert body["current_stage"] == "queued"
    assert body["progress_percent"] == 0
    assert body["result_simulation_id"] is None

    assert list_response.status_code == 200
    assert list_response.json()[0]["id"] == body["id"]

    with session_scope() as session:
        job = session.query(SimulationJob).one()
        assert job.status == "queued"
        assert job.current_stage == "queued"
        assert job.result_simulation_id is None
        assert "request" not in job.payload_json
        assert "replacement_content" not in str(job.payload_json)


def test_simulation_engine_returns_first_reply_and_short_thread(tmp_path, monkeypatch):
    context_pack = _seed_engine_context_pack(
        tmp_path,
        monkeypatch,
        replacement_content="如果你方便的话，我们慢慢聊就好",
    )

    fake_llm = FakeSimulationLLM(
        [
            BranchAssessmentPayload(
                branch_direction="closer",
                state_shift_summary="新说法更柔和，降低了推进压力，让对方更容易顺势接话。",
                other_immediate_feeling="更放松",
                reply_strategy="light_follow_up",
                risk_flags=[],
                confidence=0.82,
            ),
            FirstReplyPayload(
                first_reply_text="好呀，那我们就慢慢聊，别着急。",
                strategy_used="light_follow_up",
                first_reply_style_notes="延续对方偏轻松的接话风格。",
                state_after_turn=TurnStatePayload(**_state_payload(openness_level="high")),
            ),
            NextTurnPayload(
                message_text="好，那我就顺着慢慢说。",
                strategy_used="self_follow_up",
                state_after_turn=TurnStatePayload(**_state_payload(openness_level="high")),
                generation_notes="我方顺着放松的氛围继续说下去。",
                should_stop=False,
                stopping_reason=None,
            ),
            NextTurnPayload(
                message_text="嗯，你这样说我会更想继续聊。",
                strategy_used="light_follow_up",
                state_after_turn=TurnStatePayload(**_state_payload(openness_level="high")),
                generation_notes="对方在更安全的语气下愿意继续接话。",
                should_stop=False,
                stopping_reason=None,
            ),
            NextTurnPayload(
                message_text="那就好，我们慢慢来。",
                strategy_used="self_follow_up",
                state_after_turn=TurnStatePayload(**_state_payload(openness_level="high")),
                generation_notes="我方继续保持低压力推进。",
                should_stop=False,
                stopping_reason=None,
            ),
        ]
    )

    assessment = assess_branch(llm_client=fake_llm, context_pack=context_pack)
    first_reply = generate_first_reply(
        llm_client=fake_llm,
        context_pack=context_pack,
        assessment=assessment,
    )
    turns = simulate_short_thread(
        llm_client=fake_llm,
        context_pack=context_pack,
        assessment=assessment,
        first_reply=first_reply,
        turn_count=4,
    )

    assert first_reply.first_reply_text == "好呀，那我们就慢慢聊，别着急。"
    assert len(turns) == 4
    assert [turn["turn_index"] for turn in turns] == [1, 2, 3, 4]
    assert [turn["message_text"] for turn in turns] == [
        "好呀，那我们就慢慢聊，别着急。",
        "好，那我就顺着慢慢说。",
        "嗯，你这样说我会更想继续聊。",
        "那就好，我们慢慢来。",
    ]
    assert turns[0]["message_text"] == first_reply.first_reply_text
    assert len(fake_llm.calls) == 5
    assert fake_llm.calls[0]["system_prompt"] == BRANCH_SYSTEM_PROMPT
    assert fake_llm.calls[0]["response_model"] is BranchAssessmentPayload
    assert "你是一个“截止安全”的反事实分支状态判断器。" in fake_llm.calls[0]["system_prompt"]
    assert "你的核心任务是判断“改写相对原话改变了什么”" in fake_llm.calls[0]["system_prompt"]
    assert "reply_strategy 只描述对方最可能采取的回应方式，不要越界生成具体回复文本。" in fake_llm.calls[0]["system_prompt"]
    branch_prompt = fake_llm.calls[0]["user_prompt"]
    assert branch_prompt.startswith("请根据下面这次反事实改写请求，判断该分支相对原话的状态变化，并输出结构化 JSON。")
    assert "1. 总体原则" in branch_prompt
    assert "2. `branch_direction` 的职责" in branch_prompt
    assert "3. `state_shift_summary` 的职责" in branch_prompt
    assert "4. `other_immediate_feeling` 的职责" in branch_prompt
    assert "5. `reply_strategy` 的职责" in branch_prompt
    assert "6. `risk_flags` 的职责" in branch_prompt
    assert "7. `confidence` 的职责" in branch_prompt
    assert "8. 关键判断提醒" in branch_prompt
    assert "9. 边界示例" in branch_prompt
    assert "10. 输出质量要求" in branch_prompt
    assert "- 有没有把略微改善写成明显翻盘" in branch_prompt
    assert "先比较原话和改写分别触发了什么，再判断状态变化" in branch_prompt
    assert "如果只能确认更容易被接一句，不要把它写成关系明显拉近" in branch_prompt
    assert '"original_message_text": "我们已成功添加为好友，现在可以开始聊天啦～"' in branch_prompt
    assert '"replacement_content": "如果你方便的话，我们慢慢聊就好"' in branch_prompt
    assert "开场聊天" in branch_prompt
    assert "轻松" in branch_prompt
    assert "warming" in branch_prompt
    assert fake_llm.calls[1]["system_prompt"] == FIRST_REPLY_SYSTEM_PROMPT
    assert "你是一个“截止安全”的反事实首轮回复生成器。" in fake_llm.calls[1]["system_prompt"]
    assert "回复应优先追求真实、克制、符合当下关系允许的表达强度" in fake_llm.calls[1]["system_prompt"]
    assert "state_after_turn 只估计这条首轮回复之后的即时状态" in fake_llm.calls[1]["system_prompt"]
    first_reply_prompt = fake_llm.calls[1]["user_prompt"]
    assert first_reply_prompt.startswith("请根据下面这条反事实分支的状态判断结果，生成对方在该分支里的第一条回复，并输出结构化 JSON。")
    assert "1. 总体原则" in first_reply_prompt
    assert "2. `first_reply_text` 的职责" in first_reply_prompt
    assert "3. `strategy_used` 的职责" in first_reply_prompt
    assert "4. `first_reply_style_notes` 的职责" in first_reply_prompt
    assert "5. `state_after_turn` 的职责" in first_reply_prompt
    assert "6. 生成边界提醒" in first_reply_prompt
    assert "7. 质量要求：回复文本层" in first_reply_prompt
    assert "8. 质量要求：状态层" in first_reply_prompt
    assert "9. 边界示例" in first_reply_prompt
    assert "10. 输出质量要求" in first_reply_prompt
    assert "- 有没有把首轮回复写得过于理想化或过于会说话" in first_reply_prompt
    assert "避免分析腔、治疗腔、总结腔或过度完整的书面表达" in first_reply_prompt
    assert "宁可短一点、留一点，也不要假装对方突然很会说" in first_reply_prompt
    assert '"reply_strategy": "light_follow_up"' in first_reply_prompt
    assert '"replacement_content": "如果你方便的话，我们慢慢聊就好"' in first_reply_prompt
    assert '"speaker_role": "self"' in first_reply_prompt
    assert '"message_text": "如果你方便的话，我们慢慢聊就好"' in first_reply_prompt
    assert fake_llm.calls[2]["system_prompt"] == NEXT_TURN_SYSTEM_PROMPT
    assert "你是一个“截止安全”的反事实多轮续写器。" in fake_llm.calls[2]["system_prompt"]
    assert "你每次只生成“指定说话者”的下一句消息" in fake_llm.calls[2]["system_prompt"]
    assert "should_stop 用于判断这条分支是否应当自然收束" in fake_llm.calls[2]["system_prompt"]
    next_turn_prompt = fake_llm.calls[2]["user_prompt"]
    assert next_turn_prompt.startswith("请根据下面这条反事实分支的当前状态，生成指定说话者的下一句消息，并输出结构化 JSON。")
    assert "1. 总体原则" in next_turn_prompt
    assert "2. `message_text` 的职责" in next_turn_prompt
    assert "3. `strategy_used` 的职责" in next_turn_prompt
    assert "4. `state_after_turn` 的职责" in next_turn_prompt
    assert "5. `generation_notes` 的职责" in next_turn_prompt
    assert "6. `should_stop` 与 `stopping_reason` 的职责" in next_turn_prompt
    assert "7. 生成边界提醒" in next_turn_prompt
    assert "8. 边界示例" in next_turn_prompt
    assert "9. 输出质量要求" in next_turn_prompt
    assert "- 有没有让这一轮说得比当前关系允许的更多、更深、更热" in next_turn_prompt
    assert "允许自然变短、自然停住，不以把对话写完整为目标" in next_turn_prompt
    assert "如果继续只会重复礼貌承接或轻微改写上一句，应优先收束" in next_turn_prompt
    assert '"speaker_role": "self"' in next_turn_prompt
    assert '"reply_strategy": "light_follow_up"' in next_turn_prompt
    assert '"message_text": "好呀，那我们就慢慢聊，别着急。"' in next_turn_prompt


def test_simulation_engine_supports_single_reply_mode(tmp_path, monkeypatch):
    context_pack = _seed_engine_context_pack(
        tmp_path,
        monkeypatch,
        replacement_content="如果你现在忙，晚点聊也可以",
    )

    fake_llm = FakeSimulationLLM(
        [
            BranchAssessmentPayload(
                branch_direction="closer",
                state_shift_summary="新说法缓和了互动压力。",
                other_immediate_feeling="更放松",
                reply_strategy="light_follow_up",
                risk_flags=[],
                confidence=0.8,
            ),
            FirstReplyPayload(
                first_reply_text="好，那晚点聊也没事。",
                strategy_used="light_follow_up",
                first_reply_style_notes="用低压力方式接住改写后的说法。",
                state_after_turn=TurnStatePayload(**_state_payload()),
            ),
        ]
    )

    assessment = assess_branch(llm_client=fake_llm, context_pack=context_pack)
    first_reply = generate_first_reply(
        llm_client=fake_llm,
        context_pack=context_pack,
        assessment=assessment,
    )

    assert first_reply.first_reply_text == "好，那晚点聊也没事。"
    assert len(fake_llm.calls) == 2


def test_simulation_engine_stops_short_thread_when_repeated_turns_recur(tmp_path, monkeypatch):
    context_pack = _seed_engine_context_pack(
        tmp_path,
        monkeypatch,
        replacement_content="如果你不忙，我们慢慢说也可以",
    )

    fake_llm = FakeSimulationLLM(
        [
            BranchAssessmentPayload(
                branch_direction="closer",
                state_shift_summary="新说法缓和了互动压力。",
                other_immediate_feeling="更放松",
                reply_strategy="light_follow_up",
                risk_flags=[],
                confidence=0.8,
            ),
            FirstReplyPayload(
                first_reply_text="可以，我们慢慢说。",
                strategy_used="light_follow_up",
                first_reply_style_notes="先柔和接住。",
                state_after_turn=TurnStatePayload(**_state_payload(openness_level="high")),
            ),
            NextTurnPayload(
                message_text="好，那我继续说。",
                strategy_used="self_follow_up",
                state_after_turn=TurnStatePayload(**_state_payload(openness_level="high")),
                generation_notes="我方继续往下聊。",
                should_stop=False,
                stopping_reason=None,
            ),
            NextTurnPayload(
                message_text="可以，我们慢慢说。",
                strategy_used="light_follow_up",
                state_after_turn=TurnStatePayload(**_state_payload(openness_level="high")),
                generation_notes="错误地重复了前一条同角色发言。",
                should_stop=False,
                stopping_reason=None,
            ),
        ]
    )

    assessment = assess_branch(llm_client=fake_llm, context_pack=context_pack)
    first_reply = generate_first_reply(
        llm_client=fake_llm,
        context_pack=context_pack,
        assessment=assessment,
    )
    turns = simulate_short_thread(
        llm_client=fake_llm,
        context_pack=context_pack,
        assessment=assessment,
        first_reply=first_reply,
        turn_count=4,
    )

    assert [turn["message_text"] for turn in turns] == [
        "可以，我们慢慢说。",
        "好，那我继续说。",
    ]


def test_simulation_engine_rejects_targets_not_covered_by_segments(tmp_path, monkeypatch):
    _seed_uncovered_target_case(tmp_path, monkeypatch)

    with session_scope() as session:
        target = session.execute(
            select(Message).where(Message.conversation_id == 1)
        ).scalar_one()
        messages = session.execute(
            select(Message).where(Message.conversation_id == 1).order_by(Message.sequence_no.asc())
        ).scalars().all()

        try:
            build_context_pack(
                messages=[_message_to_context_dict(item) for item in messages],
                segments=[],
                target_message_id=target.id,
                replacement_content="换个说法",
                related_topic_digests=[],
                future_evidence_digests=[],
                base_relationship_snapshot=None,
                persona_self=None,
                persona_other=None,
            )
        except ValueError as exc:
            assert "not covered by any segment" in str(exc)
        else:
            raise AssertionError("expected build_context_pack to reject uncovered target messages")


def test_get_simulation_returns_completed_job_result(tmp_path, monkeypatch):
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
            source_file_path=str(tmp_path / "seed.txt"),
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
        session.add(
            SimulationJob(
                conversation_id=conversation.id,
                target_message_id=2,
                mode="single_reply",
                turn_count=1,
                replacement_content="如果你不忙，我们慢慢说也可以",
                status="queued",
                current_stage="queued",
                progress_percent=0,
                payload_json={
                    "progress": {
                        "current_stage_total_units": 2,
                        "current_stage_completed_units": 0,
                        "overall_total_units": 2,
                        "overall_completed_units": 0,
                        "status_message": "queued 0/2 steps",
                    }
                },
            )
        )

    fake_llm = FakeSimulationLLM(
        [
            BranchAssessmentPayload(
                branch_direction="closer",
                state_shift_summary="新说法缓和了互动压力。",
                other_immediate_feeling="更放松",
                reply_strategy="light_follow_up",
                risk_flags=[],
                confidence=0.8,
            ),
            FirstReplyPayload(
                first_reply_text="好，那晚点聊也没事。",
                strategy_used="light_follow_up",
                first_reply_style_notes="先低压力接住。",
                state_after_turn=TurnStatePayload(**_state_payload()),
            ),
        ]
    )

    assert run_next_simulation_job(llm_client=fake_llm) is True

    with session_scope() as session:
        job = session.query(SimulationJob).one()
        result_simulation_id = job.result_simulation_id

    with TestClient(create_app()) as client:
        response = client.get(f"/simulations/{result_simulation_id}")

    assert response.status_code == 200
    body = response.json()
    assert body["first_reply_text"] == "好，那晚点聊也没事。"
    assert body["simulated_turns"] == []
