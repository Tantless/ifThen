from __future__ import annotations

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


def build_segment_summary(
    *,
    llm_client: ChatJSONClient,
    segment_messages: list[dict],
    previous_snapshot_summary: str | None,
) -> SegmentSummaryPayload:
    prompt_lines: list[str] = []
    if previous_snapshot_summary:
        prompt_lines.append(f"Previous snapshot: {previous_snapshot_summary}")
    prompt_lines.extend(f"{item['speaker_role']}: {item['content_text']}" for item in segment_messages)
    return llm_client.chat_json(
        system_prompt=SEGMENT_SYSTEM_PROMPT,
        user_prompt="\n".join(prompt_lines),
        response_model=SegmentSummaryPayload,
    )


def build_topic_payload(*, llm_client: ChatJSONClient, segment_summaries: list[dict]) -> TopicPayload:
    return llm_client.chat_json(
        system_prompt="Group these summaries into one recurring topic. Return JSON.",
        user_prompt="\n".join(item["summary_text"] for item in segment_summaries),
        response_model=TopicPayload,
    )


def build_persona_payload(
    *,
    llm_client: ChatJSONClient,
    subject_role: str,
    segment_summaries: list[dict],
) -> PersonaPayload:
    prompt = f"Subject role: {subject_role}\n" + "\n".join(item["summary_text"] for item in segment_summaries)
    return llm_client.chat_json(
        system_prompt="Extract stable speaking and conflict traits. Avoid future-event specifics.",
        user_prompt=prompt,
        response_model=PersonaPayload,
    )


def build_snapshot_payload(
    *,
    llm_client: ChatJSONClient,
    segment_summary: dict,
    prior_snapshot: str | None,
) -> SnapshotPayload:
    prompt = f"Prior snapshot: {prior_snapshot or 'none'}\nSegment summary: {segment_summary['summary_text']}"
    return llm_client.chat_json(
        system_prompt="Estimate relationship state after this segment. Return JSON.",
        user_prompt=prompt,
        response_model=SnapshotPayload,
    )
