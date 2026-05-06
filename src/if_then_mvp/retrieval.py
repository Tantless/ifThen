from __future__ import annotations

from typing import Any

DEFAULT_RELATED_TOPIC_DIGEST_LIMIT = 3
DEFAULT_FUTURE_EVIDENCE_DIGEST_LIMIT = 3
DEFAULT_SAME_DAY_PRIOR_SEGMENT_LIMIT = 1
DEFAULT_OBJECTIVE_MOMENT_FACT_LIMIT = 3


def _message_position(message: dict[str, Any]) -> tuple[str, int]:
    return str(message["timestamp"]), int(message["sequence_no"])


def _segment_cutoff_position(
    segment: dict[str, Any],
    message_lookup: dict[int, dict[str, Any]],
) -> tuple[str, int] | None:
    source_message_ids = segment.get("source_message_ids") or []
    positions = [_message_position(message_lookup[message_id]) for message_id in source_message_ids if message_id in message_lookup]
    if not positions:
        return None
    return max(positions)


def _sort_messages(message_ids: list[int], message_lookup: dict[int, dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        (message_lookup[message_id] for message_id in message_ids if message_id in message_lookup),
        key=_message_position,
    )


def _build_segment_digest(
    segment: dict[str, Any],
    message_ids: list[int],
    message_lookup: dict[int, dict[str, Any]],
) -> dict[str, Any]:
    ordered_messages = _sort_messages(message_ids, message_lookup)
    preview_parts = [
        f"{message['speaker_role']}: {message['content_text']}"
        for message in ordered_messages[:2]
    ]
    return {
        "segment_id": segment["id"],
        "start_time": segment["start_time"],
        "end_time": segment["end_time"],
        "message_count": len(ordered_messages),
        "last_speaker_role": ordered_messages[-1]["speaker_role"] if ordered_messages else None,
        "summary_hint": " | ".join(preview_parts),
    }


def build_context_pack(
    *,
    messages: list[dict[str, Any]],
    segments: list[dict[str, Any]],
    target_message_id: int,
    replacement_content: str,
    related_topic_digests: list[dict[str, Any]],
    future_evidence_digests: list[dict[str, Any]],
    base_relationship_snapshot: dict[str, Any] | None,
    persona_self: dict[str, Any] | None,
    persona_other: dict[str, Any] | None,
    objective_moment_facts: dict[str, Any] | None = None,
    retrieval_trace: dict[str, Any] | None = None,
    retrieval_budget: dict[str, Any] | None = None,
) -> dict[str, Any]:
    message_lookup = {int(message["id"]): message for message in messages}
    target = message_lookup.get(target_message_id)
    if target is None:
        raise ValueError(f"Target message {target_message_id} was not found")

    target_position = _message_position(target)
    target_segment = next(
        (segment for segment in segments if target_message_id in (segment.get("source_message_ids") or [])),
        None,
    )
    if target_segment is None:
        raise ValueError(f"Target message {target_message_id} is not covered by any segment")

    current_segment_history = _sort_messages(
        [
            message_id
            for message_id in (target_segment.get("source_message_ids") or [])
            if message_id in message_lookup and _message_position(message_lookup[message_id]) < target_position
        ],
        message_lookup,
    )

    current_segment_brief = {
        "message_count": len(current_segment_history),
        "last_speaker_role": current_segment_history[-1]["speaker_role"] if current_segment_history else None,
    }

    target_day = str(target["timestamp"]).split("T", 1)[0]
    ordered_segments = [
        (segment, _segment_cutoff_position(segment, message_lookup))
        for segment in segments
    ]
    ordered_segments = [
        (segment, position)
        for segment, position in ordered_segments
        if position is not None
    ]
    ordered_segments.sort(key=lambda item: item[1])

    target_segment_index = next(
        (
            index
            for index, (segment, _position) in enumerate(ordered_segments)
            if segment.get("id") == target_segment.get("id")
        ),
        None,
    )
    same_day_prior_segments = []
    if target_segment_index is not None and target_segment_index > 0:
        prior_segment, prior_position = ordered_segments[target_segment_index - 1]
        prior_day = str(prior_segment.get("start_time") or prior_position[0]).split("T", 1)[0]
        if prior_day == target_day and prior_position < target_position:
            eligible_message_ids = [
                message_id
                for message_id in (prior_segment.get("source_message_ids") or [])
                if message_id in message_lookup and _message_position(message_lookup[message_id]) < target_position
            ]
            if eligible_message_ids:
                same_day_prior_segments.append(
                    _build_segment_digest(prior_segment, eligible_message_ids, message_lookup)
                )

    snapshot = base_relationship_snapshot or {}
    moment_state_estimate = {
        "relationship_temperature": snapshot.get("relationship_temperature", "unknown"),
        "tension_level": snapshot.get("tension_level", "unknown"),
        "openness_level": snapshot.get("openness_level", "unknown"),
        "initiative_balance": snapshot.get("initiative_balance", "unknown"),
        "defensiveness_level": snapshot.get("defensiveness_level", "unknown"),
        "relationship_phase": snapshot.get("relationship_phase", "unknown"),
        "active_sensitive_topics": snapshot.get("active_sensitive_topics", []),
        "state_rationale": "Derived from the latest cutoff-safe relationship snapshot and current segment history.",
    }

    retrieval_warnings = []
    if not related_topic_digests:
        retrieval_warnings.append("related_topic_digests_empty")
    if base_relationship_snapshot is None:
        retrieval_warnings.append("base_relationship_snapshot_missing")
    if not future_evidence_digests:
        retrieval_warnings.append("future_evidence_digests_empty")

    cutoff_safe_facts = {
        "current_segment_history": current_segment_history,
        "current_segment_brief": current_segment_brief,
        "same_day_prior_segments": same_day_prior_segments,
        "related_topic_digests": related_topic_digests,
        "base_relationship_snapshot": base_relationship_snapshot,
    }
    evidence_policy = {
        "cutoff_safe_facts": "character_known",
        "future_evidence_digests": "modeler_only_not_character_known",
        "objective_moment_facts": "background_reference_for_other_private_moment_not_dialogue_source",
        "branch_facts": "branch_only_generated_facts",
    }
    resolved_objective_moment_facts = objective_moment_facts or {
        "source_scope": "original_timeline_near_target_window",
        "use_policy": "background_reference_for_other_private_moment_not_source_disclosure",
        "dialogue_policy": "use_as_situation_background_only_do_not_quote_or_explain_source",
        "facts": [],
    }
    branch_facts = {
        "rewrite_target": {
            "target_message_id": target_message_id,
            "replacement_content": replacement_content,
        },
        "generated_branch_messages": [],
    }
    resolved_retrieval_trace = {
        "related_topic_digests": [],
        "future_evidence_digests": [],
        "objective_moment_facts": [],
    }
    if retrieval_trace:
        for key, value in retrieval_trace.items():
            resolved_retrieval_trace[key] = value

    resolved_retrieval_budget = {
        "current_segment_history": {
            "policy": "preserve_all",
            "selected_count": len(current_segment_history),
        },
        "same_day_prior_segments": {
            "limit": DEFAULT_SAME_DAY_PRIOR_SEGMENT_LIMIT,
            "selected_count": len(same_day_prior_segments),
            "overflow_count": max(0, len(same_day_prior_segments) - DEFAULT_SAME_DAY_PRIOR_SEGMENT_LIMIT),
        },
        "related_topic_digests": {
            "limit": DEFAULT_RELATED_TOPIC_DIGEST_LIMIT,
            "candidate_count": len(related_topic_digests),
            "selected_count": len(related_topic_digests),
            "overflow_count": 0,
        },
        "future_evidence_digests": {
            "limit": DEFAULT_FUTURE_EVIDENCE_DIGEST_LIMIT,
            "candidate_count": len(future_evidence_digests),
            "selected_count": len(future_evidence_digests),
            "overflow_count": 0,
        },
        "objective_moment_facts": {
            "limit": DEFAULT_OBJECTIVE_MOMENT_FACT_LIMIT,
            "candidate_count": len(resolved_objective_moment_facts.get("facts") or []),
            "selected_count": len(resolved_objective_moment_facts.get("facts") or []),
            "overflow_count": 0,
        },
    }
    if retrieval_budget:
        for key, value in retrieval_budget.items():
            if isinstance(value, dict) and isinstance(resolved_retrieval_budget.get(key), dict):
                merged_value = dict(resolved_retrieval_budget[key])
                merged_value.update(value)
                resolved_retrieval_budget[key] = merged_value
            else:
                resolved_retrieval_budget[key] = value

    return {
        "conversation_id": target["conversation_id"],
        "target_message_id": target_message_id,
        "cutoff_timestamp": target["timestamp"],
        "cutoff_sequence_no": target["sequence_no"],
        "original_message_text": target["content_text"],
        "replacement_content": replacement_content,
        "current_segment_history": current_segment_history,
        "current_segment_brief": current_segment_brief,
        "same_day_prior_segments": same_day_prior_segments,
        "related_topic_digests": related_topic_digests,
        "base_relationship_snapshot": base_relationship_snapshot,
        "cutoff_safe_facts": cutoff_safe_facts,
        "future_evidence_digests": future_evidence_digests,
        "objective_moment_facts": resolved_objective_moment_facts,
        "branch_facts": branch_facts,
        "evidence_policy": evidence_policy,
        "moment_state_estimate": moment_state_estimate,
        "persona_self": persona_self,
        "persona_other": persona_other,
        "retrieval_trace": resolved_retrieval_trace,
        "retrieval_budget": resolved_retrieval_budget,
        "retrieval_warnings": retrieval_warnings,
        "strategy_version": "layered-evidence-v1",
    }
