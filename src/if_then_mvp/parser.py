from __future__ import annotations

from dataclasses import dataclass, field
from functools import lru_cache
import re
from typing import Any


@dataclass(slots=True)
class ParsedMessage:
    speaker_name: str
    speaker_role: str
    timestamp: str
    content_text: str
    message_type: str
    resource_items: list[dict[str, Any]] | None = None
    parse_flags: list[str] = field(default_factory=list)
    raw_block_text: str | None = None
    raw_speaker_label: str | None = None
    source_line_start: int | None = None
    source_line_end: int | None = None


@dataclass(slots=True)
class ParsedConversation:
    chat_name: str | None
    chat_type: str | None
    message_count_hint: int | None
    messages: list[ParsedMessage] = field(default_factory=list)


_SPEAKER_LINE_RE = re.compile(r"^(?P<label>.+):\s*$")
_TIMESTAMP_LINE_RE = re.compile(
    r"^时间:\s*(?P<timestamp>\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}(?:\.\d+)?)\s*$"
)
_CONTENT_RE = re.compile(r"^内容:\s*(?P<content>.*)$")
_RESOURCE_ITEM_RE = re.compile(r"^\s*-\s*(?P<kind>[^:]+):\s*(?P<name>.+?)\s*$")


def parse_qq_export(text: str, self_display_name: str) -> ParsedConversation:
    lines = text.splitlines()
    chat_name = _extract_header_value(lines, "聊天名称")
    chat_type = _extract_header_value(lines, "聊天类型")
    message_count_hint = _extract_header_int(lines, "消息总数")

    messages: list[ParsedMessage] = []
    message_ranges = _find_message_ranges(lines, message_count_hint)

    for start_index, end_index in message_ranges:
        block_lines = lines[start_index:end_index]
        while block_lines and not block_lines[-1].strip():
            block_lines.pop()

        message = _parse_message_block(block_lines, start_index + 1, self_display_name)
        messages.append(message)

    return ParsedConversation(
        chat_name=chat_name,
        chat_type=chat_type,
        message_count_hint=message_count_hint,
        messages=messages,
    )


def _extract_header_value(lines: list[str], header_name: str) -> str | None:
    prefix = f"{header_name}:"
    for line in lines:
        if line.startswith(prefix):
            return line[len(prefix) :].strip()
    return None


def _extract_header_int(lines: list[str], header_name: str) -> int | None:
    value = _extract_header_value(lines, header_name)
    if value is None or not value:
        return None
    try:
        return int(value)
    except ValueError:
        return None


def _find_message_start_indices(lines: list[str]) -> list[int]:
    start_indices: list[int] = []
    for index, line in enumerate(lines):
        if not _SPEAKER_LINE_RE.match(line):
            continue
        if index > 0 and lines[index - 1].strip():
            continue
        timestamp_index = _next_nonblank_line_index(lines, index + 1)
        if timestamp_index is None or not _TIMESTAMP_LINE_RE.match(lines[timestamp_index]):
            continue
        content_index = _next_nonblank_line_index(lines, timestamp_index + 1)
        if content_index is None or not _CONTENT_RE.match(lines[content_index]):
            continue
        start_indices.append(index)
    return start_indices


def _find_message_ranges(lines: list[str], message_count_hint: int | None) -> list[tuple[int, int]]:
    candidate_start_indices = _find_message_start_indices(lines)
    if not candidate_start_indices:
        return []

    start_indices = candidate_start_indices
    if message_count_hint and 0 < message_count_hint < len(candidate_start_indices):
        resolved = _resolve_sequential_message_starts(lines, candidate_start_indices, message_count_hint)
        if resolved is not None:
            start_indices = list(resolved)

    return [
        (
            start_index,
            start_indices[position + 1] if position + 1 < len(start_indices) else len(lines),
        )
        for position, start_index in enumerate(start_indices)
    ]


def _resolve_sequential_message_starts(
    lines: list[str],
    candidate_start_indices: list[int],
    message_count_hint: int,
) -> tuple[int, ...] | None:
    if message_count_hint > len(candidate_start_indices):
        return None

    @lru_cache(maxsize=None)
    def choose_from(
        current_position: int,
        remaining_count: int,
    ) -> tuple[tuple[int, ...], tuple[tuple[int, int, int], ...]] | None:
        current_start = candidate_start_indices[current_position]
        if remaining_count == 1:
            return (current_start,), ()

        max_next_position = len(candidate_start_indices) - remaining_count + 1
        best_choice: tuple[tuple[int, ...], tuple[tuple[int, int, int], ...]] | None = None
        for next_position in range(current_position + 1, max_next_position + 1):
            rest = choose_from(next_position, remaining_count - 1)
            if rest is not None:
                rest_sequence, rest_score = rest
                following_position = rest_sequence[1] if len(rest_sequence) > 1 else None
                selected_start_score = _score_selected_start(
                    lines=lines,
                    candidate_start_indices=candidate_start_indices,
                    previous_start_index=current_start,
                    selected_start_index=rest_sequence[0],
                    following_start_index=following_position,
                )
                candidate_choice = (
                    (current_start, *rest_sequence),
                    rest_score + (selected_start_score,),
                )
                if best_choice is None or candidate_choice[1] < best_choice[1]:
                    best_choice = candidate_choice
        return best_choice

    resolved = choose_from(0, message_count_hint)
    if resolved is None:
        return None
    return resolved[0]


def _score_selected_start(
    lines: list[str],
    candidate_start_indices: list[int],
    previous_start_index: int,
    selected_start_index: int,
    following_start_index: int | None,
) -> tuple[int, int, int]:
    if following_start_index is not None:
        return (0, 0, selected_start_index)

    return (
        _final_block_continuation_tail_penalty(lines, candidate_start_indices, selected_start_index),
        _same_timestamp_penalty(lines, previous_start_index, selected_start_index),
        selected_start_index,
    )


def _final_block_continuation_tail_penalty(
    lines: list[str],
    candidate_start_indices: list[int],
    selected_start_index: int,
) -> int:
    first_nested_candidate_index = next(
        (start_index for start_index in candidate_start_indices if start_index > selected_start_index),
        None,
    )
    if first_nested_candidate_index is None:
        return 0

    timestamp_index = _next_nonblank_line_index(lines, selected_start_index + 1)
    if timestamp_index is None:
        return 0
    content_index = _next_nonblank_line_index(lines, timestamp_index + 1)
    if content_index is None:
        return 0

    for line in lines[content_index + 1 : first_nested_candidate_index]:
        if line.strip():
            return 1
    return 0


def _same_timestamp_penalty(lines: list[str], previous_start_index: int, selected_start_index: int) -> int:
    previous_timestamp = _timestamp_for_start(lines, previous_start_index)
    selected_timestamp = _timestamp_for_start(lines, selected_start_index)
    return int(bool(previous_timestamp and selected_timestamp and previous_timestamp == selected_timestamp))


def _timestamp_for_start(lines: list[str], start_index: int) -> str:
    timestamp_index = _next_nonblank_line_index(lines, start_index + 1)
    if timestamp_index is None:
        return ""
    match = _TIMESTAMP_LINE_RE.match(lines[timestamp_index])
    if match is None:
        return ""
    return match.group("timestamp").strip()


def _next_nonblank_line_index(lines: list[str], start_index: int) -> int | None:
    for index in range(start_index, len(lines)):
        if lines[index].strip():
            return index
    return None


def _parse_message_block(block_lines: list[str], start_line: int, self_display_name: str) -> ParsedMessage:
    raw_block_text = "\n".join(block_lines)
    end_line = start_line + len(block_lines) - 1

    speaker_line = block_lines[0]
    timestamp_line = block_lines[1] if len(block_lines) > 1 else ""
    body_lines = block_lines[2:] if len(block_lines) > 2 else []

    speaker_label = _SPEAKER_LINE_RE.match(speaker_line).group("label").strip() if _SPEAKER_LINE_RE.match(speaker_line) else ""
    timestamp = _TIMESTAMP_LINE_RE.match(timestamp_line).group("timestamp").strip() if _TIMESTAMP_LINE_RE.match(timestamp_line) else ""
    content_text, resource_lines = _parse_body_lines(body_lines)

    resource_items = _parse_resource_items(resource_lines)
    message_type = _classify_message_type(content_text, resource_items, speaker_label)
    speaker_role = _classify_speaker_role(speaker_label, self_display_name)

    parse_flags: list[str] = []
    if speaker_role == "unknown":
        parse_flags.append("unknown_speaker")
    if resource_items:
        parse_flags.append("resource_present")

    return ParsedMessage(
        speaker_name=speaker_label,
        speaker_role=speaker_role,
        timestamp=timestamp,
        content_text=content_text,
        message_type=message_type,
        resource_items=resource_items,
        parse_flags=parse_flags,
        raw_block_text=raw_block_text,
        raw_speaker_label=speaker_label,
        source_line_start=start_line,
        source_line_end=end_line,
    )


def _parse_body_lines(lines: list[str]) -> tuple[str, list[str]]:
    content_lines: list[str] = []
    resource_lines: list[str] = []
    in_resources = False
    content_started = False

    for line in lines:
        if not in_resources and not content_started and _CONTENT_RE.match(line):
            content_lines.append(_CONTENT_RE.match(line).group("content"))
            content_started = True
            continue
        if line == "资源:":
            in_resources = True
            continue
        if in_resources:
            resource_lines.append(line)
            continue
        content_lines.append(line)
        content_started = True

    content_text = "\n".join(content_lines)
    return content_text, resource_lines


def _parse_resource_items(lines: list[str]) -> list[dict[str, Any]] | None:
    resource_items: list[dict[str, Any]] = []
    for line in lines:
        match = _RESOURCE_ITEM_RE.match(line)
        if not match:
            continue
        resource_items.append({"kind": match.group("kind").strip(), "name": match.group("name").strip()})
    return resource_items or None


def _classify_speaker_role(speaker_label: str, self_display_name: str) -> str:
    if speaker_label == self_display_name:
        return "self"
    if not speaker_label:
        return "unknown"
    if re.fullmatch(r"\d+:?", speaker_label):
        return "unknown"
    return "other"


def _classify_message_type(
    content_text: str,
    resource_items: list[dict[str, Any]] | None,
    speaker_label: str,
) -> str:
    content = content_text.strip()
    resource_kinds = {item["kind"] for item in resource_items or []}

    if speaker_label in {"系统消息", "系统提示", "系统"} or content.startswith("[系统"):
        return "system"
    if "[图片:" in content or "image" in resource_kinds:
        return "image"
    if "[文件:" in content or "file" in resource_kinds:
        return "file"
    if not content and not resource_items:
        return "unknown"
    return "text"
