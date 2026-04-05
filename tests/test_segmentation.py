from if_then_mvp.segmentation import ParsedTimelineMessage, merge_isolated_segments, split_into_segments


def test_split_into_segments_marks_only_normal_and_single_message_isolated():
    messages = [
        ParsedTimelineMessage(1, "2025-03-02T20:18:03", "other"),
        ParsedTimelineMessage(2, "2025-03-02T20:18:30", "self"),
        ParsedTimelineMessage(3, "2025-03-02T23:30:43", "other"),
        ParsedTimelineMessage(4, "2025-03-03T23:30:43", "self"),
    ]

    segments = split_into_segments(messages, gap_minutes=30)

    assert [segment.segment_kind for segment in segments] == ["normal", "isolated", "isolated"]
    assert [segment.message_ids for segment in segments] == [[1, 2], [3], [4]]
    assert all(
        len(segment.message_ids) == 1
        for segment in segments
        if segment.segment_kind == "isolated"
    )


def test_merge_isolated_segments_merges_only_adjacent_chain_within_24_hours():
    messages = [
        ParsedTimelineMessage(1, "2025-03-02T10:00:00", "self"),
        ParsedTimelineMessage(2, "2025-03-02T10:05:00", "other"),
        ParsedTimelineMessage(3, "2025-03-02T15:00:00", "self"),
        ParsedTimelineMessage(4, "2025-03-02T16:00:00", "other"),
        ParsedTimelineMessage(5, "2025-03-02T16:40:00", "self"),
        ParsedTimelineMessage(6, "2025-03-02T16:45:00", "other"),
        ParsedTimelineMessage(7, "2025-03-04T16:00:00", "other"),
    ]

    initial = split_into_segments(messages, gap_minutes=30)
    merged = merge_isolated_segments(initial, merge_window_hours=24)

    assert [segment.segment_kind for segment in initial] == ["normal", "isolated", "isolated", "normal", "isolated"]
    assert [segment.segment_kind for segment in merged] == ["normal", "merged_isolated", "normal", "isolated"]
    assert merged[1].message_ids == [3, 4]
    assert merged[1].source_message_ids == [3, 4]
    assert merged[1].source_segment_ids == [2, 3]


def test_merge_isolated_segments_does_not_merge_when_adjacent_isolated_chain_spans_over_24_hours():
    isolated_chain = [
        ParsedTimelineMessage(1, "2025-03-02T10:00:00", "self"),
        ParsedTimelineMessage(2, "2025-03-02T10:05:00", "other"),
        ParsedTimelineMessage(3, "2025-03-02T20:00:00", "other"),
        ParsedTimelineMessage(4, "2025-03-03T09:00:00", "self"),
        ParsedTimelineMessage(5, "2025-03-04T20:30:01", "self"),
    ]

    initial = split_into_segments(isolated_chain, gap_minutes=30)
    merged = merge_isolated_segments(initial, merge_window_hours=24)

    assert [segment.segment_kind for segment in initial] == ["normal", "isolated", "isolated", "isolated"]
    assert [segment.segment_kind for segment in merged] == ["normal", "isolated", "isolated", "isolated"]
    assert all(segment.segment_kind != "merged_isolated" for segment in merged)
