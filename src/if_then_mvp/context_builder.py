from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select

from if_then_mvp.models import Message, PersonaProfile, RelationshipSnapshot, Segment, SegmentSummary, Topic, TopicLink
from if_then_mvp.retrieval import (
    DEFAULT_FUTURE_EVIDENCE_DIGEST_LIMIT,
    DEFAULT_RELATED_TOPIC_DIGEST_LIMIT,
    build_context_pack,
)


MAX_RELATED_TOPIC_DIGESTS = DEFAULT_RELATED_TOPIC_DIGEST_LIMIT
MAX_FUTURE_EVIDENCE_ITEMS = DEFAULT_FUTURE_EVIDENCE_DIGEST_LIMIT

SENSITIVE_KEYWORDS = (
    "拒绝",
    "边界",
    "冲突",
    "修复",
    "冷淡",
    "回避",
    "试探",
    "告白",
    "暧昧",
    "压力",
    "防御",
    "顾虑",
    "不合适",
    "慢一点",
    "先不要",
)


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
    target_segment_id = _find_target_segment_id(segments=segments, target_message_id=target_message.id)
    target_topic_ids = _load_target_topic_ids(
        session,
        conversation_id=conversation_id,
        target_segment_id=target_segment_id,
    )
    active_sensitive_topics = list(snapshot.unresolved_conflict_flags or []) if snapshot is not None else []
    related_topic_digests, related_topic_trace, related_topic_budget = _load_related_topic_digests_with_trace(
        session=session,
        conversation_id=conversation_id,
        target_message=target_message,
        target_topic_ids=target_topic_ids,
        active_sensitive_topics=active_sensitive_topics,
        limit=MAX_RELATED_TOPIC_DIGESTS,
    )
    future_evidence_digests, future_evidence_trace, future_evidence_budget = _load_future_evidence_digests_with_trace(
        session=session,
        conversation_id=conversation_id,
        target_message=target_message,
        target_topic_ids=target_topic_ids,
        active_sensitive_topics=active_sensitive_topics,
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
        retrieval_trace={
            "related_topic_digests": related_topic_trace,
            "future_evidence_digests": future_evidence_trace,
        },
        retrieval_budget={
            "related_topic_digests": related_topic_budget,
            "future_evidence_digests": future_evidence_budget,
        },
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
    target_topic_ids: set[int] | None = None,
    active_sensitive_topics: list[str] | None = None,
    limit: int = MAX_RELATED_TOPIC_DIGESTS,
) -> list[dict[str, object]]:
    digests, _trace, _budget = _load_related_topic_digests_with_trace(
        session=session,
        conversation_id=conversation_id,
        target_message=target_message,
        target_topic_ids=target_topic_ids or set(),
        active_sensitive_topics=active_sensitive_topics or [],
        limit=limit,
    )
    return digests


def _load_related_topic_digests_with_trace(
    *,
    session,
    conversation_id: int,
    target_message: Message,
    target_topic_ids: set[int],
    active_sensitive_topics: list[str],
    limit: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, int]]:
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
        return [], [], _build_budget(limit=limit, candidate_count=0, selected_count=0)

    digest_map: dict[int, dict[str, object]] = {}
    for topic, topic_link, segment, segment_summary, _end_message in rows:
        digest = digest_map.setdefault(
            topic.id,
            {
                "topic_id": topic.id,
                "topic_name": topic.topic_name,
                "topic_summary": topic.topic_summary,
                "cutoff_safe_summary_parts": [],
                "supporting_segment_ids": [],
                "relevance_reasons": [],
                "topic_status": topic.topic_status,
                "max_topic_link_score": 0.0,
                "latest_supporting_end_time": segment.end_time,
                "has_conflict": False,
                "has_repair": False,
                "main_topics": [],
            },
        )
        digest["cutoff_safe_summary_parts"].append(segment_summary.summary_text)
        digest["supporting_segment_ids"].append(segment.id)
        digest["relevance_reasons"].append(topic_link.link_reason)
        digest["max_topic_link_score"] = max(float(digest["max_topic_link_score"]), float(topic_link.score))
        if str(segment.end_time) > str(digest["latest_supporting_end_time"]):
            digest["latest_supporting_end_time"] = segment.end_time
        digest["has_conflict"] = bool(digest["has_conflict"] or segment_summary.has_conflict)
        digest["has_repair"] = bool(digest["has_repair"] or segment_summary.has_repair)
        digest["main_topics"].extend(segment_summary.main_topics or [])

    candidates: list[dict[str, object]] = []
    for topic_id, digest in digest_map.items():
        sensitivity_score, sensitive_signals = _compute_sensitivity(
            texts=[
                digest["topic_name"],
                digest["topic_summary"],
                *digest["cutoff_safe_summary_parts"],
                *digest["relevance_reasons"],
                *digest["main_topics"],
            ],
            active_sensitive_topics=active_sensitive_topics,
            has_conflict=bool(digest["has_conflict"]),
            has_repair=bool(digest["has_repair"]),
        )
        stability_score = min(len(set(digest["supporting_segment_ids"])), 3)
        topic_overlap = topic_id in target_topic_ids
        selection_reasons = []
        if topic_overlap:
            selection_reasons.append("target_topic_overlap")
        if sensitivity_score > 0:
            selection_reasons.append("sensitive_topic")
        if stability_score > 1:
            selection_reasons.append("stable_topic_recurrence")
        selection_reasons.append("recent_cutoff_safe_evidence")
        candidates.append(
            {
                "payload": {
                    "topic_id": topic_id,
                    "topic_name": digest["topic_name"],
                    "cutoff_safe_summary": " | ".join(digest["cutoff_safe_summary_parts"][:3]),
                    "supporting_segment_ids": digest["supporting_segment_ids"],
                    "relevance_reason": next(iter(digest["relevance_reasons"]), ""),
                    "topic_status": digest["topic_status"],
                },
                "sort_key": (
                    int(topic_overlap),
                    sensitivity_score,
                    stability_score,
                    _timestamp_sort_value(digest["latest_supporting_end_time"]),
                    float(digest["max_topic_link_score"]),
                ),
                "trace": {
                    "topic_id": topic_id,
                    "topic_name": digest["topic_name"],
                    "selection_reasons": selection_reasons,
                    "sensitive_signals": sensitive_signals,
                    "score_breakdown": {
                        "target_topic_overlap": int(topic_overlap),
                        "sensitivity": sensitivity_score,
                        "stability": stability_score,
                        "time_proximity": _timestamp_sort_value(digest["latest_supporting_end_time"]),
                        "topic_link_score": round(float(digest["max_topic_link_score"]), 3),
                    },
                },
            }
        )

    return _select_ranked_candidates(candidates=candidates, limit=limit)


def load_future_evidence_digests(
    *,
    session,
    conversation_id: int,
    target_message: Message,
    target_topic_ids: set[int] | None = None,
    active_sensitive_topics: list[str] | None = None,
    limit: int,
) -> list[dict[str, object]]:
    digests, _trace, _budget = _load_future_evidence_digests_with_trace(
        session=session,
        conversation_id=conversation_id,
        target_message=target_message,
        target_topic_ids=target_topic_ids or set(),
        active_sensitive_topics=active_sensitive_topics or [],
        limit=limit,
    )
    return digests


def _load_future_evidence_digests_with_trace(
    *,
    session,
    conversation_id: int,
    target_message: Message,
    target_topic_ids: set[int],
    active_sensitive_topics: list[str],
    limit: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, int]]:
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
        return [], [], _build_budget(limit=limit, candidate_count=0, selected_count=0)

    candidate_map: dict[int, dict[str, object]] = {}
    for topic, topic_link, segment, segment_summary, _end_message in rows:
        sensitivity_score, sensitive_signals = _compute_sensitivity(
            texts=[
                topic.topic_name,
                topic.topic_summary,
                segment_summary.summary_text,
                topic_link.link_reason,
                *(segment_summary.main_topics or []),
            ],
            active_sensitive_topics=active_sensitive_topics,
            has_conflict=segment_summary.has_conflict,
            has_repair=segment_summary.has_repair,
        )
        stability_score = min(int(topic.segment_count), 3)
        topic_overlap = topic.id in target_topic_ids
        selection_reasons = []
        if topic_overlap:
            selection_reasons.append("target_topic_overlap")
        if sensitivity_score > 0:
            selection_reasons.append("sensitive_future_constraint")
        if stability_score > 1:
            selection_reasons.append("stable_topic_recurrence")
        selection_reasons.append("future_time_proximity")
        candidate = {
            "payload": {
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
            },
            "sort_key": (
                int(topic_overlap),
                sensitivity_score,
                stability_score,
                float(topic_link.score),
                _future_time_proximity_score(target_timestamp=target_message.timestamp, evidence_end_time=segment.end_time),
            ),
            "trace": {
                "supporting_segment_id": segment.id,
                "topic_id": topic.id,
                "topic_name": topic.topic_name,
                "selection_reasons": selection_reasons,
                "sensitive_signals": sensitive_signals,
                "score_breakdown": {
                    "target_topic_overlap": int(topic_overlap),
                    "sensitivity": sensitivity_score,
                    "stability": stability_score,
                    "topic_link_score": round(float(topic_link.score), 3),
                    "time_proximity": _future_time_proximity_score(
                        target_timestamp=target_message.timestamp,
                        evidence_end_time=segment.end_time,
                    ),
                },
            },
        }
        existing_candidate = candidate_map.get(segment.id)
        if existing_candidate is None or candidate["sort_key"] > existing_candidate["sort_key"]:
            candidate_map[segment.id] = candidate

    return _select_ranked_candidates(candidates=list(candidate_map.values()), limit=limit)


def _find_target_segment_id(*, segments: list[Segment], target_message_id: int) -> int | None:
    for segment in segments:
        if target_message_id in (segment.source_message_ids or []):
            return int(segment.id)
    return None


def _load_target_topic_ids(
    session,
    *,
    conversation_id: int,
    target_segment_id: int | None,
) -> set[int]:
    if target_segment_id is None:
        return set()
    return set(
        session.execute(
            select(TopicLink.topic_id)
            .join(Topic, Topic.id == TopicLink.topic_id)
            .where(
                Topic.conversation_id == conversation_id,
                TopicLink.segment_id == target_segment_id,
            )
        )
        .scalars()
        .all()
    )


def _compute_sensitivity(
    *,
    texts: list[object],
    active_sensitive_topics: list[str],
    has_conflict: bool,
    has_repair: bool,
) -> tuple[int, list[str]]:
    haystack = " ".join(str(text) for text in texts if text).casefold()
    signals: list[str] = []
    for keyword in SENSITIVE_KEYWORDS:
        if keyword.casefold() in haystack:
            signals.append(f"keyword:{keyword}")
    for topic in active_sensitive_topics:
        if topic and str(topic).casefold() in haystack:
            signals.append(f"active_topic:{topic}")
    if has_conflict:
        signals.append("summary_has_conflict")
    if has_repair:
        signals.append("summary_has_repair")
    unique_signals = list(dict.fromkeys(signals))
    return min(len(unique_signals), 3), unique_signals[:3]


def _select_ranked_candidates(
    *,
    candidates: list[dict[str, object]],
    limit: int,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, int]]:
    ranked_candidates = sorted(candidates, key=lambda item: item["sort_key"], reverse=True)
    selected_candidates = ranked_candidates[:limit]
    trace: list[dict[str, object]] = []
    for rank, candidate in enumerate(ranked_candidates, start=1):
        trace_entry = dict(candidate["trace"])
        trace_entry["rank"] = rank
        trace_entry["selected"] = rank <= limit
        if rank <= limit:
            trace_entry["selected_rank"] = rank
        trace.append(trace_entry)
    return (
        [candidate["payload"] for candidate in selected_candidates],
        trace,
        _build_budget(limit=limit, candidate_count=len(ranked_candidates), selected_count=len(selected_candidates)),
    )


def _build_budget(*, limit: int, candidate_count: int, selected_count: int) -> dict[str, int]:
    return {
        "limit": int(limit),
        "candidate_count": int(candidate_count),
        "selected_count": int(selected_count),
        "overflow_count": max(0, int(candidate_count) - int(selected_count)),
    }


def _timestamp_sort_value(value: object) -> float:
    if value is None:
        return 0.0
    try:
        return datetime.fromisoformat(str(value)).timestamp()
    except ValueError:
        return 0.0


def _future_time_proximity_score(*, target_timestamp: str, evidence_end_time: object) -> float:
    evidence_value = _timestamp_sort_value(evidence_end_time)
    target_value = _timestamp_sort_value(target_timestamp)
    if evidence_value == 0.0 or target_value == 0.0:
        return 0.0
    return -max(0.0, evidence_value - target_value)
