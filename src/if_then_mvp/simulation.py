from __future__ import annotations

from typing import Any


def assess_branch(context_pack: dict[str, Any]) -> dict[str, Any]:
    original_text = str(context_pack.get("original_message_text", ""))
    replacement_text = str(context_pack.get("replacement_content", ""))
    original_length = len(original_text)
    replacement_length = len(replacement_text)
    gentler = any(token in replacement_text for token in ("慢慢", "方便", "晚点", "也可以", "就好"))

    if gentler:
        branch_direction = "closer"
        shift_summary = "新说法更柔和，降低了推进压力，让对方更容易顺势接话。"
        feeling = "更放松"
        reply_strategy = "light_follow_up"
    elif replacement_length < original_length:
        branch_direction = "steady"
        shift_summary = "新说法更短，整体保持轻松，但没有明显拉近或推远关系。"
        feeling = "平稳"
        reply_strategy = "brief_acknowledgement"
    else:
        branch_direction = "guarded"
        shift_summary = "新说法信息量更重一些，对方大概率会先用保守方式接住。"
        feeling = "稍微谨慎"
        reply_strategy = "guarded_reply"

    return {
        "branch_direction": branch_direction,
        "state_shift_summary": shift_summary,
        "other_immediate_feeling": feeling,
        "reply_strategy": reply_strategy,
        "risk_flags": [],
        "confidence": 0.72 if gentler else 0.64,
    }


def generate_first_reply(context_pack: dict[str, Any], assessment: dict[str, Any]) -> tuple[str, str]:
    persona_other = context_pack.get("persona_other") or {}
    other_summary = str(persona_other.get("global_persona_summary", ""))
    replacement_text = str(context_pack.get("replacement_content", ""))

    if assessment["branch_direction"] == "closer":
        if "轻松" in other_summary:
            return (
                "好呀，那我们就慢慢聊，别着急。",
                "沿用对方偏轻松的表达风格，用简短安稳的回应接住新的语气。",
            )
        return (
            "可以，我们慢慢聊就好。",
            "保持低压力和顺势回应，让分支继续朝放松方向发展。",
        )
    if assessment["reply_strategy"] == "brief_acknowledgement":
        return (
            "嗯，收到，那就先这样。",
            "维持简短确认式回应，不额外扩张话题。",
        )
    return (
        f"嗯，我看到了。{replacement_text[:10]}",
        "在不确定时采用保守回复，避免过度延展。",
    )


def simulate_short_thread(
    context_pack: dict[str, Any],
    assessment: dict[str, Any],
    turn_count: int,
) -> list[dict[str, Any]]:
    if turn_count <= 0:
        return []

    turns: list[dict[str, Any]] = []
    base_state = context_pack.get("moment_state_estimate") or {}
    state = {
        "relationship_temperature": base_state.get("relationship_temperature", "unknown"),
        "tension_level": base_state.get("tension_level", "unknown"),
        "openness_level": base_state.get("openness_level", "unknown"),
    }

    for index in range(1, turn_count + 1):
        speaker_role = "other" if index % 2 == 1 else "self"
        if speaker_role == "other":
            message_text = "嗯，这样聊会舒服一点。" if assessment["branch_direction"] == "closer" else "嗯，我先接一下这个话题。"
            strategy_used = assessment["reply_strategy"]
            if assessment["branch_direction"] == "closer":
                state["openness_level"] = "high"
        else:
            message_text = "好，那我们就顺着慢慢说。" if assessment["branch_direction"] == "closer" else "行，我接着补充一下。"
            strategy_used = "self_follow_up"

        turns.append(
            {
                "turn_index": index,
                "speaker_role": speaker_role,
                "message_text": message_text,
                "strategy_used": strategy_used,
                "state_after_turn": dict(state),
                "generation_notes": "Deterministic early-MVP progression for endpoint verification.",
            }
        )

    return turns
