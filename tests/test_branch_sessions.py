from __future__ import annotations

from fastapi.testclient import TestClient
from pydantic import BaseModel

from if_then_mvp.api import create_app
from if_then_mvp.branch_sessions import append_branch_self_message
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
from if_then_mvp.simulation import BranchReplyPayload, TurnStatePayload
from if_then_mvp.worker import run_next_branch_reply_job


class FakeBranchLLM:
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


class SupersedingBranchLLM(FakeBranchLLM):
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
                content_text="我刚刚又补充了一句",
            )
        return super().chat_json(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            response_model=response_model,
        )


def _state_payload(
    *,
    relationship_temperature: str = "warm",
    tension_level: str = "low",
    openness_level: str = "medium",
    initiative_balance: str = "balanced",
    defensiveness_level: str = "low",
    relationship_phase: str = "warming",
) -> TurnStatePayload:
    return TurnStatePayload(
        relationship_temperature=relationship_temperature,
        tension_level=tension_level,
        openness_level=openness_level,
        initiative_balance=initiative_balance,
        defensiveness_level=defensiveness_level,
        relationship_phase=relationship_phase,
        active_sensitive_topics=[],
        state_rationale="实时分支里轻微承接。",
    )


def _reply(text: str = "好，那我们慢慢说。") -> BranchReplyPayload:
    return BranchReplyPayload(
        message_text=text,
        strategy_used="light_follow_up",
        state_after_turn=_state_payload(openness_level="medium_high"),
        generation_notes="保持 other 偏简短、轻接的风格。",
    )


def _seed_ready_conversation(tmp_path, monkeypatch, *, include_future_evidence: bool = False) -> int:
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
            message_count_hint=6 if include_future_evidence else 4,
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
        messages = [prior_other, prior_self, target_other, target_self]
        if include_future_evidence:
            future_self = Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=5,
                speaker_name="Tantless",
                speaker_role="self",
                timestamp="2025-03-02T20:30:00",
                content_text="那我可以多问一点吗",
                message_type="text",
            )
            future_other = Message(
                conversation_id=conversation.id,
                import_id=batch.id,
                sequence_no=6,
                speaker_name="梣ゥ",
                speaker_role="other",
                timestamp="2025-03-02T20:30:20",
                content_text="先不要追问吧，我会有压力",
                message_type="text",
            )
            messages.extend([future_self, future_other])
        session.add_all(messages)
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
        segments = [prior_segment, target_segment]
        future_segment = None
        if include_future_evidence:
            future_segment = Segment(
                conversation_id=conversation.id,
                start_message_id=future_self.id,
                end_message_id=future_other.id,
                start_time="2025-03-02T20:30:00",
                end_time="2025-03-02T20:30:20",
                message_count=2,
                self_message_count=1,
                other_message_count=1,
                segment_kind="normal",
                source_message_ids=[future_self.id, future_other.id],
            )
            segments.append(future_segment)
        session.add_all(segments)
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
            first_seen_at="2025-03-02T20:17:00",
            last_seen_at="2025-03-02T20:30:20" if include_future_evidence else "2025-03-02T20:17:30",
            segment_count=2 if include_future_evidence else 1,
            topic_status="ongoing",
        )
        session.add(topic)
        session.flush()
        session.add(TopicLink(topic_id=topic.id, segment_id=prior_segment.id, link_reason="段摘要高度相似", score=1.0))
        if include_future_evidence and future_segment is not None:
            session.add(
                SegmentSummary(
                    segment_id=future_segment.id,
                    summary_text="后续对方明确说先不要追问，继续推进会让对方有压力。",
                    main_topics=["推进边界", "压力"],
                    self_stance="想继续追问",
                    other_stance="明确要求先不要追问",
                    emotional_tone="紧张",
                    interaction_pattern="边界表达",
                    has_conflict=True,
                    has_repair=False,
                    has_closeness_signal=False,
                    outcome="对方收缩",
                    relationship_impact="negative",
                    confidence=0.86,
                )
            )
            session.add(
                TopicLink(
                    topic_id=topic.id,
                    segment_id=future_segment.id,
                    link_reason="后续同话题显示推进边界",
                    score=0.95,
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
                    global_persona_summary="友好但会补充解释",
                    style_traits=["直白"],
                    conflict_traits=["解释"],
                    relationship_specific_patterns=["主动接话"],
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.8,
                ),
                PersonaProfile(
                    conversation_id=conversation.id,
                    subject_role="other",
                    global_persona_summary="轻松但偏简短",
                    style_traits=["简短"],
                    conflict_traits=["回避"],
                    relationship_specific_patterns=["用玩笑接话"],
                    evidence_segment_ids=[prior_segment.id],
                    confidence=0.8,
                ),
            ]
        )
        return target_self.id


def _create_branch_session(client: TestClient, *, target_message_id: int) -> dict:
    response = client.post(
        "/branch-sessions",
        json={
            "conversation_id": 1,
            "target_message_id": target_message_id,
            "replacement_content": "如果你方便的话，我们慢慢聊就好",
        },
    )
    assert response.status_code == 201
    return response.json()


def test_branch_session_api_creates_session_and_supersedes_stale_reply_jobs(tmp_path, monkeypatch):
    target_message_id = _seed_ready_conversation(tmp_path, monkeypatch)

    with TestClient(create_app()) as client:
        body = _create_branch_session(client, target_message_id=target_message_id)
        assert body["input_revision"] == 1
        assert body["current_branch_state"]["relationship_temperature"] == "warm"
        assert [(message["speaker_role"], message["source"]) for message in body["messages"]] == [("self", "rewrite")]

        with session_scope() as session:
            branch_session = session.query(BranchSession).one()
            assert branch_session.session_memory_pack["strategy_version"] == "realtime-branch-memory-v2"
            assert branch_session.session_memory_pack["layered_context_pack"]["evidence_policy"][
                "future_evidence_digests"
            ] == "modeler_only_not_character_known"
            compatibility_pack = branch_session.session_memory_pack["compatibility"]["cutoff_safe_context_pack"]
            assert compatibility_pack["target_message_id"] == target_message_id
            assert "future_evidence_digests" not in compatibility_pack
            assert "branch_facts" not in compatibility_pack
            assert "evidence_policy" not in compatibility_pack
            assert branch_session.session_memory_pack["layered_context_pack"]["branch_facts"][
                "generated_branch_messages"
            ] == []

        first_job = client.post("/branch-sessions/1/reply-jobs")
        assert first_job.status_code == 202
        assert first_job.json()["status"] == "queued"
        assert first_job.json()["input_revision"] == 1

        message_response = client.post(
            "/branch-sessions/1/messages",
            json={"content_text": "我再补一句，不用急着回。"},
        )
        assert message_response.status_code == 201
        assert message_response.json()["speaker_role"] == "self"

        second_job = client.post("/branch-sessions/1/reply-jobs")
        assert second_job.status_code == 202
        assert second_job.json()["status"] == "queued"
        assert second_job.json()["input_revision"] == 2

        session_response = client.get("/branch-sessions/1")
        assert session_response.status_code == 200
        session_body = session_response.json()
        assert session_body["input_revision"] == 2
        assert [message["sequence_no"] for message in session_body["messages"]] == [1, 2]
        assert [job["status"] for job in session_body["reply_jobs"]] == ["queued", "superseded"]


def test_run_next_branch_reply_job_persists_only_other_reply(tmp_path, monkeypatch):
    target_message_id = _seed_ready_conversation(tmp_path, monkeypatch)
    with TestClient(create_app()) as client:
        _create_branch_session(client, target_message_id=target_message_id)
        assert client.post("/branch-sessions/1/reply-jobs").status_code == 202

    llm = FakeBranchLLM([_reply()])

    assert run_next_branch_reply_job(llm_client=llm) is True

    with session_scope() as session:
        messages = session.query(BranchMessage).order_by(BranchMessage.sequence_no.asc()).all()
        assert [(message.sequence_no, message.speaker_role, message.content_text) for message in messages] == [
            (1, "self", "如果你方便的话，我们慢慢聊就好"),
            (2, "other", "好，那我们慢慢说。"),
        ]
        job = session.query(BranchReplyJob).one()
        assert job.status == "completed"
        branch_session = session.query(BranchSession).one()
        assert branch_session.current_branch_state["openness_level"] == "medium_high"
        generated_branch_messages = branch_session.session_memory_pack["layered_context_pack"]["branch_facts"][
            "generated_branch_messages"
        ]
        assert generated_branch_messages == [
            {
                "sequence_no": 2,
                "speaker_role": "other",
                "message_text": "好，那我们慢慢说。",
                "source": "llm",
                "delivery_state": "committed",
            }
        ]

    assert llm.calls[0]["response_model"] is BranchReplyPayload
    assert "只能生成 other" in llm.calls[0]["system_prompt"]
    assert "persona_other" in llm.calls[0]["user_prompt"]
    assert "persona_other deterministic style profile JSON:" in llm.calls[0]["user_prompt"]
    assert '"max_bubble_count": 1' in llm.calls[0]["user_prompt"]
    assert "默认单泡回复，不要拆成连续多条。" in llm.calls[0]["user_prompt"]
    assert "如果你方便的话，我们慢慢聊就好" in llm.calls[0]["user_prompt"]


def test_realtime_branch_reply_prompt_treats_future_evidence_as_modeler_only(tmp_path, monkeypatch):
    target_message_id = _seed_ready_conversation(tmp_path, monkeypatch, include_future_evidence=True)
    with TestClient(create_app()) as client:
        _create_branch_session(client, target_message_id=target_message_id)
        assert client.post("/branch-sessions/1/reply-jobs").status_code == 202

    llm = FakeBranchLLM([_reply("嗯，先慢慢说。")])

    assert run_next_branch_reply_job(llm_client=llm) is True

    prompt = llm.calls[0]["user_prompt"]
    assert "modeler-only future evidence JSONL:" in prompt
    assert "后续对方明确说先不要追问，继续推进会让对方有压力。" in prompt
    assert "不得引用、复述或暗示 future evidence 中的拒绝、偏好、解释或关系状态。" in prompt
    assert "当前 branch_transcript 与 pending_self_messages 是分支事实源" in prompt
    assert "不要把原时间线后续事件强行搬进分支" in prompt
    assert '"use_policy": "modeler_only_not_character_known"' in prompt


def test_run_next_branch_reply_job_discards_superseded_result(tmp_path, monkeypatch):
    target_message_id = _seed_ready_conversation(tmp_path, monkeypatch)
    with TestClient(create_app()) as client:
        _create_branch_session(client, target_message_id=target_message_id)
        assert client.post("/branch-sessions/1/reply-jobs").status_code == 202

    llm = SupersedingBranchLLM([_reply("这条旧回复不该写入。")], branch_session_id=1)

    assert run_next_branch_reply_job(llm_client=llm) is True

    with session_scope() as session:
        branch_session = session.query(BranchSession).one()
        assert branch_session.input_revision == 2
        messages = session.query(BranchMessage).order_by(BranchMessage.sequence_no.asc()).all()
        assert [(message.speaker_role, message.content_text) for message in messages] == [
            ("self", "如果你方便的话，我们慢慢聊就好"),
            ("self", "我刚刚又补充了一句"),
        ]
        job = session.query(BranchReplyJob).one()
        assert job.status == "superseded"


def test_second_branch_reply_prompt_contains_full_transcript(tmp_path, monkeypatch):
    target_message_id = _seed_ready_conversation(tmp_path, monkeypatch)
    with TestClient(create_app()) as client:
        _create_branch_session(client, target_message_id=target_message_id)
        assert client.post("/branch-sessions/1/reply-jobs").status_code == 202

    first_llm = FakeBranchLLM([_reply("可以，我们慢慢聊。")])
    assert run_next_branch_reply_job(llm_client=first_llm) is True

    with TestClient(create_app()) as client:
        assert client.post("/branch-sessions/1/messages", json={"content_text": "那我接着说一点。"}).status_code == 201
        assert client.post("/branch-sessions/1/reply-jobs").status_code == 202

    second_llm = FakeBranchLLM([_reply("嗯，你说。")])
    assert run_next_branch_reply_job(llm_client=second_llm) is True

    prompt = second_llm.calls[0]["user_prompt"]
    assert "如果你方便的话，我们慢慢聊就好" in prompt
    assert "可以，我们慢慢聊。" in prompt
    assert "那我接着说一点。" in prompt

    with session_scope() as session:
        branch_session = session.query(BranchSession).one()
        generated_branch_messages = branch_session.session_memory_pack["layered_context_pack"]["branch_facts"][
            "generated_branch_messages"
        ]
        assert generated_branch_messages == [
            {
                "sequence_no": 2,
                "speaker_role": "other",
                "message_text": "可以，我们慢慢聊。",
                "source": "llm",
                "delivery_state": "committed",
            },
            {
                "sequence_no": 3,
                "speaker_role": "self",
                "message_text": "那我接着说一点。",
                "source": "user",
                "delivery_state": "committed",
            },
            {
                "sequence_no": 4,
                "speaker_role": "other",
                "message_text": "嗯，你说。",
                "source": "llm",
                "delivery_state": "committed",
            },
        ]


def test_delete_conversation_removes_branch_session_rows(tmp_path, monkeypatch):
    target_message_id = _seed_ready_conversation(tmp_path, monkeypatch)
    with TestClient(create_app()) as client:
        _create_branch_session(client, target_message_id=target_message_id)
        assert client.post("/branch-sessions/1/reply-jobs").status_code == 202
        delete_response = client.delete("/conversations/1")

    assert delete_response.status_code == 204
    with session_scope() as session:
        assert session.query(BranchSession).count() == 0
        assert session.query(BranchMessage).count() == 0
        assert session.query(BranchReplyJob).count() == 0
