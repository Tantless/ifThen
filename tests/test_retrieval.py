from if_then_mvp.retrieval import build_context_pack


def test_build_context_pack_excludes_target_and_future_messages():
    context = build_context_pack(
        messages=[
            {
                "id": 1,
                "conversation_id": 1,
                "sequence_no": 1,
                "timestamp": "2025-03-02T20:18:03",
                "speaker_role": "other",
                "content_text": "我是凉ゥ",
            },
            {
                "id": 2,
                "conversation_id": 1,
                "sequence_no": 2,
                "timestamp": "2025-03-02T20:18:04",
                "speaker_role": "self",
                "content_text": "我们已成功添加为好友，现在可以开始聊天啦～",
            },
            {
                "id": 3,
                "conversation_id": 1,
                "sequence_no": 3,
                "timestamp": "2025-03-02T20:18:04",
                "speaker_role": "other",
                "content_text": "这句与目标同秒但更晚",
            },
            {
                "id": 4,
                "conversation_id": 1,
                "sequence_no": 4,
                "timestamp": "2025-03-02T20:19:00",
                "speaker_role": "other",
                "content_text": "[图片: 1DA1EB4EA41F53A9407923B093C213B6.jpg]",
            },
        ],
        segments=[
            {
                "id": 11,
                "source_message_ids": [3, 1, 2, 4],
                "start_time": "2025-03-02T20:18:03",
                "end_time": "2025-03-02T20:19:00",
            }
        ],
        target_message_id=2,
        replacement_content="如果方便的话，我们慢慢聊也可以",
        related_topic_digests=[],
        future_evidence_digests=[],
        base_relationship_snapshot={"relationship_temperature": "warm"},
        persona_self={"global_persona_summary": "友好"},
        persona_other={"global_persona_summary": "轻松"},
    )

    assert context["conversation_id"] == 1
    assert context["target_message_id"] == 2
    assert context["cutoff_timestamp"] == "2025-03-02T20:18:04"
    assert context["cutoff_sequence_no"] == 2
    assert [item["id"] for item in context["current_segment_history"]] == [1]
    assert context["current_segment_brief"] == {"message_count": 1, "last_speaker_role": "other"}
    assert context["original_message_text"] == "我们已成功添加为好友，现在可以开始聊天啦～"
    assert context["replacement_content"] == "如果方便的话，我们慢慢聊也可以"
    assert context["same_day_prior_segments"] == []
    assert context["related_topic_digests"] == []
    assert context["base_relationship_snapshot"] == {"relationship_temperature": "warm"}
    assert context["moment_state_estimate"]["relationship_temperature"] == "warm"
    assert context["moment_state_estimate"]["active_sensitive_topics"] == []
    assert context["persona_self"] == {"global_persona_summary": "友好"}
    assert context["persona_other"] == {"global_persona_summary": "轻松"}
    assert context["cutoff_safe_facts"]["related_topic_digests"] == []
    assert context["future_evidence_digests"] == []
    assert context["branch_facts"]["rewrite_target"]["target_message_id"] == 2
    assert context["evidence_policy"]["future_evidence_digests"] == "modeler_only_not_character_known"
    assert context["retrieval_trace"] == {"related_topic_digests": [], "future_evidence_digests": []}
    assert context["retrieval_budget"]["current_segment_history"]["policy"] == "preserve_all"
    assert context["retrieval_budget"]["related_topic_digests"]["limit"] == 3
    assert context["retrieval_budget"]["future_evidence_digests"]["selected_count"] == 0
    assert context["retrieval_warnings"] == ["related_topic_digests_empty", "future_evidence_digests_empty"]
    assert context["strategy_version"] == "layered-evidence-v1"


def test_build_context_pack_collects_same_day_prior_segments_only():
    context = build_context_pack(
        messages=[
            {
                "id": 1,
                "conversation_id": 8,
                "sequence_no": 1,
                "timestamp": "2025-03-02T09:00:00",
                "speaker_role": "other",
                "content_text": "早上好",
            },
            {
                "id": 2,
                "conversation_id": 8,
                "sequence_no": 2,
                "timestamp": "2025-03-02T09:01:00",
                "speaker_role": "self",
                "content_text": "早呀",
            },
            {
                "id": 3,
                "conversation_id": 8,
                "sequence_no": 3,
                "timestamp": "2025-03-02T12:00:00",
                "speaker_role": "other",
                "content_text": "中午的消息",
            },
            {
                "id": 4,
                "conversation_id": 8,
                "sequence_no": 4,
                "timestamp": "2025-03-02T20:18:03",
                "speaker_role": "other",
                "content_text": "晚上的开场",
            },
            {
                "id": 5,
                "conversation_id": 8,
                "sequence_no": 5,
                "timestamp": "2025-03-02T20:18:04",
                "speaker_role": "self",
                "content_text": "目标消息",
            },
            {
                "id": 6,
                "conversation_id": 8,
                "sequence_no": 6,
                "timestamp": "2025-03-02T22:00:00",
                "speaker_role": "other",
                "content_text": "目标之后的新段",
            },
        ],
        segments=[
            {
                "id": 101,
                "source_message_ids": [1, 2],
                "start_time": "2025-03-02T09:00:00",
                "end_time": "2025-03-02T09:01:00",
            },
            {
                "id": 102,
                "source_message_ids": [3],
                "start_time": "2025-03-02T12:00:00",
                "end_time": "2025-03-02T12:00:00",
            },
            {
                "id": 103,
                "source_message_ids": [5, 4],
                "start_time": "2025-03-02T20:18:03",
                "end_time": "2025-03-02T20:18:04",
            },
            {
                "id": 104,
                "source_message_ids": [6],
                "start_time": "2025-03-02T22:00:00",
                "end_time": "2025-03-02T22:00:00",
            },
        ],
        target_message_id=5,
        replacement_content="换个轻松点的说法",
        related_topic_digests=[{"topic_id": 9, "topic_name": "闲聊"}],
        future_evidence_digests=[
            {
                "source_type": "segment_summary",
                "source_id": 801,
                "topic_id": 9,
                "topic_name": "闲聊",
                "supporting_segment_id": 104,
                "starts_at": "2025-03-02T22:00:00",
                "ends_at": "2025-03-02T22:00:00",
                "evidence_kind": "topic_linked_future_summary",
                "summary": "目标后的后续互动摘要",
                "topic_summary": "闲聊延续",
                "relevance_reason": "同一话题",
                "topic_link_score": 0.8,
                "use_policy": "modeler_only_not_character_known",
            }
        ],
        base_relationship_snapshot=None,
        persona_self=None,
        persona_other=None,
    )

    assert [item["id"] for item in context["current_segment_history"]] == [4]
    assert context["same_day_prior_segments"] == [
        {
            "segment_id": 102,
            "start_time": "2025-03-02T12:00:00",
            "end_time": "2025-03-02T12:00:00",
            "message_count": 1,
            "last_speaker_role": "other",
            "summary_hint": "other: 中午的消息",
        }
    ]
    assert context["moment_state_estimate"]["relationship_temperature"] == "unknown"
    assert context["moment_state_estimate"]["active_sensitive_topics"] == []
    assert context["cutoff_safe_facts"]["same_day_prior_segments"] == context["same_day_prior_segments"]
    assert context["future_evidence_digests"][0]["supporting_segment_id"] == 104
    assert context["related_topic_digests"] == [{"topic_id": 9, "topic_name": "闲聊"}]
    assert context["retrieval_budget"]["same_day_prior_segments"]["selected_count"] == 1
    assert context["retrieval_warnings"] == ["base_relationship_snapshot_missing"]


def test_build_context_pack_preserves_explicit_retrieval_trace_and_budget():
    context = build_context_pack(
        messages=[
            {
                "id": 1,
                "conversation_id": 21,
                "sequence_no": 1,
                "timestamp": "2025-03-02T20:18:03",
                "speaker_role": "other",
                "content_text": "开场",
            },
            {
                "id": 2,
                "conversation_id": 21,
                "sequence_no": 2,
                "timestamp": "2025-03-02T20:18:04",
                "speaker_role": "self",
                "content_text": "目标",
            },
        ],
        segments=[
            {
                "id": 11,
                "source_message_ids": [1, 2],
                "start_time": "2025-03-02T20:18:03",
                "end_time": "2025-03-02T20:18:04",
            }
        ],
        target_message_id=2,
        replacement_content="换个说法",
        related_topic_digests=[{"topic_id": 3, "topic_name": "边界试探"}],
        future_evidence_digests=[],
        base_relationship_snapshot=None,
        persona_self=None,
        persona_other=None,
        retrieval_trace={
            "related_topic_digests": [
                {
                    "topic_id": 3,
                    "topic_name": "边界试探",
                    "rank": 1,
                    "selected": True,
                    "selection_reasons": ["target_topic_overlap", "sensitive_topic"],
                }
            ],
            "future_evidence_digests": [],
        },
        retrieval_budget={
            "related_topic_digests": {
                "limit": 3,
                "candidate_count": 4,
                "selected_count": 1,
                "overflow_count": 3,
            }
        },
    )

    assert context["retrieval_trace"]["related_topic_digests"][0]["topic_name"] == "边界试探"
    assert context["retrieval_trace"]["related_topic_digests"][0]["selection_reasons"] == [
        "target_topic_overlap",
        "sensitive_topic",
    ]
    assert context["retrieval_budget"]["related_topic_digests"] == {
        "limit": 3,
        "candidate_count": 4,
        "selected_count": 1,
        "overflow_count": 3,
    }
