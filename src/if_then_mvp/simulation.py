from __future__ import annotations

import json
import re
from typing import Any

from pydantic import BaseModel, Field

from if_then_mvp.llm import ChatJSONClient


class TurnStatePayload(BaseModel):
    relationship_temperature: str
    tension_level: str
    openness_level: str
    initiative_balance: str
    defensiveness_level: str
    relationship_phase: str
    active_sensitive_topics: list[str] = Field(default_factory=list)
    state_rationale: str


class BranchAssessmentPayload(BaseModel):
    branch_direction: str
    state_shift_summary: str
    other_immediate_feeling: str
    reply_strategy: str
    risk_flags: list[str] = Field(default_factory=list)
    modeler_only_risk_sources: list[str] = Field(
        default_factory=list,
        description=(
            "Modeler-only future evidence signals that made the assessment more conservative; "
            "these must never be treated as character-known facts or quoted in generated dialogue."
        ),
    )
    leakage_boundary_notes: str = Field(
        default="",
        description=(
            "Brief note separating character-known cutoff-safe facts, modeler-only future evidence, "
            "and branch-only facts for downstream reply generation."
        ),
    )
    confidence: float


class FirstReplyPayload(BaseModel):
    first_reply_text: str
    strategy_used: str
    first_reply_style_notes: str
    state_after_turn: TurnStatePayload


class NextTurnPayload(BaseModel):
    message_text: str
    strategy_used: str
    state_after_turn: TurnStatePayload
    generation_notes: str
    should_stop: bool = False
    stopping_reason: str | None = None


class BranchReplyPayload(BaseModel):
    message_text: str
    strategy_used: str
    state_after_turn: TurnStatePayload
    generation_notes: str


BRANCH_SYSTEM_PROMPT = (
    "你是一个“截止安全”的反事实分支状态判断器。"
    "你的任务不是直接生成回复文本，而是判断：把原消息改写成新消息后，"
    "对方会如何即时理解，这会让关系状态朝哪个方向发生多大幅度的变化，以及对方首轮最可能采取什么回应策略。"
    "你必须遵守以下规则："
    "1. 只能依据当前提供的分层证据进行判断：cutoff-safe facts 是角色当时可知事实，future evidence 只是 modeler-only 证据，branch facts 只来自当前反事实分支。"
    "2. 可以用 future evidence 调整风险、置信度和保守程度，但绝对不能把它写成角色已知事实，也不能生成具体回复文本。"
    "3. 你的核心任务是判断“改写相对原话改变了什么”，而不是孤立评价新话本身。"
    "4. 变化幅度必须保守；更柔和、更体面、更容易接住，不等于关系就会明显转向。"
    "5. 先比较原话和改写分别触发了什么，再判断状态变化。"
    "6. other_immediate_feeling、reply_strategy、risk_flags 各自职责不同，不能互相重复或混淆。"
    "7. reply_strategy 只描述对方最可能采取的回应方式，不要越界生成具体回复文本。"
    "8. risk_flags 必须保留仍未消失的风险，不要因为改写更好一点就把所有风险抹平。"
    "9. modeler_only_risk_sources 只能记录让判断更保守的未来证据信号，不能写成对方当时知道或说过。"
    "10. 如果证据不足，必须选择更克制、更有限的状态变化判断，而不是戏剧化乐观推演。"
    "11. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
)

FIRST_REPLY_SYSTEM_PROMPT = (
    "你是一个“截止安全”的反事实首轮回复生成器。"
    "你的任务不是评估分支，而是基于已经给定的 BranchAssessment、当前关系状态、对方 persona、相关话题和当前分支对话记录，"
    "生成“对方在这条反事实分支里的第一条回复”。"
    "你必须遵守以下规则："
    "1. 只能依据当前提供的 BranchAssessment、当前关系状态、对方 persona、cutoff-safe 话题摘要和当前分支对话记录进行生成。"
    "2. future evidence 若出现，只是 modeler-only 约束，只能让表达更保守、更有限，绝对不能被引用、复述或暗示成对方当时知道的内容。"
    "3. 你生成的是“首轮回复”，不是整段对话，不要抢跑到后续多轮发展。"
    "4. 回复必须符合对方 persona、当前关系状态和 BranchAssessment 指定的 reply_strategy，而不是单纯把改写内容顺着说得更好听。"
    "5. 回复应优先追求真实、克制、符合当下关系允许的表达强度，而不是追求戏剧性、理想化或过度治愈。"
    "6. 如果当前关系的 openness 有限、tension 偏高或 defensiveness 仍在，回复可以是有限承接、轻接一下、保留式回应、谨慎确认，而不必强行展开。"
    "7. 若 persona_other.deterministic_style_profile 指定偏短句、单泡或压力下保留边界，必须优先服从，不能写成长篇分析或无限拆泡。"
    "8. 不得说“后来”“我之后说过”“其实我一直喜欢/不喜欢”这类把 cutoff 后事实带进角色台词的话。"
    "9. 避免分析腔、治疗腔、总结腔或过度完整的书面表达。"
    "10. first_reply_text、strategy_used、first_reply_style_notes、state_after_turn 各自职责不同，不能互相重复或混淆。"
    "11. state_after_turn 只估计这条首轮回复之后的即时状态，不要把一次回复夸大成长期关系转折。"
    "12. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
)

NEXT_TURN_SYSTEM_PROMPT = (
    "你是一个“截止安全”的反事实多轮续写器。"
    "你的任务是在已给定的分支判断、当前分支状态和已有 transcript 基础上，"
    "继续生成这条反事实分支中“指定说话者”的下一句消息，并估计这一句之后的即时状态。"
    "你必须遵守以下规则："
    "1. 只能依据当前提供的 BranchAssessment、当前分支状态、指定说话者 persona、cutoff-safe 话题摘要和当前 branch transcript 进行生成。"
    "2. future evidence 若出现，只是 modeler-only 人格稳定和风险约束，不能被写成角色在分支里知道或经历过的事实。"
    "3. 你每次只生成“指定说话者”的下一句消息，不要替对方多说，也不要提前写后续轮次。"
    "4. 生成必须符合当前分支已经形成的节奏、关系状态和 persona，不要突然变得更热、更深、更会说话。"
    "5. 若指定说话者 persona 的 deterministic_style_profile 指定偏短句、单泡或压力下保留边界，必须优先服从。"
    "6. 当前 branch transcript 是分支事实源；不要把原时间线后续事件强行搬进分支。"
    "7. state_after_turn 只估计这一轮之后的即时状态，不要把单轮变化夸大成长期关系反转。"
    "8. should_stop 用于判断这条分支是否应当自然收束；只有在继续说下去明显不自然、只会机械重复或当前轮已形成自然收口时才设为 true。"
    "9. 允许自然变短、自然停住，不以把对话写完整为目标。"
    "10. 你必须主动避免机械重复、原地打转、只换说法复述上一轮、或让双方异常理想化地持续推进。"
    "11. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
)

BRANCH_REPLY_SYSTEM_PROMPT = (
    "你是实时反事实分支会话里的“other 回复生成器”。"
    "用户继续扮演 self，你只能生成 other 在当前分支里的下一条消息。"
    "你必须遵守以下规则："
    "1. 只能生成 other 的一条下一轮回复，绝对不要代写 self。"
    "2. 用户实时输入是事实源；persona_self 只能帮助理解用户风格，不能覆盖、改写或忽略用户刚说的话。"
    "3. persona_other 是主要生成约束，回复长度、语气、回避/承接方式和关系推进上限都必须受它约束。"
    "4. session_memory_pack 中的 cutoff-safe 材料可作为角色当时可知上下文；未来原时间线证据若出现，只能影响风险和保守程度，不能写成 other 已知内容。"
    "5. objective_moment_facts 若出现，只能作为 other 彼时现实处境背景，帮助理解 other 正在做什么、注意力在哪里、情绪底色如何；不能当作台词素材直接复述、引用或解释来源。"
    "6. 当前 branch transcript 和 pending self 输入是分支事实源；不要把原时间线后续事件强行搬进分支。"
    "7. 若 persona_other.deterministic_style_profile 指定偏短句、单泡或压力下保留边界，必须优先服从，不能长篇分析或无限拆泡。"
    "8. 回复必须符合当前 branch transcript 和 current_branch_state，不要突然变得更热、更深、更会沟通。"
    "9. state_after_turn 只估计这条 other 回复之后的即时状态，不要把一次回复夸大成长期关系转折。"
    "10. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
)


def assess_branch(*, llm_client: ChatJSONClient, context_pack: dict[str, Any]) -> dict[str, Any]:
    payload = llm_client.chat_json(
        system_prompt=BRANCH_SYSTEM_PROMPT,
        user_prompt=_build_branch_prompt(context_pack=context_pack),
        response_model=BranchAssessmentPayload,
    )
    return payload.model_dump()


def generate_first_reply(
    *,
    llm_client: ChatJSONClient,
    context_pack: dict[str, Any],
    assessment: dict[str, Any],
) -> FirstReplyPayload:
    return llm_client.chat_json(
        system_prompt=FIRST_REPLY_SYSTEM_PROMPT,
        user_prompt=_build_first_reply_prompt(
            context_pack=context_pack,
            assessment=assessment,
        ),
        response_model=FirstReplyPayload,
    )


def simulate_short_thread(
    *,
    llm_client: ChatJSONClient,
    context_pack: dict[str, Any],
    assessment: dict[str, Any],
    first_reply: FirstReplyPayload,
    turn_count: int,
) -> list[dict[str, Any]]:
    if turn_count <= 0:
        return []

    turns = [
        {
            "turn_index": 1,
            "speaker_role": "other",
            "message_text": first_reply.first_reply_text,
            "strategy_used": first_reply.strategy_used,
            "state_after_turn": first_reply.state_after_turn.model_dump(),
            "generation_notes": first_reply.first_reply_style_notes,
        }
    ]
    if turn_count == 1:
        return turns

    transcript = _build_branch_transcript_seed(context_pack=context_pack)
    transcript.append(
        {
            "speaker_role": "self",
            "message_text": str(context_pack.get("replacement_content", "")),
        }
    )
    transcript.append(
        {
            "speaker_role": "other",
            "message_text": first_reply.first_reply_text,
        }
    )
    state = first_reply.state_after_turn.model_dump()

    for index in range(2, turn_count + 1):
        speaker_role = "self" if index % 2 == 0 else "other"
        next_turn = llm_client.chat_json(
            system_prompt=NEXT_TURN_SYSTEM_PROMPT,
            user_prompt=_build_next_turn_prompt(
                context_pack=context_pack,
                assessment=assessment,
                transcript=transcript,
                current_state=state,
                speaker_role=speaker_role,
            ),
            response_model=NextTurnPayload,
        )
        if not next_turn.message_text.strip():
            break
        if _is_repeated_turn(
            speaker_role=speaker_role,
            message_text=next_turn.message_text,
            transcript=transcript,
        ):
            break

        turns.append(
            {
                "turn_index": index,
                "speaker_role": speaker_role,
                "message_text": next_turn.message_text,
                "strategy_used": next_turn.strategy_used,
                "state_after_turn": next_turn.state_after_turn.model_dump(),
                "generation_notes": next_turn.generation_notes,
            }
        )
        transcript.append(
            {
                "speaker_role": speaker_role,
                "message_text": next_turn.message_text,
            }
        )
        state = next_turn.state_after_turn.model_dump()
        if next_turn.should_stop:
            break

    return turns


def generate_branch_reply(
    *,
    llm_client: ChatJSONClient,
    session_memory_pack: dict[str, Any],
    branch_transcript: list[dict[str, Any]],
    pending_self_messages: list[dict[str, Any]],
    current_branch_state: dict[str, Any],
) -> BranchReplyPayload:
    return llm_client.chat_json(
        system_prompt=BRANCH_REPLY_SYSTEM_PROMPT,
        user_prompt=_build_branch_reply_prompt(
            session_memory_pack=session_memory_pack,
            branch_transcript=branch_transcript,
            pending_self_messages=pending_self_messages,
            current_branch_state=current_branch_state,
        ),
        response_model=BranchReplyPayload,
    )


def _build_branch_prompt(*, context_pack: dict[str, Any]) -> str:
    lines = [
        "请根据下面这次反事实改写请求，判断该分支相对原话的状态变化，并输出结构化 JSON。",
        "",
        "你的目标不是生成回复，而是判断：",
        "- 原话和改写相比，减少了什么风险、增加了什么承接，或触发了什么新的问题",
        "- 对方看到改写后的第一反应更可能是什么",
        "- 对方首轮更可能采取哪种回应策略",
        "- 截至首轮回应之前，这次改写让分支更可能朝哪个方向发生有限变化",
        "",
        "请根据下面规则完成判断，并只输出最终 JSON，不要输出推理过程：",
        "",
        "1. 总体原则",
        "- 你判断的是“改写相对原话造成的变化”，不是单独评价改写句子本身",
        "- 必须结合当前关系状态、对方 persona、当前段前文和相关话题一起判断",
        "- 同一句话在不同关系温度、紧张度、开放度下意义不同，不要脱离上下文做判断",
        "- 默认优先保守：变化可以是略好、略差、略缓和、略收缩，而不是动不动明显变盘",
        "- 如果证据不足，宁可写有限变化，也不要写大转向",
        "- 先比较原话和改写分别触发了什么，再判断状态变化",
        "",
        "2. `branch_direction` 的职责",
        "- 表示这次改写后，这条分支整体更可能朝哪个方向发生有限偏移",
        "- 它回答的是“相比原话，这句改写更可能让局面略微变好、略微变差、基本持平，还是只改善了表面承接度”",
        "- 这个字段应体现方向，但不要夸大幅度",
        "- 如果改写只是降低了伤害、降低了推进压力，但不足以改变关系大盘，也应写成有限正向而不是明显拉近",
        "- 如果改写虽然更体面，但核心敏感点没变，也不要写成明显 closer",
        "",
        "3. `state_shift_summary` 的职责",
        "- 用 2 到 4 句概括：改写相对原话具体改变了什么，以及这种改变为什么会影响对方首轮回应",
        "- 重点写“少了什么风险、多了什么承接、哪些触发点被减弱、哪些风险仍保留”",
        "- 不要只说“更温柔了”“更好了”这种空话",
        "- 不要直接写回复内容",
        "- 应尽量体现这是“即时层面的分支变化”，不是长期关系结论",
        "",
        "4. `other_immediate_feeling` 的职责",
        "- 表示对方看到改写后，第一反应更可能是什么感受",
        "- 例如：更放松一点、更没那么被逼迫、仍然保留、略感被安抚、稍微更愿意接话、仍然有顾虑",
        "- 这里写的是“第一反应感受”",
        "- 不要把它写成回复策略",
        "- 不要把它写成长期关系判断",
        "",
        "5. `reply_strategy` 的职责",
        "- 表示对方首轮最可能采取的回应方式",
        "- 例如：轻接一下、谨慎确认、简短安抚、保留式回应、软性回避、低压力延续、有限试探",
        "- 这里写的是“怎么回”，不是“回什么”",
        "- 不要直接生成具体回复文本",
        "- reply_strategy 应当由 persona、当前关系状态和改写后的即时感受共同决定",
        "",
        "6. `risk_flags` 的职责",
        "- 写出这次改写后仍然没有消失的风险点",
        "- 例如：核心敏感议题仍在、对方仍可能轻接不深聊、关系阶段本身不支持大幅靠近、当前 openness 仍有限、旧 tension 仍未解除",
        "- 如果改写只是减少了风险，而不是解决了问题，risk_flags 应保留这些未消失的问题",
        "- 不要因为改写更柔和就把所有风险清空",
        "- 只有在确实看不到明显残余风险时，才可少写或不写",
        "",
        "7. `confidence` 的职责",
        "- 取 0 到 1 之间",
        "- 若原话与改写差异明确、上下文充分、persona 与当前状态信号一致，则可更高",
        "- 若上下文不足、关系信号矛盾、改写影响非常细微，则应更低",
        "- 不要因为你写得完整就给高 confidence",
        "",
        "7b. `modeler_only_risk_sources` 与 `leakage_boundary_notes` 的职责",
        "- `modeler_only_risk_sources` 只记录来自 modeler-only future evidence 的风险信号，例如长期拒绝、偏好边界、后续防御或关系收缩证据",
        "- 这些风险来源可以让 branch_direction、risk_flags、confidence 更保守，但不能写成 other 在 cutoff 当下知道或说过",
        "- `leakage_boundary_notes` 要简洁说明哪些事实可作为角色已知，哪些只是 modeler-only 约束，哪些只来自当前分支",
        "- 如果没有 future evidence，应保持为空或说明未使用 modeler-only evidence，不要编造未来风险来源",
        "",
        "8. 关键判断提醒",
        "- 更柔和 ≠ 明显 closer",
        "- 更体面 ≠ 风险消失",
        "- 更容易接一句 ≠ 关系明显升温",
        "- 如果只能确认更容易被接一句，不要把它写成关系明显拉近",
        "- 一次改写通常先改变的是“首轮可接性”和“即时防御强度”，不一定改变长期关系走向",
        "- 如果 moment_state 本来 tension 高、openness 低、防御已被激活，那么再好的改写也常常只是“少踩雷”，而不是“明显翻盘”",
        "",
        "9. 边界示例",
        "",
        "示例1：原话偏硬、偏推进；改写后更柔和、更给空间",
        "正确倾向：",
        "- 可以判断对方第一反应压力降低",
        "- 可以判断 reply_strategy 更可能变成“轻接一下”而不是“防御或躲开”",
        "- 但如果当前关系仍紧，不能直接判断关系明显升温",
        "",
        "示例2：改写只是换了更礼貌的说法，但核心敏感问题没有变化",
        "正确倾向：",
        "- state_shift_summary 应写“表面摩擦下降，但核心风险仍在”",
        "- risk_flags 不应被清空",
        "- branch_direction 应保守",
        "",
        "示例3：改写减少了逼问感，使对方更容易接第一句",
        "正确倾向：",
        "- 可以判断 other_immediate_feeling 更放松一些",
        "- reply_strategy 可能从回避变成简短承接",
        "- 但这更多是首轮层面的改善，不等于长期走势已扭转",
        "",
        "示例4：当前关系本来就偏暖，改写又明显更体贴、更会承接当前语境",
        "正确倾向：",
        "- 可以给更明确一点的正向变化",
        "- 但仍应说明这主要是“更容易顺着当前状态继续靠近”，而不是无依据地夸大成重大关系转折",
        "",
        "示例5：改写虽然看起来更好，但和对方 persona 不匹配，或者超出当前关系允许的表达强度",
        "正确倾向：",
        "- 不要只看字面温柔度",
        "- 应考虑对方是否会觉得突兀、负担更大、或仍然选择保留",
        "",
        "10. 输出质量要求",
        "- 尽量写成对后续 first reply 真正有约束力的判断",
        "- 尽量明确“这句改写具体改变了哪一个触发点”",
        "- 尽量避免空泛判断，例如“更好”“更真诚”“更成熟”",
        "- 要体现有限变化幅度，不要过度乐观",
        "",
        "请再次自检：",
        "- 有没有忽视“原话 vs 改写”的差异，只在评价新话本身",
        "- 有没有把略微改善写成明显翻盘",
        "- 有没有把即时感受和回复策略写重复",
        "- 有没有把风险写没了",
        "- 有没有越界开始生成回复内容",
        "- 有没有把首轮可接性变化夸大成长期关系变化",
        "- 有没有把 modeler-only future evidence 写成角色当时已经知道的事实",
        "",
        "推演请求 JSON:",
        _to_json_line(
            {
                "original_message_text": context_pack.get("original_message_text"),
                "replacement_content": context_pack.get("replacement_content"),
                "cutoff_timestamp": context_pack.get("cutoff_timestamp"),
                "cutoff_sequence_no": context_pack.get("cutoff_sequence_no"),
            }
        ),
        "",
        "当前关系状态 JSON:",
        _to_json_line(context_pack.get("moment_state_estimate") or {}),
        "",
        "我方人格画像 JSON:",
        _to_json_line(context_pack.get("persona_self") or {}),
        "",
        "对方人格画像 JSON:",
        _to_json_line(context_pack.get("persona_other") or {}),
        "",
        "证据分层策略 JSON:",
        _to_json_line(context_pack.get("evidence_policy") or {}),
        "",
        "modeler-only future evidence JSONL:",
    ]
    lines.extend(_to_json_line(item) for item in (context_pack.get("future_evidence_digests") or []))
    lines.extend(
        [
            "",
            "branch-only facts JSON:",
            _to_json_line(context_pack.get("branch_facts") or {}),
            "",
            "cutoff-safe related topic digests JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in (context_pack.get("related_topic_digests") or []))
    lines.extend(
        [
            "",
            "同日更早会话段 JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in (context_pack.get("same_day_prior_segments") or []))
    lines.extend(
        [
            "",
            "当前会话段历史前文 JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in (context_pack.get("current_segment_history") or []))
    return "\n".join(lines)


def _build_first_reply_prompt(*, context_pack: dict[str, Any], assessment: dict[str, Any]) -> str:
    transcript = _build_branch_transcript_seed(context_pack=context_pack)
    transcript.append(
        {
            "speaker_role": "self",
            "message_text": context_pack.get("replacement_content"),
        }
    )
    persona_other = context_pack.get("persona_other") or {}
    other_style_profile = _persona_style_profile(persona_other)
    lines = [
        "请根据下面这条反事实分支的状态判断结果，生成对方在该分支里的第一条回复，并输出结构化 JSON。",
        "",
        "你的目标不是生成理想化安慰，也不是把分支写甜，而是生成一条：",
        "- 符合对方 persona 的真实首轮回应",
        "- 符合当前关系状态和 reply_strategy 的表达",
        "- 与这句改写的即时效果相匹配，但不过度夸大变化幅度",
        "",
        "请根据下面规则完成生成，并只输出最终 JSON，不要输出推理过程：",
        "",
        "1. 总体原则",
        "- 这是一条“首轮回复”，只处理对方看到改写后的第一反应表达",
        "- 必须遵守 BranchAssessment 里给出的 `reply_strategy`、`other_immediate_feeling` 和 `state_shift_summary`",
        "- 回复应同时受当前关系状态、对方 persona、当前段前文和相关话题约束",
        "- 默认优先真实、克制、有限，不要把略微改善写成明显靠近",
        "- 如果上下文显示当前关系仍有 tension、openness 有限或 defensiveness 未解除，回复可以只做到“接住一点”，不必强行深入展开",
        "",
        "2. `first_reply_text` 的职责",
        "- 生成对方在这一刻最可能说出的第一条回复",
        "- 回复要像真实聊天里的第一句，而不是总结、分析或后续多轮内容",
        "- 回复长度、语气、直接程度要符合对方 persona 和当前关系允许的强度",
        "- 若 deterministic style profile 指定偏短句、单泡或最多两条短泡，必须按该 envelope 控制长度和拆泡",
        "- 如果对方更可能简短接话，就不要生成过长回复",
        "- 如果对方更可能保留、缓冲、轻接、确认、软回避，就要如实体现，不要强行热情或深情",
        "",
        "3. `strategy_used` 的职责",
        "- 填写这条首轮回复实际采用的回应策略",
        "- 应与 BranchAssessment 中给出的 `reply_strategy` 保持一致，或是其非常接近的具体化落地",
        "- 这里写的是“这句回复采用了什么策略”",
        "- 不要写成对关系的评价",
        "",
        "4. `first_reply_style_notes` 的职责",
        "- 用 1 到 3 句简洁说明：为什么这条回复会采用这种语气、长度和表达方式",
        "- 重点说明它如何受 persona、当前关系状态和 reply_strategy 约束",
        "- 不要复述 reply text 本身",
        "- 不要写成泛泛空话，比如“因为比较自然”“因为更真实”",
        "",
        "5. `state_after_turn` 的职责",
        "- 估计在这条首轮回复之后，关系状态会发生什么即时变化",
        "- 这里写的是“首轮之后的即时状态”，不是长期走势",
        "- 应在当前 moment_state 基础上做有限修正，而不是大幅跳变",
        "- 如果这条回复只是轻接一下，state_after_turn 也应只反映有限变化",
        "- 不要因为回复体面或柔和，就直接把温度、开放度、阶段写成明显大幅改善",
        "",
        "6. 生成边界提醒",
        "- 不要把首轮回复写得比当前关系更亲密",
        "- 不要让对方突然说出和 persona 不匹配的高表达力、高承接力、高自我揭示内容",
        "- 不要把首轮回复写成完整问题解决",
        "- 不要提前生成第二轮、第三轮会发生的事",
        "- 不要为了显得好而去掉仍然存在的保留、顾虑和风险",
        "",
        "6.5. 证据边界与 future evidence 泄漏禁止",
        "- cutoff-safe facts 和当前分支对话记录是角色可知事实，可以影响首轮回复的具体表达",
        "- modeler-only future evidence 只能影响表达强度、风险保守度和是否更有限，不能进入 `first_reply_text`",
        "- 如果 future evidence 显示对方后来明确拒绝、长期不接受某类推进或偏好慢一点，回复应更克制、更有限，但不得透露这些未来证据",
        "- 不得引用、复述或暗示 cutoff 后才发生的拒绝、偏好、解释、关系状态或后续对话",
        "- 不得说“后来”“我之后说过”“我其实一直喜欢/不喜欢”“我后来告诉过你我喜欢……”这类把未来事实包装成角色当下认知的话",
        "",
        "7. 质量要求：回复文本层",
        "- 要像即时发出的聊天消息，而不是分析报告",
        "- 优先自然、口语化、符合该人平时表达密度",
        "- 如果对方通常简短，就简短",
        "- 如果对方通常会先轻接、先确认、先给一点回应，就优先采用这种结构",
        "- 不要过度文学化、过度完整、过度圆满",
        "- 避免分析腔、治疗腔、总结腔或过度完整的书面表达",
        "- 宁可短一点、留一点，也不要假装对方突然很会说",
        "",
        "8. 质量要求：状态层",
        "- `state_after_turn` 要与这条回复的真实力度匹配",
        "- 轻接一下，通常只会带来轻微 openness 改善或 tension 缓和",
        "- 保留式回应，可能只说明没有恶化，但不代表明显升温",
        "- 如果 reply_strategy 偏 guarded / brief / soft_deflection，状态改善也应有限",
        "",
        "9. 边界示例",
        "",
        "示例1：BranchAssessment 判断“改写降低了推进压力，对方更容易接一句，但核心顾虑仍在”",
        "正确倾向：",
        "- first_reply_text 可以是轻接一下或低压力回应",
        "- 不要直接生成明显亲密、明显深入展开的回复",
        "- state_after_turn 应体现有限改善，而不是明显升温",
        "",
        "示例2：当前关系本来 openness 就有限，对方 persona 又偏简短保留",
        "正确倾向：",
        "- 回复可以短、轻、留余地",
        "- 不要为了显得分支变好了，就强行让对方展开很多",
        "",
        "示例3：reply_strategy 是 soft_deflection 或 guarded_acknowledgement",
        "正确倾向：",
        "- first_reply_text 应体现接住一点但不过度推进",
        "- style_notes 应说明这是因为对方仍有保留或防御",
        "- state_after_turn 不应写成明显 closer",
        "",
        "示例4：当前关系偏暖，assessment 也判断这句改写明显更会承接当前语境",
        "正确倾向：",
        "- 可以写更自然、更顺着的首轮回复",
        "- 但仍然要像“真实第一句”，不要一下把后续几轮的情绪承接全说完",
        "",
        "10. 输出质量要求",
        "- `first_reply_text` 要真实可发",
        "- `strategy_used` 要和 assessment 对齐",
        "- `first_reply_style_notes` 要解释语气/长度/克制感来源",
        "- `state_after_turn` 要是有限的即时状态更新",
        "- 四个字段不要换个说法重复同一件事",
        "",
        "请再次自检：",
        "- 有没有把首轮回复写得过于理想化或过于会说话",
        "- 有没有忽视 persona，写出不像这个人的表达",
        "- 有没有忽视当前关系状态，把回复写得太热或太深",
        "- 有没有把 assessment 里的有限改善夸大成明显转向",
        "- 有没有在 first reply 里偷偷写进后续几轮内容",
        "- 有没有把 modeler-only future evidence 写进 `first_reply_text`",
        "- 有没有让 `state_after_turn` 跳变过大",
        "",
        "分支请求 JSON:",
        _to_json_line(
            {
                "original_message_text": context_pack.get("original_message_text"),
                "replacement_content": context_pack.get("replacement_content"),
            }
        ),
        "",
        "分支判断结果 JSON:",
        _to_json_line(assessment),
        "",
        "证据分层策略 JSON:",
        _to_json_line(context_pack.get("evidence_policy") or {}),
        "",
        "modeler-only future evidence JSONL:",
    ]
    lines.extend(_to_json_line(item) for item in (context_pack.get("future_evidence_digests") or []))
    lines.extend(
        [
            "",
            "branch-only facts JSON:",
            _to_json_line(context_pack.get("branch_facts") or {}),
            "",
            "cutoff-safe related topic digests JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in (context_pack.get("related_topic_digests") or []))
    lines.extend(
        [
            "",
            "当前关系状态 JSON:",
            _to_json_line(context_pack.get("moment_state_estimate") or {}),
            "",
            "对方人格画像 JSON:",
            _to_json_line(persona_other),
            "",
            "对方 deterministic style profile JSON:",
            _to_json_line(other_style_profile),
            "",
            "对方风格护栏 JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in _style_hint_lines(other_style_profile))
    lines.extend(
        [
            "",
            "当前分支对话记录 JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in transcript)
    return "\n".join(lines)


def _build_next_turn_prompt(
    *,
    context_pack: dict[str, Any],
    assessment: dict[str, Any],
    transcript: list[dict[str, Any]],
    current_state: dict[str, Any],
    speaker_role: str,
) -> str:
    persona_key = "persona_self" if speaker_role == "self" else "persona_other"
    speaker_persona = context_pack.get(persona_key) or {}
    speaker_style_profile = _persona_style_profile(speaker_persona)
    lines = [
        "请根据下面这条反事实分支的当前状态，生成指定说话者的下一句消息，并输出结构化 JSON。",
        "",
        "你的目标不是把对话写得更好看，而是让它继续以“当前这个人、当前这个状态、当前这个节奏”自然往下走一轮。",
        "",
        "请根据下面规则完成生成，并只输出最终 JSON，不要输出推理过程：",
        "",
        "1. 总体原则",
        "- 你当前只负责生成一轮，而且只能生成指定说话者这一轮",
        "- 这句话必须同时受 BranchAssessment、当前分支状态、当前 transcript、指定说话者 persona 和相关话题约束",
        "- 继续往下走时，要优先保持真实、克制、自然，而不是让对话越来越会说、越来越完整、越来越理想",
        "- 如果当前关系状态仍有限、仍有保留、仍有 tension 或当前说话者本来就偏简短，那这一轮也应如实体现",
        "- 不要为了让故事推进，而让人物突然突破当前关系允许的表达强度",
        "- 允许自然变短、自然停住，不以把对话写完整为目标",
        "",
        "2. `message_text` 的职责",
        "- 生成指定说话者在当前这一轮最可能说出的下一句消息",
        "- 这句话应承接上一轮，但不能只是换个说法重复上一句",
        "- 这句话应符合该说话者 persona、当前状态和前面 transcript 已形成的风格密度",
        "- 若 deterministic style profile 指定偏短句、单泡或最多两条短泡，必须按该 envelope 控制长度和拆泡",
        "- 如果继续深入不自然，可以保持简短、有限承接、有限回应、轻微推进或自然收束",
        "- 不要把一轮写成一大段分析、解释或关系总结",
        "",
        "3. `strategy_used` 的职责",
        "- 说明这一轮实际采用了什么互动策略",
        "- 应体现该说话者此刻是在延续、确认、试探、轻接、保留、缓和、回避、收束还是有限推进",
        "- 不要写成关系评价",
        "",
        "4. `state_after_turn` 的职责",
        "- 估计这条消息说出后，当前分支状态发生了什么即时变化",
        "- 这里只做一轮后的有限修正，不做长期走势判断",
        "- 如果这一轮只是轻接或保留，状态变化也应有限",
        "- 不要因为一句顺滑的话，就把 openness、temperature、phase 写成明显大幅跃迁",
        "",
        "5. `generation_notes` 的职责",
        "- 用 1 到 3 句简洁说明：为什么这一轮会这么说",
        "- 重点说明这句话如何受 persona、当前状态、上一轮语气和当前节奏约束",
        "- 不要复述 message_text 本身",
        "- 不要写泛泛空话",
        "",
        "6. `should_stop` 与 `stopping_reason` 的职责",
        "- 如果这条分支在这一轮后已经自然收口，或继续生成只会机械重复、硬聊、失真，才将 `should_stop = true`",
        "- `stopping_reason` 要简洁说明为什么此时更适合停下",
        "- 如果对话仍自然可继续，则 `should_stop = false`",
        "- 不要为了省事过早停止，也不要为了凑轮次强行继续",
        "",
        "7. 生成边界提醒",
        "- 不要让这一轮说得比当前关系允许的更多、更深、更热",
        "- 不要突然让角色变得比 persona 更成熟、更会承接、更会沟通",
        "- 不要连续几轮都只是在同一个意思上轻微改写",
        "- 不要强行制造重大情绪升级或重大关系进展",
        "- 不要把 transcript 里没有铺垫的信息突然说出来",
        "",
        "7.5. 证据边界与 branch transcript 优先级",
        "- 当前 branch transcript 是分支内事实源，后续生成只能沿着它自然继续",
        "- modeler-only future evidence 只用于人格稳定、风险保守度和关系推进上限，不能作为角色台词来源",
        "- 如果用户在分支中改变了走向，以当前分支为准，不要把原时间线后续事件强行搬进分支",
        "- 不得说“后来”“我之后才发现”“我后来告诉过你我喜欢/不喜欢”这类暴露 cutoff 后事实的话",
        "",
        "8. 边界示例",
        "",
        "示例1：当前状态只是略有缓和，上一轮也只是轻接一下",
        "正确倾向：",
        "- 下一轮可以顺着接一点，但不应突然进入深层表达或完整问题解决",
        "- state_after_turn 应只做有限改善",
        "",
        "示例2：指定说话者 persona 偏简短、偏保留",
        "正确倾向：",
        "- 即使当前分支比原始情况更顺，也不应突然写出很长、很会说的话",
        "",
        "示例3：上一轮和再上一轮已经在表达相似意思",
        "正确倾向：",
        "- 这一轮要么换成真正的新推进，要么自然收束",
        "- 如果继续只会重复，应考虑 should_stop = true",
        "",
        "示例4：当前说话者是 self，而 BranchAssessment 显示整体只是有限正向",
        "正确倾向：",
        "- self 这一轮也不应突然大幅推进关系",
        "- 可以顺势说一点，但要符合当前 openness 和 temperature",
        "",
        "9. 输出质量要求",
        "- `message_text` 要真实可发",
        "- `strategy_used` 要体现当前轮策略",
        "- `state_after_turn` 要是有限即时更新",
        "- `generation_notes` 要解释这轮为何这样说",
        "- 如果应停，就用 `should_stop` 和 `stopping_reason` 明确表达",
        "- 如果继续只会重复礼貌承接或轻微改写上一句，应优先收束",
        "- 各字段不要重复堆砌同一个意思",
        "",
        "请再次自检：",
        "- 有没有让这一轮说得比当前关系允许的更多、更深、更热",
        "- 有没有把这一轮写成上一轮的换皮重复",
        "- 有没有忽视指定说话者 persona",
        "- 有没有把 state_after_turn 写得跳变过大",
        "- 有没有为了凑轮次硬继续，而不是自然推进或自然收束",
        "- 有没有把 modeler-only future evidence 或原时间线后续事件搬进当前分支",
        "",
        "下一轮请求 JSON:",
        _to_json_line({"speaker_role": speaker_role}),
        "",
        "分支判断结果 JSON:",
        _to_json_line(assessment),
        "",
        "证据分层策略 JSON:",
        _to_json_line(context_pack.get("evidence_policy") or {}),
        "",
        "modeler-only future evidence JSONL:",
    ]
    lines.extend(_to_json_line(item) for item in (context_pack.get("future_evidence_digests") or []))
    lines.extend(
        [
            "",
            "branch-only facts JSON:",
            _to_json_line(context_pack.get("branch_facts") or {}),
            "",
            "cutoff-safe related topic digests JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in (context_pack.get("related_topic_digests") or []))
    lines.extend(
        [
            "",
            "当前分支状态 JSON:",
            _to_json_line(current_state),
            "",
            "当前说话者人格画像 JSON:",
            _to_json_line(speaker_persona),
            "",
            "当前说话者 deterministic style profile JSON:",
            _to_json_line(speaker_style_profile),
            "",
            "当前说话者风格护栏 JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in _style_hint_lines(speaker_style_profile))
    lines.extend(
        [
            "",
            "当前分支对话记录 JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in transcript)
    return "\n".join(lines)


def _build_branch_reply_prompt(
    *,
    session_memory_pack: dict[str, Any],
    branch_transcript: list[dict[str, Any]],
    pending_self_messages: list[dict[str, Any]],
    current_branch_state: dict[str, Any],
) -> str:
    compatibility_pack = ((session_memory_pack.get("compatibility") or {}).get("cutoff_safe_context_pack") or {})
    layered_context_pack = session_memory_pack.get("layered_context_pack") or {}
    persona_other = compatibility_pack.get("persona_other") or {}
    other_style_profile = _persona_style_profile(persona_other)
    lines = [
        "请根据下面的实时反事实分支会话，生成 other 的下一条回复，并输出结构化 JSON。",
        "",
        "你的目标是让 other 对用户最新 self 输入做出真实、克制、符合对方 persona 的即时回应。",
        "",
        "硬性边界：",
        "- 只生成 other 的下一条消息，不要生成 self 消息。",
        "- 不要总结整段关系，不要替用户决定下一句怎么说。",
        "- 用户实时输入优先于 persona_self；persona_self 只用于理解，不用于改写用户输入。",
        "- persona_other 是主要生成约束。",
        "- 若 persona_other.deterministic_style_profile 指定偏短句、单泡或最多两条短泡，必须按该 envelope 控制长度和拆泡。",
        "- objective_moment_facts 只能作为 other 此刻处境背景，帮助你理解角色现实状态；不得把背景事实当作台词素材直接复述、引用或解释来源。",
        "- 如果 pending self 没有自然触发 objective_moment_facts 中的背景，不要主动说出这些背景。",
        "- 如果 session_memory_pack 中存在 cutoff 后证据，只能用于保守估计风险，不能让 other 说出这些未来事实。",
        "- 当前 branch_transcript 与 pending_self_messages 是分支事实源；不要把原时间线后续事件强行搬进分支。",
        "- 不得引用、复述或暗示 future evidence 中的拒绝、偏好、解释或关系状态。",
        "- 如果 pending_self_messages 是连续多条 self 消息，应把它们当作同一轮用户输入一起回应。",
        "",
        "输出字段要求：",
        "- `message_text`：other 此刻最可能发出的下一条消息。",
        "- `strategy_used`：这条回复采用的互动策略。",
        "- `state_after_turn`：这条 other 回复之后的即时分支状态。",
        "- `generation_notes`：用 1 到 3 句说明回复如何受 persona_other、当前状态和用户最新输入约束。",
        "",
        "证据分层策略 JSON:",
        _to_json_line(layered_context_pack.get("evidence_policy") or {}),
        "",
        "objective moment facts JSON:",
        _to_json_line(layered_context_pack.get("objective_moment_facts") or {}),
        "",
        "modeler-only future evidence JSONL:",
    ]
    lines.extend(_to_json_line(item) for item in (layered_context_pack.get("future_evidence_digests") or []))
    lines.extend(
        [
            "",
            "branch-only facts JSON:",
            _to_json_line(layered_context_pack.get("branch_facts") or {}),
            "",
            "session_memory_pack JSON:",
            _to_json_line(session_memory_pack),
            "",
            "current_branch_state JSON:",
            _to_json_line(current_branch_state),
            "",
            "persona_other JSON:",
            _to_json_line(persona_other),
            "",
            "persona_other deterministic style profile JSON:",
            _to_json_line(other_style_profile),
            "",
            "persona_other 风格护栏 JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in _style_hint_lines(other_style_profile))
    lines.extend(
        [
            "",
            "branch_transcript JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in branch_transcript)
    lines.extend(
        [
            "",
            "pending_self_messages JSONL:",
        ]
    )
    lines.extend(_to_json_line(item) for item in pending_self_messages)
    return "\n".join(lines)


def _build_branch_transcript_seed(*, context_pack: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "speaker_role": item.get("speaker_role"),
            "message_text": item.get("content_text"),
        }
        for item in (context_pack.get("current_segment_history") or [])
    ]


def _is_repeated_turn(*, speaker_role: str, message_text: str, transcript: list[dict[str, Any]]) -> bool:
    normalized = _normalize_message_text(message_text)
    if not normalized:
        return True
    recent_same_speaker = [
        _normalize_message_text(item.get("message_text", ""))
        for item in reversed(transcript)
        if item.get("speaker_role") == speaker_role
    ][:2]
    return normalized in recent_same_speaker


def _normalize_message_text(value: str) -> str:
    lowered = value.casefold()
    lowered = re.sub(r"\s+", "", lowered)
    lowered = re.sub(r"[，。！？,.!?:：~～]+", "", lowered)
    return lowered


def _to_json_line(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def _persona_style_profile(persona_payload: dict[str, Any]) -> dict[str, Any]:
    style_profile = persona_payload.get("deterministic_style_profile")
    if isinstance(style_profile, dict):
        return style_profile
    return {}


def _style_hint_lines(style_profile: dict[str, Any]) -> list[dict[str, Any]]:
    lines: list[dict[str, Any]] = []
    reply_envelope = style_profile.get("reply_envelope")
    if isinstance(reply_envelope, dict) and reply_envelope:
        lines.append(reply_envelope)
    generation_hints = style_profile.get("generation_hints")
    if isinstance(generation_hints, list):
        for hint in generation_hints:
            if hint:
                lines.append({"hint": hint})
    return lines
