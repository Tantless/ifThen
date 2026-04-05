from __future__ import annotations

import json

from pydantic import BaseModel

from if_then_mvp.llm import ChatJSONClient


class SegmentSummaryPayload(BaseModel):
    summary_text: str
    main_topics: list[str]
    self_stance: str
    other_stance: str
    emotional_tone: str
    interaction_pattern: str
    has_conflict: bool
    has_repair: bool
    has_closeness_signal: bool
    outcome: str
    relationship_impact: str
    confidence: float


class TopicPayload(BaseModel):
    topic_name: str
    topic_summary: str
    topic_status: str
    relevance_reason: str


class PersonaPayload(BaseModel):
    global_persona_summary: str
    style_traits: list[str]
    conflict_traits: list[str]
    relationship_specific_patterns: list[str]
    confidence: float


class SnapshotPayload(BaseModel):
    relationship_temperature: str
    tension_level: str
    openness_level: str
    initiative_balance: str
    defensiveness_level: str
    unresolved_conflict_flags: list[str]
    relationship_phase: str
    snapshot_summary: str


SEGMENT_SYSTEM_PROMPT = (
    "You summarize a cutoff-safe conversation segment. "
    "Return concise JSON and do not reference future events."
)
TOPIC_SYSTEM_PROMPT = (
    "You group cutoff-safe segment summaries into one recurring topic. "
    "Return concise JSON and do not reference future events."
)
PERSONA_SYSTEM_PROMPT = (
    "You extract stable speaking and conflict traits from cutoff-safe evidence. "
    "Return concise JSON and do not reference future events."
)
SNAPSHOT_SYSTEM_PROMPT = (
    "You estimate the relationship state after a cutoff-safe segment. "
    "Return concise JSON and do not reference future events."
)


def build_segment_summary(
    *,
    llm_client: ChatJSONClient,
    segment_messages: list[dict],
    previous_snapshot_summary: str | None,
) -> SegmentSummaryPayload:
    return llm_client.chat_json(
        system_prompt=SEGMENT_SYSTEM_PROMPT,
        user_prompt=_build_segment_prompt(
            segment_messages=segment_messages,
            previous_snapshot_summary=previous_snapshot_summary,
        ),
        response_model=SegmentSummaryPayload,
    )


def build_topic_payload(*, llm_client: ChatJSONClient, segment_summaries: list[dict]) -> TopicPayload:
    return llm_client.chat_json(
        system_prompt=TOPIC_SYSTEM_PROMPT,
        user_prompt=_build_jsonl_prompt(
            heading="Segment summaries JSONL:",
            items=segment_summaries,
        ),
        response_model=TopicPayload,
    )


def build_persona_payload(
    *,
    llm_client: ChatJSONClient,
    subject_role: str,
    segment_summaries: list[dict],
) -> PersonaPayload:
    return llm_client.chat_json(
        system_prompt=PERSONA_SYSTEM_PROMPT,
        user_prompt=_build_persona_prompt(
            subject_role=subject_role,
            segment_summaries=segment_summaries,
        ),
        response_model=PersonaPayload,
    )


def build_snapshot_payload(
    *,
    llm_client: ChatJSONClient,
    segment_summary: dict,
    prior_snapshot: str | None,
) -> SnapshotPayload:
    return llm_client.chat_json(
        system_prompt=SNAPSHOT_SYSTEM_PROMPT,
        user_prompt=_build_snapshot_prompt(
            segment_summary=segment_summary,
            prior_snapshot=prior_snapshot,
        ),
        response_model=SnapshotPayload,
    )


def _build_segment_prompt(*, segment_messages: list[dict], previous_snapshot_summary: str | None) -> str:
    lines: list[str] = []
    if previous_snapshot_summary:
        lines.append("Previous snapshot JSON:")
        lines.append(_to_json_line({"snapshot_summary": previous_snapshot_summary}))
    lines.append("Segment messages JSONL:")
    lines.extend(
        _to_json_line(
            {
                "speaker_role": item["speaker_role"],
                "content_text": item["content_text"],
            }
        )
        for item in segment_messages
    )
    return "\n".join(lines)


def _build_persona_prompt(*, subject_role: str, segment_summaries: list[dict]) -> str:
    lines = [
        "Persona request JSON:",
        _to_json_line({"subject_role": subject_role}),
        "Segment summaries JSONL:",
    ]
    lines.extend(_to_json_line(item) for item in segment_summaries)
    return "\n".join(lines)


def _build_snapshot_prompt(*, segment_summary: dict, prior_snapshot: str | None) -> str:
    lines = [
        "Prior snapshot JSON:",
        _to_json_line({"snapshot_summary": prior_snapshot or "none"}),
        "Segment summary JSON:",
        _to_json_line(segment_summary),
    ]
    return "\n".join(lines)


def _build_jsonl_prompt(*, heading: str, items: list[dict]) -> str:
    lines = [heading]
    lines.extend(_to_json_line(item) for item in items)
    return "\n".join(lines)


def _to_json_line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
