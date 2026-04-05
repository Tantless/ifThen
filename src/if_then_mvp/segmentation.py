from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta


@dataclass(slots=True)
class ParsedTimelineMessage:
    message_id: int
    timestamp: str
    speaker_role: str


@dataclass(slots=True)
class SegmentDraft:
    segment_id: int
    message_ids: list[int]
    start_time: str
    end_time: str
    self_message_count: int
    other_message_count: int
    segment_kind: str
    source_message_ids: list[int] = field(default_factory=list)
    source_segment_ids: list[int] = field(default_factory=list)


def _parse_ts(value: str) -> datetime:
    return datetime.fromisoformat(value)


def split_into_segments(messages: list[ParsedTimelineMessage], gap_minutes: int) -> list[SegmentDraft]:
    if not messages:
        return []

    gap = timedelta(minutes=gap_minutes)
    grouped_messages: list[list[ParsedTimelineMessage]] = [[messages[0]]]

    for current in messages[1:]:
        previous = grouped_messages[-1][-1]
        if _parse_ts(current.timestamp) - _parse_ts(previous.timestamp) <= gap:
            grouped_messages[-1].append(current)
            continue
        grouped_messages.append([current])

    segments: list[SegmentDraft] = []
    for index, group in enumerate(grouped_messages, start=1):
        segments.append(
            SegmentDraft(
                segment_id=index,
                message_ids=[item.message_id for item in group],
                start_time=group[0].timestamp,
                end_time=group[-1].timestamp,
                self_message_count=sum(1 for item in group if item.speaker_role == "self"),
                other_message_count=sum(1 for item in group if item.speaker_role == "other"),
                segment_kind="isolated" if len(group) == 1 else "normal",
                source_message_ids=[item.message_id for item in group],
            )
        )
    return segments


def merge_isolated_segments(segments: list[SegmentDraft], merge_window_hours: int) -> list[SegmentDraft]:
    if not segments:
        return []

    merge_window = timedelta(hours=merge_window_hours)
    merged_segments: list[SegmentDraft] = []
    cursor = 0
    next_segment_id = 1

    while cursor < len(segments):
        current = segments[cursor]
        if current.segment_kind != "isolated":
            merged_segments.append(_copy_segment(current, segment_id=next_segment_id))
            next_segment_id += 1
            cursor += 1
            continue

        chain = [current]
        look_ahead = cursor + 1
        while look_ahead < len(segments) and segments[look_ahead].segment_kind == "isolated":
            chain.append(segments[look_ahead])
            look_ahead += 1

        chain_span = _parse_ts(chain[-1].end_time) - _parse_ts(chain[0].start_time)
        if len(chain) >= 2 and chain_span <= merge_window:
            merged_segments.append(
                SegmentDraft(
                    segment_id=next_segment_id,
                    message_ids=[message_id for item in chain for message_id in item.message_ids],
                    start_time=chain[0].start_time,
                    end_time=chain[-1].end_time,
                    self_message_count=sum(item.self_message_count for item in chain),
                    other_message_count=sum(item.other_message_count for item in chain),
                    segment_kind="merged_isolated",
                    source_message_ids=[message_id for item in chain for message_id in item.message_ids],
                    source_segment_ids=[item.segment_id for item in chain],
                )
            )
            next_segment_id += 1
        else:
            for item in chain:
                merged_segments.append(_copy_segment(item, segment_id=next_segment_id))
                next_segment_id += 1

        cursor = look_ahead

    return merged_segments


def _copy_segment(segment: SegmentDraft, *, segment_id: int) -> SegmentDraft:
    return SegmentDraft(
        segment_id=segment_id,
        message_ids=list(segment.message_ids),
        start_time=segment.start_time,
        end_time=segment.end_time,
        self_message_count=segment.self_message_count,
        other_message_count=segment.other_message_count,
        segment_kind=segment.segment_kind,
        source_message_ids=list(segment.source_message_ids),
        source_segment_ids=list(segment.source_segment_ids),
    )
