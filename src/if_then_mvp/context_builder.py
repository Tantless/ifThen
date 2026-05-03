from __future__ import annotations

from typing import Any

from sqlalchemy import select

from if_then_mvp.models import Message, PersonaProfile, RelationshipSnapshot, Segment, SegmentSummary, Topic, TopicLink
from if_then_mvp.retrieval import build_context_pack


MAX_FUTURE_EVIDENCE_ITEMS = 3


def build_conversation_context_pack(
    session,
    *,
    conversation_id: int,
    target_message: Message,
    replacement_content: str,
) -> dict[str, object]:
    messages = (
        session.execute(
            select(Message)
            .where(Message.conversation_id == conversation_id)
            .order_by(Message.timestamp.asc(), Message.sequence_no.asc(), Message.id.asc())
        )
        .scalars()
        .all()
    )
    segments = (
        session.execute(
            select(Segment)
            .where(Segment.conversation_id == conversation_id)
            .order_by(Segment.start_time.asc(), Segment.id.asc())
        )
        .scalars()
        .all()
    )
    snapshot = (
        session.execute(
            select(RelationshipSnapshot)
            .join(Message, RelationshipSnapshot.as_of_message_id == Message.id)
            .where(
                RelationshipSnapshot.conversation_id == conversation_id,
                (
                    (RelationshipSnapshot.as_of_time < target_message.timestamp)
                    | (
                        (RelationshipSnapshot.as_of_time == target_message.timestamp)
                        & (Message.sequence_no < target_message.sequence_no)
                    )
                ),
            )
            .order_by(RelationshipSnapshot.as_of_time.desc(), Message.sequence_no.desc())
        )
        .scalars()
        .first()
    )
    related_topic_digests = load_related_topic_digests(
        session=session,
        conversation_id=conversation_id,
        target_message=target_message,
    )
    future_evidence_digests = load_future_evidence_digests(
        session=session,
        conversation_id=conversation_id,
        target_message=target_message,
        limit=MAX_FUTURE_EVIDENCE_ITEMS,
    )
    personas = (
        session.execute(select(PersonaProfile).where(PersonaProfile.conversation_id == conversation_id))
        .scalars()
        .all()
    )
    persona_self = next((item for item in personas if item.subject_role == "self"), None)
    persona_other = next((item for item in personas if item.subject_role == "other"), None)

    return build_context_pack(
        messages=[message_to_context_dict(item) for item in messages],
        segments=[segment_to_context_dict(item) for item in segments],
        target_message_id=target_message.id,
        replacement_content=replacement_content,
        related_topic_digests=related_topic_digests,
        future_evidence_digests=future_evidence_digests,
        base_relationship_snapshot=snapshot_to_context_dict(snapshot),
        persona_self=persona_to_context_dict(persona_self),
        persona_other=persona_to_context_dict(persona_other),
    )


def message_to_context_dict(message: Message) -> dict[str, object]:
    return {
        "id": message.id,
        "conversation_id": message.conversation_id,
        "sequence_no": message.sequence_no,
        "timestamp": message.timestamp,
        "speaker_role": message.speaker_role,
        "content_text": message.content_text,
    }


def segment_to_context_dict(segment: Segment) -> dict[str, object]:
    return {
        "id": segment.id,
        "source_message_ids": segment.source_message_ids or [],
        "start_time": segment.start_time,
        "end_time": segment.end_time,
    }


def snapshot_to_context_dict(snapshot: RelationshipSnapshot | None) -> dict[str, object] | None:
    if snapshot is None:
        return None
    return {
        "relationship_temperature": snapshot.relationship_temperature,
        "tension_level": snapshot.tension_level,
        "openness_level": snapshot.openness_level,
        "initiative_balance": snapshot.initiative_balance,
        "defensiveness_level": snapshot.defensiveness_level,
        "relationship_phase": snapshot.relationship_phase,
        "active_sensitive_topics": snapshot.unresolved_conflict_flags,
    }


def persona_to_context_dict(persona: PersonaProfile | None) -> dict[str, object] | None:
    if persona is None:
        return None
    return {
        "global_persona_summary": persona.global_persona_summary,
        "style_traits": persona.style_traits,
        "conflict_traits": persona.conflict_traits,
        "relationship_specific_patterns": persona.relationship_specific_patterns,
        "confidence": persona.confidence,
    }


def load_related_topic_digests(
    *,
    session,
    conversation_id: int,
    target_message: Message,
) -> list[dict[str, object]]:
    rows = (
        session.execute(
            select(Topic, TopicLink, Segment, SegmentSummary, Message)
            .join(TopicLink, TopicLink.topic_id == Topic.id)
            .join(Segment, TopicLink.segment_id == Segment.id)
            .join(SegmentSummary, SegmentSummary.segment_id == Segment.id)
            .join(Message, Segment.end_message_id == Message.id)
            .where(
                Topic.conversation_id == conversation_id,
                (
                    (Segment.end_time < target_message.timestamp)
                    | (
                        (Segment.end_time == target_message.timestamp)
                        & (Message.sequence_no < target_message.sequence_no)
                    )
                ),
            )
            .order_by(Topic.id.asc(), Segment.end_time.asc(), Message.sequence_no.asc(), Segment.id.asc())
        )
        .all()
    )
    if not rows:
        return []

    digest_map: dict[int, dict[str, object]] = {}
    for topic, topic_link, segment, segment_summary, _end_message in rows:
        digest = digest_map.setdefault(
            topic.id,
            {
                "topic_id": topic.id,
                "topic_name": topic.topic_name,
                "cutoff_safe_summary_parts": [],
                "supporting_segment_ids": [],
                "relevance_reason": topic_link.link_reason,
                "topic_status": topic.topic_status,
            },
        )
        digest["cutoff_safe_summary_parts"].append(segment_summary.summary_text)
        digest["supporting_segment_ids"].append(segment.id)

    return [
        {
            "topic_id": topic_id,
            "topic_name": digest["topic_name"],
            "cutoff_safe_summary": " | ".join(digest["cutoff_safe_summary_parts"][:3]),
            "supporting_segment_ids": digest["supporting_segment_ids"],
            "relevance_reason": digest["relevance_reason"],
            "topic_status": digest["topic_status"],
        }
        for topic_id, digest in digest_map.items()
    ]


def load_future_evidence_digests(
    *,
    session,
    conversation_id: int,
    target_message: Message,
    limit: int,
) -> list[dict[str, object]]:
    rows = (
        session.execute(
            select(Topic, TopicLink, Segment, SegmentSummary, Message)
            .join(TopicLink, TopicLink.topic_id == Topic.id)
            .join(Segment, TopicLink.segment_id == Segment.id)
            .join(SegmentSummary, SegmentSummary.segment_id == Segment.id)
            .join(Message, Segment.end_message_id == Message.id)
            .where(
                Topic.conversation_id == conversation_id,
                (
                    (Segment.end_time > target_message.timestamp)
                    | (
                        (Segment.end_time == target_message.timestamp)
                        & (Message.sequence_no > target_message.sequence_no)
                    )
                ),
            )
            .order_by(TopicLink.score.desc(), Segment.end_time.asc(), Message.sequence_no.asc(), Segment.id.asc())
        )
        .all()
    )
    if not rows:
        return []

    evidence_items: list[dict[str, object]] = []
    seen_segment_ids: set[int] = set()
    for topic, topic_link, segment, segment_summary, _end_message in rows:
        if segment.id in seen_segment_ids:
            continue
        seen_segment_ids.add(segment.id)
        evidence_items.append(
            {
                "source_type": "segment_summary",
                "source_id": segment_summary.id,
                "topic_id": topic.id,
                "topic_name": topic.topic_name,
                "supporting_segment_id": segment.id,
                "starts_at": segment.start_time,
                "ends_at": segment.end_time,
                "evidence_kind": "topic_linked_future_summary",
                "summary": segment_summary.summary_text,
                "topic_summary": topic.topic_summary,
                "relevance_reason": topic_link.link_reason,
                "topic_link_score": topic_link.score,
                "use_policy": "modeler_only_not_character_known",
            }
        )
        if len(evidence_items) >= limit:
            break
    return evidence_items
