from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
from pydantic import BaseModel

from if_then_mvp.api import create_app
from if_then_mvp.branch_sessions import append_branch_self_message
from if_then_mvp.context_builder import build_conversation_context_pack
from if_then_mvp.db import init_db, session_scope
from if_then_mvp.models import (
    BranchMessage,
    BranchReplyJob,
    BranchSession,
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
from if_then_mvp.simulation import (
    BranchAssessmentPayload,
    BranchReplyPayload,
    FirstReplyPayload,
    TurnStatePayload,
    assess_branch,
    generate_first_reply,
)
from if_then_mvp.worker import run_next_branch_reply_job


BASELINE_PATH = Path("tests/fixtures/realism_baseline/cases.json")
REQUIRED_FAILURE_TYPES = {
    "over_optimistic_shift",
    "future_fact_blindness",
    "future_fact_leakage",
    "persona_mismatch",
    "style_mismatch",
    "retrieval_miss",
    "short_thread_incoherence",
    "relationship_state_jump",
}


class FakeQualityLLM:
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


class SupersedingQualityLLM(FakeQualityLLM):
    def __init__(self, responses: list[BaseModel], *, branch_session_id: int) -> None:
        super().__init__(responses)
        self._branch_session_id = branch_session_id

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        with session_scope() as session:
            branch_session = session.get(BranchSession, self._branch_session_id)
            assert branch_session is not None
            append_branch_self_message(
                session,
                branch_session=branch_session,
                content_text="我又补充了一句，先不用急着答。",
            )
        return super().chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
        )


def _state_payload(*, openness_level: str = "medium") -> TurnStatePayload:
    return TurnStatePayload(
        relationship_temperature="warm",
        tension_level="low",
        openness_level=openness_level,
        initiative_balance="balanced",
        defensiveness_level="low",
        relationship_phase="warming",
        active_sensitive_topics=["推进边界"],
        state_rationale="质量门禁测试中的即时状态。",
    )


def _branch_reply(text: str = "嗯，先慢慢说。") -> BranchReplyPayload:
    return BranchReplyPayload(
        message_text=text,
        strategy_used="guarded_acknowledgement",
        state_after_turn=_state_payload(openness_level="medium"),
        generation_notes="保持 other 偏简短、保留式轻接。",
    )


def _seed_quality_conversation(tmp_path, monkeypatch) -> int:
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    init_db()

    with session_scope() as session:
        conversation = Conversation(
            title="quality gate",
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
            source_file_name="quality.txt",
            source_file_path=str(tmp_path / "quality.txt"),
            source_file_hash="quality",
            message_count_hint=4,
        )
        session.add(batch)
        session.flush()

        prior_other = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=1,
            speaker_name="梣ゥ",
            speaker_role="other",
            timestamp="2025-03-02T20:15:00",
            content_text="我们先慢一点吧",
            message_type="text",
        )
        prior_self = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=2,
            speaker_name="Tantless",
            speaker_role="self",
            timestamp="2025-03-02T20:16:00",
            content_text="好，我听你的节奏",
            message_type="text",
        )
        target_self = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=3,
            speaker_name="Tantless",
            speaker_role="self",
            timestamp="2025-03-02T20:18:00",
            content_text="那我可以多问一点吗",
            message_type="text",
        )
        future_other = Message(
            conversation_id=conversation.id,
            import_id=batch.id,
            sequence_no=4,
            speaker_name="梣ゥ",
            speaker_role="other",
            timestamp="2025-03-02T20:25:00",
            content_text="先不要追问吧，我会有压力",
            message_type="text",
        )
        session.add_all([prior_other, prior_self, target_self, future_other])
        session.flush()

        prior_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=prior_other.id,
            end_message_id=prior_self.id,
            start_time="2025-03-02T20:15:00",
            end_time="2025-03-02T20:16:00",
            message_count=2,
            self_message_count=1,
            other_message_count=1,
            segment_kind="normal",
            source_message_ids=[prior_other.id, prior_self.id],
        )
        target_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=target_self.id,
            end_message_id=target_self.id,
            start_time="2025-03-02T20:18:00",
            end_time="2025-03-02T20:18:00",
            message_count=1,
            self_message_count=1,
            other_message_count=0,
            segment_kind="normal",
            source_message_ids=[target_self.id],
        )
        future_segment = Segment(
            conversation_id=conversation.id,
            start_message_id=future_other.id,
            end_message_id=future_other.id,
            start_time="2025-03-02T20:25:00",
            end_time="2025-03-02T20:25:00",
            message_count=1,
            self_message_count=0,
            other_message_count=1,
            segment_kind="normal",
            source_message_ids=[future_other.id],
        )
        session.add_all([prior_segment, target_segment, future_segment])
        session.flush()

        session.add_all(
            [
                SegmentSummary(
                    segment_id=prior_segment.id,
                    summary_text="对方提前表达过希望慢一点，推进边界是当前敏感点。",
                    main_topics=["推进边界"],
                    self_stance="接受对方节奏",
                    other_stance="要求慢一点",
                    emotional_tone="谨慎",
                    interaction_pattern="边界协商",
                    has_conflict=False,
                    has_repair=False,
                    has_closeness_signal=False,
                    outcome="暂时缓和",
                    relationship_impact="mixed",
                    confidence=0.82,
                ),
                SegmentSummary(
                    segment_id=future_segment.id,
                    summary_text="后续对方明确说先不要追问，继续推进会让对方有压力。",
                    main_topics=["推进边界", "压力"],
                    self_stance="未出现",
                    other_stance="明确拒绝追问",
                    emotional_tone="紧张",
                    interaction_pattern="边界表达",
                    has_conflict=True,
                    has_repair=False,
                    has_closeness_signal=False,
                    outcome="对方收缩",
                    relationship_impact="negative",
                    confidence=0.9,
                ),
            ]
        )

        topic = Topic(
            conversation_id=conversation.id,
            topic_name="推进边界",
            topic_summary="围绕聊天推进速度、追问压力和边界的讨论。",
            first_seen_at="2025-03-02T20:15:00",
            last_seen_at="2025-03-02T20:25:00",
            segment_count=3,
            topic_status="ongoing",
        )
        session.add(topic)
        session.flush()
        session.add_all(
            [
                TopicLink(topic_id=topic.id, segment_id=prior_segment.id, link_reason="cutoff 前同一推进边界主题", score=0.91),
                TopicLink(topic_id=topic.id, segment_id=target_segment.id, link_reason="目标消息仍在追问边界", score=0.96),
                TopicLink(topic_id=topic.id, segment_id=future_segment.id, link_reason="cutoff 后明确拒绝追问", score=0.95),
            ]
        )
        session.add(
            RelationshipSnapshot(
                conversation_id=conversation.id,
                as_of_message_id=prior_self.id,
                as_of_time="2025-03-02T20:16:00",
                relationship_temperature="warm",
                tension_level="medium",
                openness_level="low",
                initiative_balance="self_leading",
                defensiveness_level="medium",
                unresolved_conflict_flags=["推进边界"],
                relationship_phase="uncertain",
                snapshot_summary="推进边界仍敏感。",
            )
        )
        session.add_all(
            [
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="self",
                    global_persona_summary="会主动解释",
                    style_traits=["直白"],
                    conflict_traits=["解释"],
                    relationship_specific_patterns=["想确认边界"],
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.8,
                ),
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="other",
                    global_persona_summary="有压力时会先保留",
                    style_traits=["简短"],
                    conflict_traits=["回避"],
                    relationship_specific_patterns=["先降速"],
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.82,
                ),
            ]
        )
        return target_self.id


def _build_quality_context_pack(target_message_id: int) -> dict:
    with session_scope() as session:
        target_message = session.get(Message, target_message_id)
        assert target_message is not None
        return build_conversation_context_pack(
            session,
            conversation_id=target_message.conversation_id,
            target_message=target_message,
            replacement_content="如果你不想继续聊也没关系，我听你的节奏",
        )


def test_realism_quality_gate_context_layers_and_future_evidence_flag(tmp_path, monkeypatch):
    monkeypatch.delenv("IF_THEN_ENABLE_FUTURE_EVIDENCE", raising=False)
    target_message_id = _seed_quality_conversation(tmp_path, monkeypatch)

    context_pack = _build_quality_context_pack(target_message_id)

    assert context_pack["evidence_policy"]["cutoff_safe_facts"] == "character_known"
    assert context_pack["evidence_policy"]["future_evidence_digests"] == "modeler_only_not_character_known"
    assert context_pack["related_topic_digests"][0]["topic_name"] == "推进边界"
    assert context_pack["future_evidence_digests"][0]["summary"] == "后续对方明确说先不要追问，继续推进会让对方有压力。"
    assert "future_evidence_digests" not in context_pack["cutoff_safe_facts"]
    assert context_pack["retrieval_trace"]["future_evidence_digests"][0]["selected"] is True

    monkeypatch.setenv("IF_THEN_ENABLE_FUTURE_EVIDENCE", "false")
    disabled_context_pack = _build_quality_context_pack(target_message_id)

    assert disabled_context_pack["future_evidence_digests"] == []
    assert disabled_context_pack["retrieval_trace"]["future_evidence_digests"] == []
    assert disabled_context_pack["retrieval_budget"]["future_evidence_digests"] == {
        "limit": 3,
        "candidate_count": 0,
        "selected_count": 0,
        "overflow_count": 0,
    }
    assert disabled_context_pack["related_topic_digests"][0]["topic_name"] == "推进边界"
    assert "future_evidence_digests_empty" in disabled_context_pack["retrieval_warnings"]
    assert "future_evidence_disabled" in disabled_context_pack["retrieval_warnings"]


def test_realism_quality_gate_prompt_keeps_future_evidence_modeler_only(tmp_path, monkeypatch):
    target_message_id = _seed_quality_conversation(tmp_path, monkeypatch)
    context_pack = _build_quality_context_pack(target_message_id)
    fake_llm = FakeQualityLLM(
        [
            BranchAssessmentPayload(
                branch_direction="limited_positive_with_high_guardrail",
                state_shift_summary="改写降低了追问压力，但 future evidence 显示推进边界高风险，因此只能有限缓和。",
                other_immediate_feeling="压力下降但仍保留",
                reply_strategy="guarded_acknowledgement",
                risk_flags=["推进边界仍敏感"],
                modeler_only_risk_sources=["future_evidence: 后续明确拒绝追问"],
                leakage_boundary_notes="future evidence 只用于保守判断，不作为 other 当下已知事实。",
                confidence=0.64,
            ),
            FirstReplyPayload(
                first_reply_text="嗯，先慢慢来吧。",
                strategy_used="guarded_acknowledgement",
                first_reply_style_notes="按对方简短保留的风格低压力承接。",
                state_after_turn=_state_payload(openness_level="medium"),
            ),
        ]
    )

    assessment = assess_branch(llm_client=fake_llm, context_pack=context_pack)
    first_reply = generate_first_reply(
        llm_client=fake_llm,
        context_pack=context_pack,
        assessment=assessment,
    )

    assert assessment["modeler_only_risk_sources"] == ["future_evidence: 后续明确拒绝追问"]
    assert first_reply.first_reply_text == "嗯，先慢慢来吧。"
    assert "先不要追问" not in first_reply.first_reply_text
    assert "后来" not in first_reply.first_reply_text

    branch_prompt = fake_llm.calls[0]["user_prompt"]
    first_reply_prompt = fake_llm.calls[1]["user_prompt"]
    assert "modeler-only future evidence JSONL:" in branch_prompt
    assert "modeler_only_risk_sources" in branch_prompt
    assert "后续对方明确说先不要追问，继续推进会让对方有压力。" in branch_prompt
    assert "modeler-only future evidence 只能影响表达强度、风险保守度和是否更有限" in first_reply_prompt
    assert "不得引用、复述或暗示 cutoff 后才发生的拒绝、偏好、解释、关系状态或后续对话" in first_reply_prompt


def test_realism_quality_gate_realtime_branch_serializes_and_cleans_up(tmp_path, monkeypatch):
    target_message_id = _seed_quality_conversation(tmp_path, monkeypatch)
    with TestClient(create_app()) as client:
        create_response = client.post(
            "/branch-sessions",
            json={
                "conversation_id": 1,
                "target_message_id": target_message_id,
                "replacement_content": "如果你不想继续聊也没关系，我听你的节奏",
            },
        )
        assert create_response.status_code == 201
        assert client.post("/branch-sessions/1/reply-jobs").status_code == 202
        assert client.post("/branch-sessions/1/messages", json={"content_text": "我补一句，不用急着回。"}).status_code == 201
        assert client.post("/branch-sessions/1/reply-jobs").status_code == 202

        session_response = client.get("/branch-sessions/1")
        assert session_response.status_code == 200
        assert [job["status"] for job in session_response.json()["reply_jobs"]] == ["queued", "superseded"]

    stale_llm = SupersedingQualityLLM([_branch_reply("这条旧回复不该提交。")], branch_session_id=1)
    assert run_next_branch_reply_job(llm_client=stale_llm) is True

    with session_scope() as session:
        branch_session = session.query(BranchSession).one()
        assert branch_session.input_revision == 3
        assert session.query(BranchReplyJob).filter(BranchReplyJob.status == "superseded").count() == 2
        assert session.query(BranchReplyJob).filter(BranchReplyJob.status == "queued").count() == 0
        assert [message.speaker_role for message in session.query(BranchMessage).order_by(BranchMessage.sequence_no.asc()).all()] == [
            "self",
            "self",
            "self",
        ]

    with TestClient(create_app()) as client:
        assert client.post("/branch-sessions/1/reply-jobs").status_code == 202

    reply_llm = FakeQualityLLM([_branch_reply("嗯，我听着。")])
    assert run_next_branch_reply_job(llm_client=reply_llm) is True

    prompt = reply_llm.calls[0]["user_prompt"]
    assert "如果你不想继续聊也没关系，我听你的节奏" in prompt
    assert "我补一句，不用急着回。" in prompt
    assert "我又补充了一句，先不用急着答。" in prompt
    assert "modeler-only future evidence JSONL:" in prompt
    assert "不要把原时间线后续事件强行搬进分支" in prompt

    with TestClient(create_app()) as client:
        assert client.delete("/conversations/1").status_code == 204

    with session_scope() as session:
        assert session.query(BranchSession).count() == 0
        assert session.query(BranchMessage).count() == 0
        assert session.query(BranchReplyJob).count() == 0


def test_realism_quality_gate_baseline_fixture_tracks_leakage_cases():
    payload = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    cases = payload["cases"]
    covered_failure_types = {
        annotation["type"]
        for case in cases
        for annotation in case["failure_annotations"]
    }

    assert len(cases) >= 10
    assert REQUIRED_FAILURE_TYPES <= covered_failure_types

    leakage_case_count = 0
    for case in cases:
        output_text = json.dumps(case["current_output"], ensure_ascii=False)
        forbidden_terms = case["modeler_only_evidence"]["forbidden_character_knowledge"]
        output_contains_future_term = any(term in output_text for term in forbidden_terms)
        is_leakage_case = any(
            annotation["type"] == "future_fact_leakage"
            for annotation in case["failure_annotations"]
        )
        if is_leakage_case:
            leakage_case_count += 1
        assert output_contains_future_term is is_leakage_case

    assert leakage_case_count > 0
