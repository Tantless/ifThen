from __future__ import annotations

from dataclasses import dataclass, field
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


_MESSAGE_START_RE = re.compile(r"^说话人:\s*(?P<label>.*)$")
_TIMESTAMP_RE = re.compile(r"^时间:\s*(?P<timestamp>.*)$")
_CONTENT_RE = re.compile(r"^内容:\s*(?P<content>.*)$")
_RESOURCE_ITEM_RE = re.compile(r"^\s*-\s*(?P<kind>[^:]+):\s*(?P<name>.+?)\s*$")


def parse_qq_export(text: str, self_display_name: str) -> ParsedConversation:
    lines = text.splitlines()
    chat_name = _extract_header_value(lines, "聊天名称")
    chat_type = _extract_header_value(lines, "聊天类型")
    message_count_hint = _extract_header_int(lines, "消息总数")

    messages: list[ParsedMessage] = []
    start_indices = [index for index, line in enumerate(lines) if _MESSAGE_START_RE.match(line)]

    for position, start_index in enumerate(start_indices):
        end_index = start_indices[position + 1] if position + 1 < len(start_indices) else len(lines)
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


def _parse_message_block(block_lines: list[str], start_line: int, self_display_name: str) -> ParsedMessage:
    raw_block_text = "\n".join(block_lines)
    end_line = start_line + len(block_lines) - 1

    speaker_line = block_lines[0]
    timestamp_line = block_lines[1] if len(block_lines) > 1 else ""
    content_line = block_lines[2] if len(block_lines) > 2 else ""

    speaker_label = _MESSAGE_START_RE.match(speaker_line).group("label").strip() if _MESSAGE_START_RE.match(speaker_line) else ""
    timestamp = _TIMESTAMP_RE.match(timestamp_line).group("timestamp").strip() if _TIMESTAMP_RE.match(timestamp_line) else ""
    content_text = _CONTENT_RE.match(content_line).group("content").strip() if _CONTENT_RE.match(content_line) else ""

    resource_items = _parse_resource_items(block_lines[3:])
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
