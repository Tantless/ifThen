import json

import httpx
import pytest

from if_then_mvp.analysis import (
    PERSONA_SYSTEM_PROMPT,
    SEGMENT_SYSTEM_PROMPT,
    SNAPSHOT_SYSTEM_PROMPT,
    TOPIC_ASSIGNMENT_SYSTEM_PROMPT,
    TOPIC_CREATION_SYSTEM_PROMPT,
    TOPIC_MERGE_REVIEW_SYSTEM_PROMPT,
    PersonaPayload,
    SegmentSummaryPayload,
    SnapshotPayload,
    TopicAssignmentPayload,
    TopicCreationPayload,
    TopicMergeReviewPayload,
    assign_segment_topics,
    build_persona_payload,
    build_segment_summary,
    build_snapshot_payload,
    build_topic_creation_payload,
    review_topic_merges,
)
from if_then_mvp.llm import LLMClient, LLMClientError, OpenAICompatibleTransport


class FakeLLM:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    def chat_json(self, *, system_prompt, user_prompt, response_model):
        self.calls.append(
            {
                "system_prompt": system_prompt,
                "user_prompt": user_prompt,
                "response_model": response_model,
            }
        )
        payload_map = {
            SegmentSummaryPayload: {
                "summary_text": "双方在互相打招呼并发送图片。",
                "main_topics": ["初次聊天", "发图"],
                "self_stance": "我方主动接话",
                "other_stance": "对方轻松回应",
                "emotional_tone": "轻松",
                "interaction_pattern": "日常互动",
                "has_conflict": False,
                "has_repair": False,
                "has_closeness_signal": False,
                "outcome": "继续聊天",
                "relationship_impact": "neutral_positive",
                "confidence": 0.82,
            },
            TopicAssignmentPayload: {
                "matched_topics": [
                    {
                        "topic_id": 7,
                        "link_reason": "当前片段继续围绕宿舍/住宿问题展开。",
                        "score": 0.91,
                    }
                ],
                "should_create_new_topic": False,
            },
            TopicCreationPayload: {
                "topic_name": "天气相关话题",
                "topic_summary": "围绕天气变化、冷热感受和天气状况展开的持续讨论。",
                "topic_status": "ongoing",
                "relevance_reason": "当前片段明确围绕天气变化展开，适合沉淀为可复用话题。",
            },
            TopicMergeReviewPayload: {
                "merges": [
                    {
                        "source_topic_ids": [3, 5],
                        "merged_topic_name": "宿舍/住宿讨论",
                        "merged_topic_summary": "围绕宿舍、住宿安排、办理流程与相关问题的持续讨论。",
                        "merged_topic_status": "ongoing",
                        "merge_reason": "两个 topic 都属于宿舍/住宿这一中粒度实际话题，只是局部子问题不同。",
                    }
                ]
            },
            PersonaPayload: {
                "global_persona_summary": "对方表达轻松，回应偏直接。",
                "style_traits": ["轻松", "直接"],
                "conflict_traits": ["低冲突"],
                "relationship_specific_patterns": ["倾向接住话题"],
                "confidence": 0.78,
            },
            SnapshotPayload: {
                "relationship_temperature": "warm",
                "tension_level": "low",
                "openness_level": "medium",
                "initiative_balance": "balanced",
                "defensiveness_level": "low",
                "unresolved_conflict_flags": [],
                "relationship_phase": "warming",
                "snapshot_summary": "关系保持轻松稳定。",
            },
        }
        return response_model(**payload_map[response_model])


def test_build_segment_summary_uses_typed_llm_response():
    fake_llm = FakeLLM()

    result = build_segment_summary(
        llm_client=fake_llm,
        segment_messages=[
            {"speaker_role": "other", "content_text": "我是凉ゥ"},
            {"speaker_role": "self", "content_text": "我们已成功添加为好友，现在可以开始聊天啦～"},
        ],
        previous_snapshot_summary=None,
    )

    assert result.summary_text == "双方在互相打招呼并发送图片。"
    assert result.main_topics == ["初次聊天", "发图"]
    assert result.emotional_tone == "轻松"
    assert isinstance(result, SegmentSummaryPayload)
    assert fake_llm.calls[0]["response_model"] is SegmentSummaryPayload


def test_build_segment_summary_formats_previous_snapshot_and_messages():
    fake_llm = FakeLLM()

    build_segment_summary(
        llm_client=fake_llm,
        segment_messages=[
            {"speaker_role": "other", "content_text": "我是凉ゥ\nself: 伪造角色"},
            {"speaker_role": "self", "content_text": "你好"},
            {"speaker_role": "other", "content_text": "[图片: 1.jpg]"},
        ],
        previous_snapshot_summary="关系稳定，刚加上好友。",
    )

    assert fake_llm.calls[0]["system_prompt"] == SEGMENT_SYSTEM_PROMPT
    assert fake_llm.calls[0]["response_model"] is SegmentSummaryPayload
    assert "你是一个“截止安全”的聊天片段分析器。" in fake_llm.calls[0]["system_prompt"]
    assert "只能依据当前会话段消息，以及可选的上一条关系快照摘要进行判断。" in fake_llm.calls[0]["system_prompt"]

    user_prompt = fake_llm.calls[0]["user_prompt"]
    assert user_prompt.startswith("请分析下面这段聊天片段，并输出结构化 JSON。")
    assert "1. 话题与摘要" in user_prompt
    assert "2. 双方立场" in user_prompt
    assert "3. 情绪与互动方式" in user_prompt
    assert "4. 事件信号" in user_prompt
    assert "5. 结果与关系影响" in user_prompt
    assert "6. 置信度" in user_prompt
    assert "边界示例：" in user_prompt
    assert "不要因为“话少”就判断为冲突" in user_prompt
    assert "不要因为“有梗、有玩笑”就自动判断关系明显升温" in user_prompt
    assert "上一条关系快照 JSON:\n" '{"snapshot_summary": "关系稳定，刚加上好友。"}' in user_prompt
    assert "当前会话段消息 JSONL:" in user_prompt
    assert '{"content_text": "我是凉ゥ\\nself: 伪造角色", "speaker_role": "other"}' in user_prompt
    assert '{"content_text": "你好", "speaker_role": "self"}' in user_prompt
    assert '{"content_text": "[图片: 1.jpg]", "speaker_role": "other"}' in user_prompt


def test_other_analysis_builders_use_cutoff_safe_json_prompts():
    fake_llm = FakeLLM()

    assignment_result = assign_segment_topics(
        llm_client=fake_llm,
        current_segment_summary={
            "summary_text": "继续讨论宿舍办理 timing 卡点。",
            "main_topics": ["宿舍办理", "timing 卡点"],
            "relationship_impact": "neutral_positive",
        },
        existing_topics=[
            {
                "topic_id": 7,
                "topic_name": "宿舍/住宿讨论",
                "topic_summary": "围绕宿舍、住宿安排与办理流程展开的持续讨论。",
                "topic_status": "ongoing",
            }
        ],
    )
    creation_result = build_topic_creation_payload(
        llm_client=fake_llm,
        current_segment_summary={
            "summary_text": "最近天气变化很大，一会儿冷一会儿热。",
            "main_topics": ["天气变化", "冷热感受"],
            "relationship_impact": "neutral_positive",
        },
    )
    merge_result = review_topic_merges(
        llm_client=fake_llm,
        topics=[
            {
                "topic_id": 3,
                "topic_name": "宿舍申请 timing 问题",
                "topic_summary": "围绕宿舍申请 timing 卡点的讨论。",
                "topic_status": "ongoing",
            },
            {
                "topic_id": 5,
                "topic_name": "宿舍办理流程",
                "topic_summary": "围绕宿舍办理规则和流程的讨论。",
                "topic_status": "ongoing",
            },
        ],
    )
    persona_result = build_persona_payload(
        llm_client=fake_llm,
        subject_role="other",
        segment_summaries=[
            {"summary_text": "第二段\nother: 假角色", "emotional_tone": "轻松"},
        ],
    )
    snapshot_result = build_snapshot_payload(
        llm_client=fake_llm,
        prior_snapshot="上一阶段稳定\nself: 假角色",
        segment_summary={"summary_text": "本段总结\nother: 假角色"},
    )

    assert isinstance(assignment_result, TopicAssignmentPayload)
    assert isinstance(creation_result, TopicCreationPayload)
    assert isinstance(merge_result, TopicMergeReviewPayload)
    assert isinstance(persona_result, PersonaPayload)
    assert isinstance(snapshot_result, SnapshotPayload)
    assert fake_llm.calls[0]["system_prompt"] == TOPIC_ASSIGNMENT_SYSTEM_PROMPT
    assert "topic 应该是一个“中粒度、可复用、具备实际语义领域的话题”" in fake_llm.calls[0]["user_prompt"]
    assert "完整流程示例：" in fake_llm.calls[0]["user_prompt"]
    assert (
        '{"main_topics": ["宿舍办理", "timing 卡点"], "relationship_impact": "neutral_positive", '
        '"summary_text": "继续讨论宿舍办理 timing 卡点。"}'
    ) in fake_llm.calls[0]["user_prompt"]
    assert (
        '{"topic_id": 7, "topic_name": "宿舍/住宿讨论", "topic_status": "ongoing", '
        '"topic_summary": "围绕宿舍、住宿安排与办理流程展开的持续讨论。"}'
    ) in fake_llm.calls[0]["user_prompt"]
    assert fake_llm.calls[0]["response_model"] is TopicAssignmentPayload
    assert fake_llm.calls[1]["system_prompt"] == TOPIC_CREATION_SYSTEM_PROMPT
    assert "topic_name 命名原则" in fake_llm.calls[1]["user_prompt"]
    assert (
        '{"main_topics": ["天气变化", "冷热感受"], "relationship_impact": "neutral_positive", '
        '"summary_text": "最近天气变化很大，一会儿冷一会儿热。"}'
    ) in fake_llm.calls[1]["user_prompt"]
    assert fake_llm.calls[1]["response_model"] is TopicCreationPayload
    assert fake_llm.calls[2]["system_prompt"] == TOPIC_MERGE_REVIEW_SYSTEM_PROMPT
    assert "当前 topic 列表 JSONL:" in fake_llm.calls[2]["user_prompt"]
    assert (
        '{"topic_id": 3, "topic_name": "宿舍申请 timing 问题", "topic_status": "ongoing", '
        '"topic_summary": "围绕宿舍申请 timing 卡点的讨论。"}'
    ) in fake_llm.calls[2]["user_prompt"]
    assert (
        '{"topic_id": 5, "topic_name": "宿舍办理流程", "topic_status": "ongoing", '
        '"topic_summary": "围绕宿舍办理规则和流程的讨论。"}'
    ) in fake_llm.calls[2]["user_prompt"]
    assert fake_llm.calls[2]["response_model"] is TopicMergeReviewPayload
    assert fake_llm.calls[3]["system_prompt"] == PERSONA_SYSTEM_PROMPT
    assert "你是一个“截止安全”的关系语境人格画像提炼器。" in fake_llm.calls[3]["system_prompt"]
    assert "你要提炼的是“跨多段相对稳定、可复用、能约束后续推演”的倾向" in fake_llm.calls[3]["system_prompt"]
    assert "不要做心理诊断、依恋类型判断、创伤推测或隐藏动机猜测。" in fake_llm.calls[3]["system_prompt"]
    persona_prompt = fake_llm.calls[3]["user_prompt"]
    assert persona_prompt.startswith("请根据下面这些会话段摘要，为指定说话者生成结构化 persona 画像，并输出 JSON。")
    assert "1. 总体原则" in persona_prompt
    assert "2. `global_persona_summary` 的职责" in persona_prompt
    assert "3. `style_traits` 的职责" in persona_prompt
    assert "4. `conflict_traits` 的职责" in persona_prompt
    assert "5. `relationship_specific_patterns` 的职责" in persona_prompt
    assert "6. 字段边界提醒" in persona_prompt
    assert "7. 边界示例" in persona_prompt
    assert "8. 输出质量要求" in persona_prompt
    assert "- 有没有把单次事件误写成长期人格" in persona_prompt
    assert "优先提炼能直接约束后续措辞、长度、推进方式的行为模式" in persona_prompt
    assert "如果不确定更像全局倾向还是关系特定模式，优先降低结论强度或写进 `relationship_specific_patterns`" in persona_prompt
    assert "人格画像请求 JSON:\n" '{"subject_role": "other"}' in persona_prompt
    assert '{"emotional_tone": "轻松", "summary_text": "第二段\\nother: 假角色"}' in persona_prompt
    assert fake_llm.calls[3]["response_model"] is PersonaPayload
    assert fake_llm.calls[4]["system_prompt"] == SNAPSHOT_SYSTEM_PROMPT
    assert "你是一个“截止安全”的关系状态快照估计器。" in fake_llm.calls[4]["system_prompt"]
    assert "你要做的是在已有关系背景上进行连续更新，而不是每次都从零重新判断。" in fake_llm.calls[4]["system_prompt"]
    assert "不要把普通简短、普通礼貌、普通谨慎自动解释为高 tension、高 defensiveness 或关系恶化。" in fake_llm.calls[4]["system_prompt"]
    snapshot_prompt = fake_llm.calls[4]["user_prompt"]
    assert snapshot_prompt.startswith("请根据下面的上一条关系快照和当前会话段摘要，生成截至当前段结束时的关系状态快照，并输出 JSON。")
    assert "1. 总体原则" in snapshot_prompt
    assert "2. `relationship_temperature` 的职责" in snapshot_prompt
    assert "3. `tension_level` 的职责" in snapshot_prompt
    assert "4. `openness_level` 的职责" in snapshot_prompt
    assert "5. `initiative_balance` 的职责" in snapshot_prompt
    assert "6. `defensiveness_level` 的职责" in snapshot_prompt
    assert "7. `unresolved_conflict_flags` 的职责" in snapshot_prompt
    assert "8. `relationship_phase` 的职责" in snapshot_prompt
    assert "9. `snapshot_summary` 的职责" in snapshot_prompt
    assert "10. 边界示例" in snapshot_prompt
    assert "11. 输出质量要求" in snapshot_prompt
    assert "- 有没有忽视上一快照，导致状态跳变过大" in snapshot_prompt
    assert "先判断哪些状态应延续，再判断哪些字段发生了有限变化" in snapshot_prompt
    assert "如果只是普通礼貌、普通接话或普通停顿，不要把它解释成关系修复或关系恶化" in snapshot_prompt
    assert "上一条关系快照 JSON:\n" '{"snapshot_summary": "上一阶段稳定\\nself: 假角色"}' in snapshot_prompt
    assert '{"summary_text": "本段总结\\nother: 假角色"}' in snapshot_prompt
    assert fake_llm.calls[4]["response_model"] is SnapshotPayload


class FakeTransport:
    def __init__(self, content: str) -> None:
        self.content = content
        self.calls: list[dict] = []

    def post_chat_completion(self, *, base_url: str, api_key: str, payload: dict) -> str:
        self.calls.append({"base_url": base_url, "api_key": api_key, "payload": payload})
        return self.content


class FakeSequenceTransport:
    def __init__(self, contents: list[str]) -> None:
        self.contents = contents
        self.calls: list[dict] = []

    def post_chat_completion(self, *, base_url: str, api_key: str, payload: dict) -> str:
        self.calls.append({"base_url": base_url, "api_key": api_key, "payload": payload})
        return self.contents[len(self.calls) - 1]


def test_llm_client_builds_payload_and_returns_typed_model():
    transport = FakeTransport(
        json.dumps(
            {
                "summary_text": "双方在互相打招呼并发送图片。",
                "main_topics": ["初次聊天", "发图"],
                "self_stance": "我方主动接话",
                "other_stance": "对方轻松回应",
                "emotional_tone": "轻松",
                "interaction_pattern": "日常互动",
                "has_conflict": False,
                "has_repair": False,
                "has_closeness_signal": False,
                "outcome": "继续聊天",
                "relationship_impact": "neutral_positive",
                "confidence": 0.82,
            },
            ensure_ascii=False,
        )
    )
    client = LLMClient(
        base_url="https://example.test/v1",
        api_key="secret",
        chat_model="gpt-test",
        transport=transport,
    )

    result = client.chat_json(
        system_prompt="system",
        user_prompt="user",
        response_model=SegmentSummaryPayload,
    )

    assert isinstance(result, SegmentSummaryPayload)
    assert transport.calls == [
        {
            "base_url": "https://example.test/v1",
            "api_key": "secret",
            "payload": {
                "model": "gpt-test",
                "messages": [
                    {"role": "system", "content": "system"},
                    {"role": "user", "content": "user"},
                ],
                "response_format": {"type": "json_object"},
            },
        }
    ]


def test_llm_client_wraps_validation_errors_in_stable_exception():
    client = LLMClient(
        base_url="https://example.test/v1",
        api_key="secret",
        chat_model="gpt-test",
        transport=FakeTransport('{"summary_text": "only one field"}'),
    )

    with pytest.raises(LLMClientError, match="Failed to validate structured LLM response"):
        client.chat_json(
            system_prompt="system",
            user_prompt="user",
            response_model=SegmentSummaryPayload,
        )


def test_llm_client_repairs_invalid_structured_response_once():
    transport = FakeSequenceTransport(
        [
            '{"summary":"对方回应有空并询问怎么了","sentiment":"neutral","open_question":"下一步要说明具体事情吗？"}',
            json.dumps(
                {
                    "summary_text": "双方在试探性开启对话。",
                    "main_topics": ["开场询问"],
                    "self_stance": "我方主动发起",
                    "other_stance": "对方愿意接话",
                    "emotional_tone": "中性",
                    "interaction_pattern": "简短试探",
                    "has_conflict": False,
                    "has_repair": False,
                    "has_closeness_signal": False,
                    "outcome": "对话被接住",
                    "relationship_impact": "neutral",
                    "confidence": 0.66,
                },
                ensure_ascii=False,
            ),
        ]
    )
    client = LLMClient(
        base_url="https://example.test/v1",
        api_key="secret",
        chat_model="gpt-test",
        transport=transport,
    )

    result = client.chat_json(
        system_prompt="system",
        user_prompt="user",
        response_model=SegmentSummaryPayload,
    )

    assert isinstance(result, SegmentSummaryPayload)
    assert result.summary_text == "双方在试探性开启对话。"
    assert len(transport.calls) == 2
    assert transport.calls[1]["payload"]["messages"][0]["content"] == "请将给定的 JSON 修复为符合要求的结构。"
    assert "summary_text" in transport.calls[1]["payload"]["messages"][1]["content"]


class FakeHTTPResponse:
    def __init__(self, payload=None, *, json_error: Exception | None = None, status_error: Exception | None = None) -> None:
        self._payload = payload
        self._json_error = json_error
        self._status_error = status_error
        self.text = ""  # Add text attribute for streaming response fallback

    def raise_for_status(self) -> None:
        if self._status_error is not None:
            raise self._status_error
        return None

    def json(self):
        if self._json_error is not None:
            raise self._json_error
        return self._payload


class FakeHTTPClient:
    def __init__(self, response: FakeHTTPResponse | None = None, *, post_error: Exception | None = None) -> None:
        self.response = response or FakeHTTPResponse({})
        self.post_error = post_error

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None

    def post(self, url: str, json: dict, headers: dict) -> FakeHTTPResponse:
        if self.post_error is not None:
            raise self.post_error
        return self.response


@pytest.mark.parametrize(
    ("response_payload", "message"),
    [
        ({}, "choices list"),
        ({"choices": []}, "no choices"),
        ({"choices": [{}]}, "message object"),
        ({"choices": [{"message": {}}]}, "content must be a string"),
        ({"choices": [{"message": {"content": ["not", "a", "string"]}}]}, "content must be a string"),
    ],
)
def test_openai_compatible_transport_raises_stable_errors(monkeypatch, response_payload, message):
    monkeypatch.setattr(httpx, "Client", lambda timeout: FakeHTTPClient(FakeHTTPResponse(response_payload)))
    transport = OpenAICompatibleTransport(timeout_seconds=5.0)

    with pytest.raises(LLMClientError, match=message):
        transport.post_chat_completion(
            base_url="https://example.test/v1",
            api_key="secret",
            payload={"model": "gpt-test"},
        )


def test_openai_compatible_transport_wraps_non_object_json(monkeypatch):
    monkeypatch.setattr(httpx, "Client", lambda timeout: FakeHTTPClient(FakeHTTPResponse(["not", "an", "object"])))
    transport = OpenAICompatibleTransport(timeout_seconds=5.0)

    with pytest.raises(LLMClientError, match="JSON object"):
        transport.post_chat_completion(
            base_url="https://example.test/v1",
            api_key="secret",
            payload={"model": "gpt-test"},
        )


def test_openai_compatible_transport_wraps_invalid_json(monkeypatch):
    monkeypatch.setattr(
        httpx,
        "Client",
        lambda timeout: FakeHTTPClient(FakeHTTPResponse(json_error=json.JSONDecodeError("bad json", "x", 0))),
    )
    transport = OpenAICompatibleTransport(timeout_seconds=5.0)

    with pytest.raises(LLMClientError, match="valid JSON"):
        transport.post_chat_completion(
            base_url="https://example.test/v1",
            api_key="secret",
            payload={"model": "gpt-test"},
        )


@pytest.mark.parametrize(
    "exception_factory",
    [
        lambda: httpx.ConnectTimeout("timeout"),
        lambda: httpx.HTTPStatusError(
            "bad status",
            request=httpx.Request("POST", "https://example.test/v1/chat/completions"),
            response=httpx.Response(500, request=httpx.Request("POST", "https://example.test/v1/chat/completions")),
        ),
    ],
)
def test_openai_compatible_transport_wraps_http_errors(monkeypatch, exception_factory):
    error = exception_factory()
    if isinstance(error, httpx.HTTPStatusError):
        fake_client = FakeHTTPClient(response=FakeHTTPResponse(status_error=error))
    else:
        fake_client = FakeHTTPClient(post_error=error)
    monkeypatch.setattr(httpx, "Client", lambda timeout: fake_client)
    transport = OpenAICompatibleTransport(timeout_seconds=5.0)

    with pytest.raises(LLMClientError, match="request failed"):
        transport.post_chat_completion(
            base_url="https://example.test/v1",
            api_key="secret",
            payload={"model": "gpt-test"},
        )
