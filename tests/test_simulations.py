from unittest.mock import patch

from fastapi.testclient import TestClient
from pydantic import BaseModel

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
from if_then_mvp.simulation import (
    BRANCH_SYSTEM_PROMPT,
    BranchAssessmentPayload,
    FIRST_REPLY_SYSTEM_PROMPT,
    FirstReplyPayload,
    NEXT_TURN_SYSTEM_PROMPT,
    NextTurnPayload,
    TurnStatePayload,
)


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

    with TestClient(create_app(llm_client=fake_llm)) as client:
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
    assert body["first_reply_text"] == "好呀，那我们就慢慢聊，别着急。"
    assert len(body["simulated_turns"]) == 4
    assert [turn["turn_index"] for turn in body["simulated_turns"]] == [1, 2, 3, 4]
    assert [turn["message_text"] for turn in body["simulated_turns"]] == [
        "好呀，那我们就慢慢聊，别着急。",
        "好，那我就顺着慢慢说。",
        "嗯，你这样说我会更想继续聊。",
        "那就好，我们慢慢来。",
    ]
    assert body["simulated_turns"][0]["message_text"] == body["first_reply_text"]
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
    assert '"speaker_role": "self"' in next_turn_prompt
    assert '"reply_strategy": "light_follow_up"' in next_turn_prompt
    assert '"message_text": "好呀，那我们就慢慢聊，别着急。"' in next_turn_prompt

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

    with TestClient(create_app(llm_client=fake_llm)) as client:
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
    assert body["first_reply_text"] == "好，那晚点聊也没事。"
    assert body["simulated_turns"] == []
    assert len(fake_llm.calls) == 2


def test_simulations_endpoint_stops_short_thread_when_repeated_turns_recur(tmp_path, monkeypatch):
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

    with TestClient(create_app(llm_client=fake_llm)) as client:
        response = client.post(
            "/simulations",
            json={
                "conversation_id": 1,
                "target_message_id": 2,
                "replacement_content": "如果你不忙，我们慢慢说也可以",
                "mode": "short_thread",
                "turn_count": 4,
            },
        )

    assert response.status_code == 201
    body = response.json()
    assert [turn["message_text"] for turn in body["simulated_turns"]] == [
        "可以，我们慢慢说。",
        "好，那我继续说。",
    ]


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


def test_simulations_endpoint_returns_503_when_llm_is_not_configured(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path / "app_data"))
    monkeypatch.delenv("IF_THEN_LLM_BASE_URL", raising=False)
    monkeypatch.delenv("IF_THEN_LLM_API_KEY", raising=False)
    monkeypatch.delenv("IF_THEN_LLM_CHAT_MODEL", raising=False)
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

    with patch(
        "if_then_mvp.runtime_llm.load_local_llm_config",
        side_effect=RuntimeError("local config unavailable"),
    ):
        with TestClient(create_app()) as client:
            response = client.post(
                "/simulations",
                json={
                    "conversation_id": 1,
                    "target_message_id": 2,
                    "replacement_content": "如果你不忙，我们慢慢说也可以",
                    "mode": "single_reply",
                    "turn_count": 1,
                },
            )

    assert response.status_code == 503
    assert "Simulation LLM is not configured" in response.json()["detail"]
