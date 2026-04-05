from if_then_mvp.analysis import SEGMENT_SYSTEM_PROMPT, SegmentSummaryPayload, build_segment_summary


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
        return response_model(
            summary_text="双方在互相打招呼并发送图片。",
            main_topics=["初次聊天", "发图"],
            self_stance="我方主动接话",
            other_stance="对方轻松回应",
            emotional_tone="轻松",
            interaction_pattern="日常互动",
            has_conflict=False,
            has_repair=False,
            has_closeness_signal=False,
            outcome="继续聊天",
            relationship_impact="neutral_positive",
            confidence=0.82,
        )


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
            {"speaker_role": "other", "content_text": "我是凉ゥ"},
            {"speaker_role": "self", "content_text": "你好"},
            {"speaker_role": "other", "content_text": "[图片: 1.jpg]"},
        ],
        previous_snapshot_summary="关系稳定，刚加上好友。",
    )

    assert fake_llm.calls == [
        {
            "system_prompt": SEGMENT_SYSTEM_PROMPT,
            "user_prompt": (
                "Previous snapshot: 关系稳定，刚加上好友。\n"
                "other: 我是凉ゥ\n"
                "self: 你好\n"
                "other: [图片: 1.jpg]"
            ),
            "response_model": SegmentSummaryPayload,
        }
    ]
