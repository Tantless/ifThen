from __future__ import annotations

from typing import Any


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
    base_relationship_snapshot: dict[str, Any] | None,
    persona_self: dict[str, Any] | None,
    persona_other: dict[str, Any] | None,
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
        "moment_state_estimate": moment_state_estimate,
        "persona_self": persona_self,
        "persona_other": persona_other,
        "retrieval_warnings": retrieval_warnings,
        "strategy_version": "cutoff-safe-rules-v1",
    }
