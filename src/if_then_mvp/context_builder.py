from __future__ import annotations

from datetime import datetime
import re
from typing import Any

from sqlalchemy import select

from if_then_mvp.config import get_settings
from if_then_mvp.models import Message, PersonaProfile, RelationshipSnapshot, Segment, SegmentSummary, Topic, TopicLink
from if_then_mvp.retrieval import (
    DEFAULT_FUTURE_EVIDENCE_DIGEST_LIMIT,
    DEFAULT_OBJECTIVE_MOMENT_FACT_LIMIT,
    DEFAULT_RELATED_TOPIC_DIGEST_LIMIT,
    build_context_pack,
)


MAX_RELATED_TOPIC_DIGESTS = DEFAULT_RELATED_TOPIC_DIGEST_LIMIT
MAX_FUTURE_EVIDENCE_ITEMS = DEFAULT_FUTURE_EVIDENCE_DIGEST_LIMIT
MAX_OBJECTIVE_MOMENT_FACTS = DEFAULT_OBJECTIVE_MOMENT_FACT_LIMIT
OBJECTIVE_MOMENT_WINDOW_MESSAGES = 8
OBJECTIVE_MOMENT_WINDOW_MINUTES = 10
RECENT_INTERACTION_WINDOW_MESSAGES = 12
RECENT_ROLE_STYLE_SAMPLE_SIZE = 6
SHORT_STYLE_MESSAGE_CHAR_LIMIT = 12
LONG_STYLE_MESSAGE_CHAR_LIMIT = 36
MAX_STYLE_SIGNAL_ITEMS = 3

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
STYLE_PARTICLES = (
    "hhh",
    "哈哈",
    "哈哈哈",
    "嗯",
    "哦",
    "好",
    "啊",
    "吧",
    "嘛",
    "呀",
    "诶",
    "欸",
)
STYLE_PUNCTUATION = ("。", "，", "？", "！", "…", "~", "～")
PLACEHOLDER_MESSAGE_PATTERN = re.compile(r"^\[[^\]]+\]$")
ACTIVITY_STARTERS = (
    "在",
    "看",
    "写",
    "打",
    "刷",
    "玩",
    "吃",
    "喝",
    "洗",
    "收拾",
    "躺",
    "睡",
    "忙",
    "复习",
    "上课",
    "下课",
    "回家",
    "出门",
    "走路",
    "坐车",
)
MENTAL_STATE_SIGNALS = ("想", "纠结", "担心", "烦", "累", "困", "紧张", "害怕", "难受", "卡着")
FUTURE_OUTCOME_SIGNALS = (
    "后来",
    "之后",
    "以后",
    "下次",
    "明天",
    "拒绝",
    "不合适",
    "不要追问",
    "别追问",
    "慢一点",
    "边界",
    "告白",
    "喜欢你",
    "不喜欢",
)


def build_conversation_context_pack(
    session,
    *,
    conversation_id: int,
    target_message: Message,
    replacement_content: str,
) -> dict[str, object]:
    settings = get_settings()
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
    if settings.enable_future_evidence:
        (
            future_evidence_digests,
            future_evidence_trace,
            future_evidence_budget,
        ) = _load_future_evidence_digests_with_trace(
            session=session,
            conversation_id=conversation_id,
            target_message=target_message,
            target_topic_ids=target_topic_ids,
            active_sensitive_topics=active_sensitive_topics,
            limit=MAX_FUTURE_EVIDENCE_ITEMS,
        )
        future_evidence_disabled = False
    else:
        future_evidence_digests = []
        future_evidence_trace = []
        future_evidence_budget = _build_budget(limit=MAX_FUTURE_EVIDENCE_ITEMS, candidate_count=0, selected_count=0)
        future_evidence_disabled = True
    (
        objective_moment_facts,
        objective_moment_trace,
        objective_moment_budget,
    ) = _load_objective_moment_facts_with_trace(
        session=session,
        messages=messages,
        segments=segments,
        target_message=target_message,
        target_segment_id=target_segment_id,
        target_topic_ids=target_topic_ids,
        limit=MAX_OBJECTIVE_MOMENT_FACTS,
    )
    personas = (
        session.execute(select(PersonaProfile).where(PersonaProfile.conversation_id == conversation_id))
        .scalars()
        .all()
    )
    style_profiles = _build_role_style_profiles(
        messages=messages,
        target_message=target_message,
        snapshot=snapshot,
    )
    persona_self = next((item for item in personas if item.subject_role == "self"), None)
    persona_other = next((item for item in personas if item.subject_role == "other"), None)

    context_pack = build_context_pack(
        messages=[message_to_context_dict(item) for item in messages],
        segments=[segment_to_context_dict(item) for item in segments],
        target_message_id=target_message.id,
        replacement_content=replacement_content,
        related_topic_digests=related_topic_digests,
        future_evidence_digests=future_evidence_digests,
        objective_moment_facts=objective_moment_facts,
        base_relationship_snapshot=snapshot_to_context_dict(snapshot),
        persona_self=persona_to_context_dict(
            persona_self,
            deterministic_style_profile=style_profiles.get("self"),
        ),
        persona_other=persona_to_context_dict(
            persona_other,
            deterministic_style_profile=style_profiles.get("other"),
        ),
        retrieval_trace={
            "related_topic_digests": related_topic_trace,
            "future_evidence_digests": future_evidence_trace,
            "objective_moment_facts": objective_moment_trace,
        },
        retrieval_budget={
            "related_topic_digests": related_topic_budget,
            "future_evidence_digests": future_evidence_budget,
            "objective_moment_facts": objective_moment_budget,
        },
    )
    if future_evidence_disabled:
        retrieval_warnings = list(context_pack.get("retrieval_warnings") or [])
        if "future_evidence_disabled" not in retrieval_warnings:
            retrieval_warnings.append("future_evidence_disabled")
        context_pack["retrieval_warnings"] = retrieval_warnings
    return context_pack


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


def persona_to_context_dict(
    persona: PersonaProfile | None,
    *,
    deterministic_style_profile: dict[str, object] | None = None,
) -> dict[str, object] | None:
    if persona is None:
        if deterministic_style_profile is None:
            return None
        return {
            "deterministic_style_profile": deterministic_style_profile,
        }
    payload = {
        "global_persona_summary": persona.global_persona_summary,
        "style_traits": persona.style_traits,
        "conflict_traits": persona.conflict_traits,
        "relationship_specific_patterns": persona.relationship_specific_patterns,
        "confidence": persona.confidence,
    }
    if deterministic_style_profile is not None:
        payload["deterministic_style_profile"] = deterministic_style_profile
    return payload


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


def _load_objective_moment_facts_with_trace(
    *,
    session,
    messages: list[Message],
    segments: list[Segment],
    target_message: Message,
    target_segment_id: int | None,
    target_topic_ids: set[int],
    limit: int,
) -> tuple[dict[str, object], list[dict[str, object]], dict[str, int]]:
    candidates = _objective_moment_candidate_messages(
        session=session,
        messages=messages,
        segments=segments,
        target_message=target_message,
        target_segment_id=target_segment_id,
        target_topic_ids=target_topic_ids,
    )
    facts: list[dict[str, object]] = []
    trace: list[dict[str, object]] = []
    for message, time_relation in candidates:
        fact = _build_objective_moment_fact(message=message, time_relation=time_relation)
        selected = fact is not None and len(facts) < limit
        trace.append(
            {
                "message_id": message.id,
                "sequence_no": message.sequence_no,
                "speaker_role": message.speaker_role,
                "time_relation_to_target": time_relation,
                "selected": selected,
                "skip_reason": None if fact is not None else "not_objective_moment_background",
            }
        )
        if fact is not None and selected:
            facts.append(fact)

    return (
        {
            "source_scope": "original_timeline_near_target_window",
            "use_policy": "background_reference_for_other_private_moment_not_source_disclosure",
            "dialogue_policy": "use_as_situation_background_only_do_not_quote_or_explain_source",
            "facts": facts,
        },
        trace,
        _build_budget(limit=limit, candidate_count=len(candidates), selected_count=len(facts)),
    )


def _objective_moment_candidate_messages(
    *,
    session,
    messages: list[Message],
    segments: list[Segment],
    target_message: Message,
    target_segment_id: int | None,
    target_topic_ids: set[int],
) -> list[tuple[Message, str]]:
    message_lookup = {int(message.id): message for message in messages}
    target_position = _message_model_sort_key(target_message)
    target_segment = next((segment for segment in segments if int(segment.id) == target_segment_id), None)
    candidates: list[tuple[Message, str]] = []
    if target_segment is not None:
        for message in _messages_from_segment(segment=target_segment, message_lookup=message_lookup):
            if _message_model_sort_key(message) <= target_position:
                continue
            if not _is_within_objective_moment_window(target_message=target_message, message=message):
                continue
            candidates.append((message, "immediate_after_target_same_segment"))
            if len(candidates) >= OBJECTIVE_MOMENT_WINDOW_MESSAGES:
                return candidates
    if candidates:
        return candidates

    next_segment = _next_objective_moment_segment(
        session=session,
        segments=segments,
        target_message=target_message,
        target_segment_id=target_segment_id,
        target_topic_ids=target_topic_ids,
    )
    if next_segment is None:
        return []
    for message in _messages_from_segment(segment=next_segment, message_lookup=message_lookup):
        if _message_model_sort_key(message) <= target_position:
            continue
        if not _is_within_objective_moment_window(target_message=target_message, message=message):
            continue
        candidates.append((message, "nearby_after_target_same_topic_segment"))
        if len(candidates) >= OBJECTIVE_MOMENT_WINDOW_MESSAGES:
            break
    return candidates


def _messages_from_segment(*, segment: Segment, message_lookup: dict[int, Message]) -> list[Message]:
    return sorted(
        [message_lookup[message_id] for message_id in (segment.source_message_ids or []) if message_id in message_lookup],
        key=_message_model_sort_key,
    )


def _next_objective_moment_segment(
    *,
    session,
    segments: list[Segment],
    target_message: Message,
    target_segment_id: int | None,
    target_topic_ids: set[int],
) -> Segment | None:
    if target_segment_id is None or not target_topic_ids:
        return None
    ordered_segments = sorted(segments, key=lambda item: (str(item.start_time), int(item.id)))
    target_index = next((index for index, segment in enumerate(ordered_segments) if int(segment.id) == target_segment_id), None)
    if target_index is None or target_index + 1 >= len(ordered_segments):
        return None
    candidate = ordered_segments[target_index + 1]
    if not _timestamp_within_minutes(
        start=target_message.timestamp,
        end=candidate.start_time,
        max_minutes=OBJECTIVE_MOMENT_WINDOW_MINUTES,
    ):
        return None
    overlap_topic_id = (
        session.execute(
            select(TopicLink.topic_id).where(
                TopicLink.segment_id == candidate.id,
                TopicLink.topic_id.in_(target_topic_ids),
            )
        )
        .scalars()
        .first()
    )
    return candidate if overlap_topic_id is not None else None


def _build_objective_moment_fact(*, message: Message, time_relation: str) -> dict[str, object] | None:
    if message.speaker_role != "other" or not _is_style_eligible_message(message):
        return None
    text = _style_text(message)
    fact_kind = _classify_objective_moment_fact(text)
    if fact_kind is None:
        return None
    fact_text = _objective_moment_fact_text(text=text, fact_kind=fact_kind)
    if fact_text is None:
        return None
    return {
        "fact_kind": fact_kind,
        "speaker_role": "other",
        "fact_text": fact_text,
        "confidence": "medium" if fact_kind == "other_current_mental_focus" else "high",
        "supporting_message_ids": [message.id],
        "supporting_sequence_nos": [message.sequence_no],
        "time_relation_to_target": time_relation,
        "dialogue_use_policy": "background_only_do_not_quote_or_explain_source",
    }


def _classify_objective_moment_fact(text: str) -> str | None:
    compact = text.strip()
    if not compact or len(compact) > 48:
        return None
    if any(mark in compact for mark in ("?", "？")):
        return None
    if any(signal in compact for signal in FUTURE_OUTCOME_SIGNALS):
        return None
    if compact.startswith(ACTIVITY_STARTERS) or any(signal in compact for signal in ("动漫", "作业", "游戏", "番", "视频")):
        return "other_current_activity"
    if any(signal in compact for signal in MENTAL_STATE_SIGNALS):
        return "other_current_mental_focus"
    return None


def _objective_moment_fact_text(*, text: str, fact_kind: str) -> str | None:
    normalized = text.strip()
    normalized = normalized.removeprefix("我").strip()
    if not normalized:
        return None
    if fact_kind == "other_current_activity":
        if normalized.startswith("在"):
            return f"other 此刻{normalized}"
        return f"other 此刻正在{normalized}"
    if fact_kind == "other_current_mental_focus":
        return f"other 此刻的注意力或情绪背景：{normalized}"
    return None


def _is_within_objective_moment_window(*, target_message: Message, message: Message) -> bool:
    return _timestamp_within_minutes(
        start=target_message.timestamp,
        end=message.timestamp,
        max_minutes=OBJECTIVE_MOMENT_WINDOW_MINUTES,
    )


def _timestamp_within_minutes(*, start: object, end: object, max_minutes: int) -> bool:
    start_time = _parse_timestamp(start)
    end_time = _parse_timestamp(end)
    if start_time is None or end_time is None:
        return False
    delta_seconds = (end_time - start_time).total_seconds()
    return 0 <= delta_seconds <= max_minutes * 60


def _parse_timestamp(value: object) -> datetime | None:
    try:
        return datetime.fromisoformat(str(value))
    except ValueError:
        return None


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


def _build_role_style_profiles(
    *,
    messages: list[Message],
    target_message: Message,
    snapshot: RelationshipSnapshot | None,
) -> dict[str, dict[str, object]]:
    cutoff_key = _message_model_sort_key(target_message)
    cutoff_safe_messages = [
        message
        for message in sorted(messages, key=_message_model_sort_key)
        if _message_model_sort_key(message) < cutoff_key and _is_style_eligible_message(message)
    ]
    recent_window_messages = cutoff_safe_messages[-RECENT_INTERACTION_WINDOW_MESSAGES:]
    return {
        "self": _build_role_style_profile(
            role="self",
            cutoff_safe_messages=cutoff_safe_messages,
            recent_window_messages=recent_window_messages,
            snapshot=snapshot,
        ),
        "other": _build_role_style_profile(
            role="other",
            cutoff_safe_messages=cutoff_safe_messages,
            recent_window_messages=recent_window_messages,
            snapshot=snapshot,
        ),
    }


def _build_role_style_profile(
    *,
    role: str,
    cutoff_safe_messages: list[Message],
    recent_window_messages: list[Message],
    snapshot: RelationshipSnapshot | None,
) -> dict[str, object]:
    global_role_messages = [message for message in cutoff_safe_messages if message.speaker_role == role]
    recent_role_messages = [message for message in recent_window_messages if message.speaker_role == role]
    if not recent_role_messages:
        recent_role_messages = global_role_messages[-RECENT_ROLE_STYLE_SAMPLE_SIZE:]

    global_style = _summarize_style_window(global_role_messages)
    current_relationship_style = _summarize_style_window(recent_role_messages)
    global_reply_pattern = _summarize_reply_pattern(messages=cutoff_safe_messages, role=role)
    recent_reply_pattern = _summarize_reply_pattern(
        messages=recent_window_messages or cutoff_safe_messages[-RECENT_INTERACTION_WINDOW_MESSAGES:],
        role=role,
    )
    reply_envelope = _build_reply_envelope(
        global_style=global_style,
        current_relationship_style=current_relationship_style,
        global_reply_pattern=global_reply_pattern,
        recent_reply_pattern=recent_reply_pattern,
        snapshot=snapshot,
    )
    return {
        "style_profile_version": "deterministic-style-v1",
        "source_scope": "cutoff_safe_messages_only",
        "global_style": global_style,
        "current_relationship_style": current_relationship_style,
        "reply_pattern": {
            "global_average_run_length": global_reply_pattern["average_run_length"],
            "recent_average_run_length": recent_reply_pattern["average_run_length"],
            "multi_message_run_ratio": recent_reply_pattern["multi_message_run_ratio"],
            "short_burst_ratio": recent_reply_pattern["short_burst_ratio"],
            "max_run_length": recent_reply_pattern["max_run_length"],
            "preferred_bubble_mode": reply_envelope["preferred_bubble_mode"],
        },
        "reply_envelope": reply_envelope,
        "generation_hints": _build_generation_hints(
            global_style=global_style,
            current_relationship_style=current_relationship_style,
            reply_envelope=reply_envelope,
        ),
    }


def _summarize_style_window(messages: list[Message]) -> dict[str, object]:
    texts = [_style_text(message) for message in messages]
    lengths = [len(text) for text in texts if text]
    sample_size = len(lengths)
    question_ratio = _message_ratio(
        sum(1 for text in texts if "?" in text or "？" in text),
        sample_size,
    )
    exclamation_ratio = _message_ratio(
        sum(1 for text in texts if "!" in text or "！" in text),
        sample_size,
    )
    return {
        "sample_size": sample_size,
        "average_chars": _average(lengths),
        "median_chars": _median(lengths),
        "short_message_ratio": _message_ratio(
            sum(1 for length in lengths if length <= SHORT_STYLE_MESSAGE_CHAR_LIMIT),
            sample_size,
        ),
        "long_message_ratio": _message_ratio(
            sum(1 for length in lengths if length >= LONG_STYLE_MESSAGE_CHAR_LIMIT),
            sample_size,
        ),
        "question_ratio": question_ratio,
        "exclamation_ratio": exclamation_ratio,
        "conflict_signal_ratio": _message_ratio(
            sum(1 for text in texts if _text_has_sensitive_signal(text)),
            sample_size,
        ),
        "frequent_particles": _top_message_signals(texts=texts, signals=STYLE_PARTICLES),
        "frequent_punctuation": _top_message_signals(texts=texts, signals=STYLE_PUNCTUATION),
    }


def _summarize_reply_pattern(*, messages: list[Message], role: str) -> dict[str, object]:
    role_runs = _collect_role_runs(messages=messages, role=role)
    if not role_runs:
        return {
            "average_run_length": 0.0,
            "multi_message_run_ratio": 0.0,
            "short_burst_ratio": 0.0,
            "max_run_length": 0,
        }

    run_lengths = [len(run) for run in role_runs]
    short_burst_count = 0
    for run in role_runs:
        if len(run) < 2:
            continue
        if all(len(_style_text(message)) <= SHORT_STYLE_MESSAGE_CHAR_LIMIT for message in run):
            short_burst_count += 1
    return {
        "average_run_length": _average(run_lengths),
        "multi_message_run_ratio": _message_ratio(
            sum(1 for length in run_lengths if length >= 2),
            len(role_runs),
        ),
        "short_burst_ratio": _message_ratio(short_burst_count, len(role_runs)),
        "max_run_length": max(run_lengths),
    }


def _build_reply_envelope(
    *,
    global_style: dict[str, object],
    current_relationship_style: dict[str, object],
    global_reply_pattern: dict[str, object],
    recent_reply_pattern: dict[str, object],
    snapshot: RelationshipSnapshot | None,
) -> dict[str, object]:
    recent_sample_size = int(current_relationship_style["sample_size"])
    median_chars = int(current_relationship_style["median_chars"] or global_style["median_chars"] or 0)
    short_ratio = float(
        current_relationship_style["short_message_ratio"]
        if recent_sample_size > 0
        else global_style["short_message_ratio"]
    )
    if recent_sample_size == 0 and int(global_style["sample_size"]) == 0:
        length_style = "medium"
        max_chars = 24
    elif median_chars <= SHORT_STYLE_MESSAGE_CHAR_LIMIT or short_ratio >= 0.6:
        length_style = "short"
        max_chars = max(18, min(28, median_chars + 10 if median_chars > 0 else 18))
    elif median_chars <= 24:
        length_style = "medium"
        max_chars = max(28, min(52, median_chars + 16 if median_chars > 0 else 36))
    else:
        length_style = "long"
        max_chars = max(40, min(88, median_chars + 20 if median_chars > 0 else 56))

    short_burst_ratio = max(
        float(recent_reply_pattern["short_burst_ratio"]),
        float(global_reply_pattern["short_burst_ratio"]),
    )
    multi_message_run_ratio = max(
        float(recent_reply_pattern["multi_message_run_ratio"]),
        float(global_reply_pattern["multi_message_run_ratio"]),
    )
    max_run_length = max(
        int(recent_reply_pattern["max_run_length"]),
        int(global_reply_pattern["max_run_length"]),
    )
    if short_burst_ratio >= 0.34 or (multi_message_run_ratio >= 0.4 and max_run_length >= 2):
        preferred_bubble_mode = "double_short"
        max_bubble_count = 2
    else:
        preferred_bubble_mode = "single"
        max_bubble_count = 1

    question_ratio = float(
        current_relationship_style["question_ratio"]
        if recent_sample_size > 0
        else global_style["question_ratio"]
    )
    if question_ratio >= 0.45:
        question_tendency = "high"
    elif question_ratio >= 0.2:
        question_tendency = "medium"
    else:
        question_tendency = "low"

    return {
        "length_style": length_style,
        "max_chars": max_chars,
        "max_bubble_count": max_bubble_count,
        "max_clauses": max_bubble_count,
        "preferred_bubble_mode": preferred_bubble_mode,
        "question_tendency": question_tendency,
        "pressure_expression_cap": _resolve_pressure_expression_cap(
            global_style=global_style,
            current_relationship_style=current_relationship_style,
            snapshot=snapshot,
        ),
    }


def _resolve_pressure_expression_cap(
    *,
    global_style: dict[str, object],
    current_relationship_style: dict[str, object],
    snapshot: RelationshipSnapshot | None,
) -> str:
    conflict_signal_ratio = max(
        float(global_style["conflict_signal_ratio"]),
        float(current_relationship_style["conflict_signal_ratio"]),
    )
    tension_rank = _state_intensity_rank(snapshot.tension_level if snapshot is not None else None)
    defensiveness_rank = _state_intensity_rank(snapshot.defensiveness_level if snapshot is not None else None)
    has_active_sensitive_topics = bool(snapshot and snapshot.unresolved_conflict_flags)

    if tension_rank >= 2 or defensiveness_rank >= 2 or conflict_signal_ratio >= 0.4:
        return "guarded_brief"
    if tension_rank >= 1 or defensiveness_rank >= 1 or has_active_sensitive_topics or conflict_signal_ratio >= 0.2:
        return "soft_but_limited"
    return "natural_but_not_expansive"


def _build_generation_hints(
    *,
    global_style: dict[str, object],
    current_relationship_style: dict[str, object],
    reply_envelope: dict[str, object],
) -> list[str]:
    hints = [
        _build_length_hint(reply_envelope=reply_envelope),
        _build_bubble_hint(reply_envelope=reply_envelope),
    ]
    particles = list(current_relationship_style["frequent_particles"]) or list(global_style["frequent_particles"])
    if particles:
        hints.append(f"常见语气词可参考：{'、'.join(particles)}。")

    punctuation = list(current_relationship_style["frequent_punctuation"]) or list(global_style["frequent_punctuation"])
    if punctuation:
        hints.append(f"常见标点倾向可参考：{' '.join(punctuation)}。")

    hints.append(_build_pressure_hint(reply_envelope=reply_envelope))
    if reply_envelope["question_tendency"] == "low":
        hints.append("没有明显需要确认时，不要连续追问或堆叠多个问题。")
    elif reply_envelope["question_tendency"] == "high":
        hints.append("可以保留轻问一句的习惯，但仍受长度上限和当前关系强度约束。")
    return hints


def _build_length_hint(*, reply_envelope: dict[str, object]) -> str:
    max_chars = int(reply_envelope["max_chars"])
    length_style = str(reply_envelope["length_style"])
    if length_style == "short":
        return f"优先用偏短句回复，单条尽量不超过{max_chars}字，避免长篇解释或心理分析。"
    if length_style == "medium":
        return f"优先保持中短句节奏，单条尽量不超过{max_chars}字，不要展开成整段长文。"
    return f"即使允许相对完整，也尽量控制在{max_chars}字以内，保持口语化而不是长篇总结。"


def _build_bubble_hint(*, reply_envelope: dict[str, object]) -> str:
    max_bubble_count = int(reply_envelope["max_bubble_count"])
    if max_bubble_count <= 1:
        return "默认单泡回复，不要拆成连续多条。"
    return f"若需要拆泡，最多拆成{max_bubble_count}条短泡，每条保持短句，不要无限拆分。"


def _build_pressure_hint(*, reply_envelope: dict[str, object]) -> str:
    pressure_cap = str(reply_envelope["pressure_expression_cap"])
    if pressure_cap == "guarded_brief":
        return "有压力时优先简短确认、轻接或保留，不要突然长篇解释、深入复盘或高强度安抚。"
    if pressure_cap == "soft_but_limited":
        return "有压力时可以软化语气，但只做有限承接，不要一下展开很多。"
    return "即使气氛较稳，也保持原本节奏，不要突然比平时更会说或更深。"


def _collect_role_runs(*, messages: list[Message], role: str) -> list[list[Message]]:
    runs: list[list[Message]] = []
    current_run: list[Message] = []
    for message in messages:
        if message.speaker_role == role:
            current_run.append(message)
            continue
        if current_run:
            runs.append(current_run)
            current_run = []
    if current_run:
        runs.append(current_run)
    return runs


def _top_message_signals(*, texts: list[str], signals: tuple[str, ...]) -> list[str]:
    counts: list[tuple[int, str]] = []
    lowered_texts = [text.casefold() for text in texts if text]
    for signal in signals:
        hit_count = sum(1 for text in lowered_texts if signal.casefold() in text)
        if hit_count > 0:
            counts.append((hit_count, signal))
    counts.sort(key=lambda item: (-item[0], item[1]))
    return [signal for _count, signal in counts[:MAX_STYLE_SIGNAL_ITEMS]]


def _is_style_eligible_message(message: Message) -> bool:
    if message.message_type != "text":
        return False
    text = _style_text(message)
    if not text:
        return False
    return PLACEHOLDER_MESSAGE_PATTERN.fullmatch(text) is None


def _style_text(message: Message) -> str:
    return str(message.content_text or "").strip()


def _message_model_sort_key(message: Message) -> tuple[str, int, int]:
    return (str(message.timestamp), int(message.sequence_no), int(message.id))


def _text_has_sensitive_signal(text: str) -> bool:
    haystack = text.casefold()
    return any(keyword.casefold() in haystack for keyword in SENSITIVE_KEYWORDS)


def _average(values: list[int]) -> float:
    if not values:
        return 0.0
    return round(sum(values) / len(values), 2)


def _median(values: list[int]) -> int:
    if not values:
        return 0
    ordered = sorted(values)
    midpoint = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return int(ordered[midpoint])
    return int(round((ordered[midpoint - 1] + ordered[midpoint]) / 2))


def _message_ratio(numerator: int, denominator: int) -> float:
    if denominator <= 0:
        return 0.0
    return round(numerator / denominator, 2)


def _state_intensity_rank(value: object) -> int:
    normalized = str(value or "").casefold()
    if not normalized:
        return 0
    if "high" in normalized or normalized in {"高", "偏高"}:
        return 2
    if "medium" in normalized or normalized in {"中", "中等"}:
        return 1
    return 0
