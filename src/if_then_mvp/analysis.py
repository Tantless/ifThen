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


class TopicAssignmentMatch(BaseModel):
    topic_id: int
    link_reason: str
    score: float


class TopicAssignmentPayload(BaseModel):
    matched_topics: list[TopicAssignmentMatch]
    should_create_new_topic: bool


class TopicCreationPayload(BaseModel):
    topic_name: str
    topic_summary: str
    topic_status: str
    relevance_reason: str


class TopicMergeDecision(BaseModel):
    source_topic_ids: list[int]
    merged_topic_name: str
    merged_topic_summary: str
    merged_topic_status: str
    merge_reason: str


class TopicMergeReviewPayload(BaseModel):
    merges: list[TopicMergeDecision]


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
    "你是一个“截止安全”的聊天片段分析器。"
    "你的任务是从当前提供的聊天片段中，提炼后续检索、关系建模和推演需要的结构化信息。"
    "你必须遵守以下规则："
    "1. 只能依据当前会话段消息，以及可选的上一条关系快照摘要进行判断。"
    "2. 绝对不能引用这段时间点之后才发生的内容。"
    "3. 绝对不能脑补片段之外的剧情、关系结论或隐藏动机。"
    "4. 如果证据不足，优先保守判断，不要夸大冲突、亲密或关系变化。"
    "5. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
)
TOPIC_ASSIGNMENT_SYSTEM_PROMPT = (
    "你是一个“截止安全”的聊天主题归属判断器。"
    "你的任务是判断：当前这个会话段摘要，是否应归入已有 topic，以及应归入哪些 topic。"
    "你必须遵守以下规则："
    "1. 只能依据当前提供的会话段摘要和已有 topic 信息进行判断。"
    "2. 绝对不能引用摘要之外的信息，更不能引入未来内容。"
    "3. 判断 topic 归属时，优先看共同议题、共同问题、共同关系线，而不是只看情绪是否相似。"
    "4. topic 的粒度应当是“中粒度、可复用、具备实际语义领域的话题”，不能过泛，也不能过窄。"
    "5. 如果当前片段讨论的是某个已有 topic 下的具体子问题，应优先归入该上位 topic，而不是因为细节变化就要求新建更窄 topic。"
    "6. 允许一个会话段同时归属多个 topic，但只有在证据明确时才这样做。"
    "7. 如果当前会话段与所有已有 topic 都不够贴合，应明确返回需要新建 topic，而不是强行挂靠。"
    "8. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
)
TOPIC_CREATION_SYSTEM_PROMPT = (
    "你是一个“截止安全”的聊天主题创建器。"
    "你的任务是在当前会话段不适合归入任何已有 topic 时，为它创建一个新的 topic。"
    "你必须遵守以下规则："
    "1. 只能依据当前提供的会话段摘要进行判断。"
    "2. 绝对不能引用摘要之外的信息，更不能引入未来内容。"
    "3. 你创建的 topic 必须是“中粒度、可复用、具备实际语义领域的话题”，不能过泛，也不能过窄。"
    "4. topic 的目标是服务后续检索、关系建模和推演，因此应优先创建“可持续命中”的话题，而不是一次性的局部细节标签。"
    "5. 如果当前片段只是在某个非常窄的局部子问题上展开，你应优先提炼它所属的上位话题，而不是直接把局部细节命名成 topic。"
    "6. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
)
TOPIC_MERGE_REVIEW_SYSTEM_PROMPT = (
    "你是一个“截止安全”的聊天主题合并审查器。"
    "你的任务是检查一组已有 topic，判断其中哪些 topic 实际上属于同一条中粒度主题线，因此应当合并。"
    "你必须遵守以下规则："
    "1. 只能依据当前提供的 topic 信息进行判断。"
    "2. 绝对不能引用 topic 之外的信息，更不能引入未来内容。"
    "3. 你的目标不是机械减少 topic 数量，而是把 topic 收敛为“中粒度、可复用、具备实际语义领域的话题”。"
    "4. 如果多个 topic 只是名字不同、局部表述不同、子问题不同，但未来大概率会命中同一类 segment，应考虑合并。"
    "5. 如果多个 topic 虽然都属于同一大领域，但在后续检索和推演中具有明显不同的实际用途，应保留分开。"
    "6. 不要因为情绪相似或互动方式相似就合并 topic。"
    "7. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
)
PERSONA_SYSTEM_PROMPT = (
    "你是一个“截止安全”的关系语境人格画像提炼器。"
    "你的任务不是写人物小传，也不是总结单次聊天状态，而是从当前提供的截止安全证据中，"
    "提炼某个说话者在这段关系里的稳定表达倾向、冲突反应模式，以及仅对当前聊天对象成立的互动模式。"
    "你必须遵守以下规则："
    "1. 只能依据当前提供的会话段摘要进行判断。"
    "2. 绝对不能引用这些摘要之外的信息，更不能引入未来发生的内容。"
    "3. 你要提炼的是“跨多段相对稳定、可复用、能约束后续推演”的倾向，而不是单次事件或短期情绪。"
    "4. 如果证据不足，必须保守，不要把偶发行为、单次冲突或一时冷淡夸大成长期人格特征。"
    "5. 不要做心理诊断、依恋类型判断、创伤推测或隐藏动机猜测。"
    "6. `global_persona_summary`、`style_traits`、`conflict_traits`、`relationship_specific_patterns` 各自职责不同，不能互相重复堆砌。"
    "7. 你的输出必须服务后续分支判断和对话推演，因此要尽量写成“这个人通常怎么说、怎么应对、面对当前对象有什么特别模式”，而不是空泛评价。"
    "8. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
)
SNAPSHOT_SYSTEM_PROMPT = (
    "你是一个“截止安全”的关系状态快照估计器。"
    "你的任务不是复述当前会话段发生了什么，而是根据上一条关系快照和当前会话段摘要，"
    "估计“截至当前会话段结束时”这段关系所处的状态。"
    "你必须遵守以下规则："
    "1. 只能依据当前提供的上一条关系快照摘要和当前会话段摘要进行判断。"
    "2. 绝对不能引用这些材料之外的信息，更不能引入未来发生的内容。"
    "3. 你要做的是在已有关系背景上进行连续更新，而不是每次都从零重新判断。"
    "4. 如果证据不足，必须保守，不要把单段氛围、一次解释或一次冷淡夸大成整体关系转折。"
    "5. 不要把普通简短、普通礼貌、普通谨慎自动解释为高 tension、高 defensiveness 或关系恶化。"
    "6. `relationship_temperature`、`tension_level`、`openness_level`、`initiative_balance`、`defensiveness_level`、`unresolved_conflict_flags`、`relationship_phase` 各自职责不同，不能互相混淆或重复。"
    "7. `relationship_phase` 只能在趋势相对明确时使用，不能只依据当前这一段的局部气氛下重判断。"
    "8. `unresolved_conflict_flags` 只有在确实存在未化解的问题、误解、冲突或推进阻力时才填写，否则应保持空列表。"
    "9. `snapshot_summary` 必须总结当前时点的关系状态及其相对上一快照的有限变化，而不是复述当前段剧情。"
    "10. 只返回一个符合 schema 的 JSON 对象，不要输出解释、备注或推理过程。"
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


def assign_segment_topics(
    *,
    llm_client: ChatJSONClient,
    current_segment_summary: dict,
    existing_topics: list[dict],
) -> TopicAssignmentPayload:
    return llm_client.chat_json(
        system_prompt=TOPIC_ASSIGNMENT_SYSTEM_PROMPT,
        user_prompt=_build_topic_assignment_prompt(
            current_segment_summary=current_segment_summary,
            existing_topics=existing_topics,
        ),
        response_model=TopicAssignmentPayload,
    )


def build_topic_creation_payload(
    *,
    llm_client: ChatJSONClient,
    current_segment_summary: dict,
) -> TopicCreationPayload:
    return llm_client.chat_json(
        system_prompt=TOPIC_CREATION_SYSTEM_PROMPT,
        user_prompt=_build_topic_creation_prompt(current_segment_summary=current_segment_summary),
        response_model=TopicCreationPayload,
    )


def review_topic_merges(
    *,
    llm_client: ChatJSONClient,
    topics: list[dict],
) -> TopicMergeReviewPayload:
    return llm_client.chat_json(
        system_prompt=TOPIC_MERGE_REVIEW_SYSTEM_PROMPT,
        user_prompt=_build_topic_merge_review_prompt(topics=topics),
        response_model=TopicMergeReviewPayload,
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
    lines: list[str] = [
        "请分析下面这段聊天片段，并输出结构化 JSON。",
        "",
        "你的目标不是泛泛概括聊天内容，而是为后续检索、关系建模和推演提炼可用信息。",
        "",
        "请根据下面规则完成判断，并只输出最终 JSON，不要输出推理过程：",
        "",
        "1. 话题与摘要",
        "- `summary_text`：用 2 到 4 句概括这段实际发生了什么，要求具体，不要空话",
        "- `main_topics`：写 1 到 3 个核心话题，不要堆关键词，也不要写得过泛",
        "",
        "2. 双方立场",
        "- `self_stance`：描述我方在这段里的态度、动作或策略",
        "- `other_stance`：描述对方在这段里的态度、动作或策略",
        "- 这里只总结“这段里发生了什么”，不要上升为长期人格判断",
        "",
        "3. 情绪与互动方式",
        "- `emotional_tone`：写整体情绪基调，例如：轻松、中性、谨慎、紧张、别扭、试探",
        "- `interaction_pattern`：写互动方式，例如：日常接话、轻松调侃、简短确认、解释澄清、试探靠近、回避推进、争执拉扯",
        "- 两者不要重复表达同一件事",
        "",
        "4. 事件信号",
        "- `has_conflict`：只有在有明确对立、防御、争执、指责或明显不满时才为 true",
        "- `has_repair`：只有在有明确缓和、解释化解、安抚、给台阶、修复误会时才为 true",
        "- `has_closeness_signal`：只有在有明确靠近、关心、调情、情绪承接、关系推进时才为 true",
        "- 普通礼貌、普通玩笑、普通接话，不自动算作 closeness",
        "",
        "5. 结果与关系影响",
        "- `outcome`：描述这段最后实际落到了哪里，例如：继续聊天、轻松收尾、话题中断、问题未解决、达成共识",
        "- `relationship_impact`：只判断这段本身对关系造成的实际影响，优先保守，不要夸大",
        "",
        "6. 置信度",
        "- `confidence`：0 到 1 之间；证据越明确越高，模糊时更低",
        "",
        "边界示例：",
        "",
        "示例1：",
        "输入特征：双方只是简短回复，没有明显指责、防御、情绪升级",
        "正确倾向：",
        "- `has_conflict = false`",
        "- 不要因为“话少”就判断为冲突",
        "",
        "示例2：",
        "输入特征：出现玩笑、调侃、轻松接话，但没有明确靠近、关心、关系推进",
        "正确倾向：",
        "- `has_closeness_signal = false` 或保持保守",
        "- 不要因为“有梗、有玩笑”就自动判断关系明显升温",
        "",
        "示例3：",
        "输入特征：一方先缓和语气、解释误会、给台阶，另一方明显接住",
        "正确倾向：",
        "- 可以判断 `has_repair = true`",
        "- `relationship_impact` 可以偏保守地写为修复中的正向变化",
        "",
        "请再次自检：",
        "- 有没有使用未来信息",
        "- 有没有把短句误判成冲突",
        "- 有没有把玩笑误判成亲密",
        "- 有没有把这段写得比原文更戏剧化",
        "",
    ]
    if previous_snapshot_summary:
        lines.append("上一条关系快照 JSON:")
        lines.append(_to_json_line({"snapshot_summary": previous_snapshot_summary}))
        lines.append("")
    lines.append("当前会话段消息 JSONL:")
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
        "请根据下面这些会话段摘要，为指定说话者生成结构化 persona 画像，并输出 JSON。",
        "",
        "你的目标不是写好看的人物分析，而是提炼后续关系建模和聊天推演真正可用的稳定约束。",
        "",
        "你要处理的对象是：",
        "- `subject_role = self`：表示总结“我方”在这段关系中的稳定表达与互动模式",
        "- `subject_role = other`：表示总结“对方”在这段关系中的稳定表达与互动模式",
        "",
        "请根据下面规则完成判断，并只输出最终 JSON，不要输出推理过程：",
        "",
        "1. 总体原则",
        "- 只提炼相对稳定、跨多段重复出现的倾向",
        "- 单次事件、单段异常、某一时刻情绪，不应直接上升为长期人格",
        "- 证据不足时宁可写弱结论，也不要写戏剧化强结论",
        "- 不要把“这段关系当前状态”误写成人格本身；关系状态属于 snapshot，不属于 persona",
        "",
        "2. `global_persona_summary` 的职责",
        "- 用 2 到 4 句总结该角色在这段关系中的总体互动倾向",
        "- 应写这个人通常如何表达、如何推进互动、如何处理分寸和情绪",
        "- 应尽量体现“稳定倾向”，而不是复述某几段发生了什么",
        "- 不要写成文学化、空泛、无法约束后续推演的评价",
        "- 不要只写“细腻、复杂、敏感、有边界感”这类抽象标签，除非它们被具体互动模式支撑",
        "",
        "3. `style_traits` 的职责",
        "- 写 3 到 6 条“说话方式上的稳定特征”",
        "- 例如：回复偏短还是偏长、表达偏直接还是偏含蓄、是否爱解释、是否喜欢留余地、是否常用玩笑/缓冲/试探",
        "- 这里写的是“怎么说”",
        "- 不要把冲突反应、关系阶段、心理成因写进来",
        "- 每条尽量具体，可直接服务后续生成",
        "",
        "4. `conflict_traits` 的职责",
        "- 写 2 到 5 条在压力、误解、争执、推进受阻时的常见反应模式",
        "- 例如：先解释降温、回避正面冲突、转轻松话题、短句收缩、反问、冷处理、给台阶、缓和但不正面展开",
        "- 这里写的是“被触发后通常怎么应对”",
        "- 不要把普通聊天风格重复写进来",
        "- 如果证据很少，不要硬写满",
        "",
        "5. `relationship_specific_patterns` 的职责",
        "- 写 2 到 5 条“面对当前这个聊天对象时”才更明显成立的互动模式",
        "- 重点回答：他/她面对这个对象时，是否会更主动、更谨慎、更会接梗、更会解释、更会回避、更容易试探或更容易防御",
        "- 这里写的是“对这个人有什么特别的互动方式”",
        "- 不要把对所有人都可能成立的普遍风格写进来",
        "- 不要复述具体事件本身，而要提炼成可复用模式",
        "",
        "6. 字段边界提醒",
        "- `global_persona_summary` = 总体稳定倾向",
        "- `style_traits` = 表达表层风格",
        "- `conflict_traits` = 压力/冲突下的反应方式",
        "- `relationship_specific_patterns` = 只在当前关系里更明显的特殊模式",
        "- 四个字段不要换个说法重复同一件事",
        "",
        "7. 边界示例",
        "",
        "示例1：某几段里对方回复很冷、很短，但其他段并不稳定如此",
        "正确倾向：",
        "- 不要直接写成“天生冷淡”或“长期疏离”",
        "- 更保守的写法应是：在部分压力或低投入场景下，倾向用短句降低互动强度",
        "",
        "示例2：某次争执里一方明显防御、解释很多",
        "正确倾向：",
        "- 可以谨慎写进 `conflict_traits`，前提是类似模式在多段中反复出现",
        "- 不要直接上升为心理学诊断或深层人格定义",
        "",
        "示例3：一个人整体说话都偏简短，但面对当前对象时会更愿意接玩笑、顺着说、给回应",
        "正确倾向：",
        "- “整体说话偏简短”更适合写进 `style_traits`",
        "- “面对当前对象时更愿意接玩笑/顺着说”更适合写进 `relationship_specific_patterns`",
        "",
        "示例4：某人会在互动里保持分寸，不轻易把话说满",
        "正确倾向：",
        "- 这可以进入 `global_persona_summary` 或 `style_traits`",
        "- 但必须尽量写成可操作的表达特征，例如“倾向留余地，不轻易下很重的情绪判断”",
        "",
        "示例5：当前关系里对方一被推进就后撤，但在别的材料里看不出这是不是全局人格",
        "正确倾向：",
        "- 更适合写为 `relationship_specific_patterns`，例如“面对当前对象的关系推进时，更容易收缩或回避”",
        "- 不宜直接写成全局人格特征",
        "",
        "8. 输出质量要求",
        "- 尽量避免空话、套话、文艺化评价",
        "- 尽量写成能约束后续推演的话",
        "- 如果材料不足，列表项可以更少，但不要为了凑数编造",
        "- `confidence` 取 0 到 1 之间；跨段证据越稳定越高，证据稀薄或矛盾时更低",
        "请再次自检：",
        "- 有没有把单次事件误写成长期人格",
        "- 有没有把短期状态误写成稳定特征",
        "- 有没有把关系特定模式误写成全局人格",
        "- 有没有把全局风格和冲突反应写重复",
        "- 有没有写出空泛但对推演无帮助的话",
        "- 有没有脑补没有证据支持的深层心理成因",
        "",
        "人格画像请求 JSON:",
        _to_json_line({"subject_role": subject_role}),
        "",
        "会话段摘要 JSONL:",
    ]
    lines.extend(_to_json_line(item) for item in segment_summaries)
    return "\n".join(lines)


def _build_snapshot_prompt(*, segment_summary: dict, prior_snapshot: str | None) -> str:
    lines = [
        "请根据下面的上一条关系快照和当前会话段摘要，生成截至当前段结束时的关系状态快照，并输出 JSON。",
        "",
        "你的目标不是复述这段聊天内容，而是提炼“此刻关系处在什么状态、相比上一状态有何有限变化”。",
        "",
        "请根据下面规则完成判断，并只输出最终 JSON，不要输出推理过程：",
        "",
        "1. 总体原则",
        "- 如果存在 `prior_snapshot`，应把它视为当前判断的背景状态",
        "- 当前会话段只负责在这个背景上做更新，而不是完全推翻之前状态",
        "- 没有强证据时，优先保持连续性和保守性，不要大幅跳变",
        "- 不要把当前段的局部氛围直接等同于整体关系状态",
        "",
        "2. `relationship_temperature` 的职责",
        "- 表示截至当前段结束时，这段关系整体的情感温度",
        "- 应判断关系整体更接近：冷、一般、中性偏暖、稳定偏暖、明显靠近中的哪类状态",
        "- 主要看双方是否愿意接住彼此、互动是否带有稳定的承接感或疏离感",
        "- 不要因为一次礼貌、一次轻松接话或一句关心就直接判断明显升温",
        "- 也不要因为一时简短或一时别扭就直接判断明显降温",
        "",
        "3. `tension_level` 的职责",
        "- 表示当前关系里有多强的紧绷、卡住、顾虑、误解或推进阻力",
        "- 应看是否存在明显拉扯、误解、难以展开、持续小心翼翼或话题推进受阻",
        "- 不要因为话少、回复短、表达克制就自动判断高 tension",
        "- tension 关注的是“关系里有多紧”，不是“聊天热不热闹”",
        "",
        "4. `openness_level` 的职责",
        "- 表示此刻双方有多愿意继续聊、继续展开、继续承接",
        "- 应看对话是否容易被接住、是否愿意继续推进同一话题或情绪",
        "- 不要因为关系温度偏暖就自动判断 openness 高",
        "- 也不要因为当前段没展开很多就自动判断 openness 低",
        "",
        "5. `initiative_balance` 的职责",
        "- 表示当前互动主动权更偏向谁",
        "- 应判断是我方更在推进、对方更在推进、双方大致平衡，还是整体推进动力偏弱",
        "- 不要只根据消息长短判断主动性",
        "- 重点看谁在开启、接续、维持或推动互动往前走",
        "",
        "6. `defensiveness_level` 的职责",
        "- 表示当前关系中是否已经出现明显的自我保护、防御、收缩或回避姿态",
        "- 应看是否出现解释自保、避免正面回应、主动降强度、绕开敏感点、后撤等迹象",
        "- 不要把普通分寸感、普通谨慎、普通简短自动判成高 defensiveness",
        "- defensiveness 关注的是“防御有没有被激活”，不等同于 tension",
        "",
        "7. `unresolved_conflict_flags` 的职责",
        "- 只写当前仍悬着、尚未化解的具体问题点",
        "- 例如：某次误解未真正化开、某个敏感推进点仍被回避、某个争议没有形成共识",
        "- 如果没有明确证据，应返回空列表",
        "- 不要用太抽象、太宽泛、太文学化的词来凑数",
        "",
        "8. `relationship_phase` 的职责",
        "- 表示截至此刻，这段关系更接近哪个整体阶段",
        "- 可保守使用如：`warming`、`steady`、`cooling`、`strained`、`repairing` 这类阶段",
        "- 该字段必须结合上一快照和当前段变化强度一起判断",
        "- 不要因为这一段局部轻松就直接写 `warming`",
        "- 不要因为一次冷淡、一次推进未接住就直接写 `cooling` 或 `strained`",
        "- 不要因为一次解释缓和就直接写 `repairing`，除非缓和证据足够明确",
        "",
        "9. `snapshot_summary` 的职责",
        "- 用 2 到 3 句总结截至当前段结束时的关系状态",
        "- 要体现整体状态，以及相对上一快照发生了什么有限变化",
        "- 不要把它写成当前段摘要复述",
        "- 不要写得比证据更戏剧化",
        "",
        "10. 边界示例",
        "",
        "示例1：当前段双方回复都比较短，但没有明显指责、防御、误解或卡住",
        "正确倾向：",
        "- 不要因为简短就判断 `tension_level` 高",
        "- 不要自动填写 `unresolved_conflict_flags`",
        "- `openness_level` 可以保守，但不应无依据地写得很低",
        "",
        "示例2：当前段气氛轻松，有普通接话和玩笑，但没有明确关系推进",
        "正确倾向：",
        "- 可以维持偏暖或稳定状态",
        "- 但不要仅因为轻松就判断关系明显升温",
        "- `relationship_phase` 不应轻易直接切到 `warming`",
        "",
        "示例3：当前段出现解释和缓和，但之前的 tension 是否真正解除并不明确",
        "正确倾向：",
        "- 可以写 tension 略缓、defensiveness 略降",
        "- 但不要轻易直接进入 `repairing`",
        "",
        "示例4：某次推进没有被完全接住，但还不足以证明关系明显转冷",
        "正确倾向：",
        "- 可以写 openness 有限、temperature 略收",
        "- 但不要夸大成 `cooling` 或 `strained`，除非证据持续且明确",
        "",
        "示例5：说话克制、留余地、谨慎，但没有明显自我保护动作",
        "正确倾向：",
        "- 这可能只是分寸感，不应自动判为高 `defensiveness_level`",
        "",
        "11. 输出质量要求",
        "- 优先写保守、可解释、可供后续推演使用的状态",
        "- 尽量让各字段之间分工清晰，不重复堆砌同一个意思",
        "- 如果证据不足，优先延续上一状态或只做小幅修正",
        "- 不要为了显得深刻而强行制造关系戏剧性",
        "",
        "请再次自检：",
        "- 有没有把当前段氛围误写成整体关系状态",
        "- 有没有忽视上一快照，导致状态跳变过大",
        "- 有没有把简短、谨慎或礼貌误判成高 tension 或高 defensiveness",
        "- 有没有在证据不足时滥写 unresolved_conflict_flags",
        "- 有没有把 relationship_phase 写得过重",
        "- 有没有把 snapshot_summary 写成当前段剧情复述",
        "- 有没有把变化写得比证据更戏剧化",
        "",
        "上一条关系快照 JSON:",
        _to_json_line({"snapshot_summary": prior_snapshot or "none"}),
        "",
        "当前会话段摘要 JSON:",
        _to_json_line(segment_summary),
    ]
    return "\n".join(lines)


def _build_topic_assignment_prompt(*, current_segment_summary: dict, existing_topics: list[dict]) -> str:
    lines = [
        "请判断下面这条会话段摘要，应该归入哪些已有 topic，并输出结构化 JSON。",
        "",
        "你的目标不是做表面相似度匹配，而是判断它是否与某条已有 topic 在“议题层、问题层、关系线层”上属于同一条主线。",
        "",
        "请根据下面规则完成判断，并只输出最终 JSON，不要输出推理过程：",
        "",
        "1. topic 粒度要求",
        "- topic 应该是一个“中粒度、可复用、具备实际语义领域的话题”",
        "- 不要把 topic 取成过泛概念，例如：`日常闲聊`、`轻松聊天`",
        "- 也不要把 topic 取成过窄的局部细节，例如：`宿舍申请 timing bug`",
        "- 更合理的粒度示例：`宿舍/住宿讨论`、`天气相关话题`、`学习/课程讨论`、`游戏相关话题`、`见面安排`、`关系试探`",
        "",
        "2. 归属判断原则",
        "- 优先依据共同议题、共同问题、共同关系线来判断",
        "- 可以参考互动方式和情绪，但它们只能作为辅助，不能单独成为归属依据",
        "- 如果当前片段讨论的是已有 topic 下的一个具体子问题，应优先挂到该 topic，而不是因为子问题不同就视为新 topic",
        "",
        "3. 多 topic 归属",
        "- 一个会话段可以同时归入多个 topic",
        "- 但只有在当前片段确实同时触及多条明确主题线时，才允许多归属",
        "- 如果只是轻微擦边，不要滥挂多个 topic",
        "",
        "4. 新建 topic 条件",
        "- 如果当前片段和所有已有 topic 都没有明确的议题级重合",
        "- 或只能勉强匹配到非常宽泛、非常牵强的 topic",
        "- 应返回 `should_create_new_topic = true`",
        "",
        "5. 归属理由",
        "- 对每个命中的 topic，都要给出简洁明确的 `link_reason`",
        "- `link_reason` 应说明共同点来自共同议题、共同问题、共同关系议题或同一条持续互动线",
        "- 不要只写“内容相似”",
        "",
        "6. 分数",
        "- `score` 表示当前片段与该 topic 的匹配程度",
        "- 只有在它明显属于该 topic 时，才给高分",
        "- 模糊时应降低分数，或直接不挂",
        "",
        "边界示例：",
        "",
        "示例1：当前片段继续讨论某个已多次出现的问题，比如见面安排、关系确认、某次争执后续",
        "正确倾向：应归入对应已有 topic，归属依据应写清是“同一持续议题”，而不是“语气相似”",
        "",
        "示例2：当前片段只是轻松闲聊，和已有多个轻松 topic 在情绪上相似，但议题不同",
        "正确倾向：不要仅凭情绪相似挂到已有 topic；如果没有明确议题重合，可以新建 topic",
        "",
        "示例3：当前片段同时涉及两条主线，比如一边继续聊日常安排，一边触及关系试探",
        "正确倾向：可以同时归入两个 topic，但前提是两条线都在当前片段中明确出现，而不是勉强联想",
        "",
        "完整流程示例：",
        "已有 topic 列表示意：",
        "1. topic_name = “宿舍/住宿讨论”",
        "   topic_summary = “围绕宿舍、住宿安排、办理流程、申请条件、居住相关问题的持续讨论”",
        "2. topic_name = “天气相关话题”",
        "   topic_summary = “围绕天气变化、气温、下雨、冷热感受等展开的持续讨论”",
        "3. topic_name = “关系试探”",
        "   topic_summary = “围绕情绪承接、关系确认、靠近试探展开的持续互动”",
        "",
        "当前会话段摘要示意：",
        "- summary_text = “双方继续吐槽宿舍办理流程里的 timing 卡点，并用游戏化的说法调侃规则设计。”",
        "- main_topics = [\"宿舍办理\", \"timing 卡点\", \"轻松调侃\"]",
        "- emotional_tone = \"轻松\"",
        "- interaction_pattern = \"轻松调侃\"",
        "",
        "正确判断倾向：",
        "- 应归入 “宿舍/住宿讨论”",
        "- 不应归入 “天气相关话题”",
        "- 不应仅因为语气轻松就新建 “轻松聊天” 之类的话题",
        "- 不应把当前片段单独新建成 “宿舍 timing 问题”",
        "- `should_create_new_topic = false`",
        "",
        "请再次自检：",
        "- 有没有把情绪相似误当成主题相同",
        "- 有没有因为局部细节不同就错误拆出更窄的新 topic",
        "- 有没有把 topic 名称写得过泛或过窄",
        "- 有没有为了减少新 topic 数量而强行挂靠",
        "- 有没有滥用多 topic 归属",
        "",
        "当前会话段摘要 JSON:",
        _to_json_line(current_segment_summary),
        "",
        "已有 topic 列表 JSONL:",
    ]
    lines.extend(_to_json_line(item) for item in existing_topics)
    return "\n".join(lines)


def _build_topic_creation_prompt(*, current_segment_summary: dict) -> str:
    lines = [
        "请根据下面这条会话段摘要，创建一个新的 topic，并输出结构化 JSON。",
        "",
        "这个 topic 将被用于后续：主题检索、segment 归属、关系建模和推演上下文组装。",
        "因此，你创建的 topic 必须稳定、可复用、语义清晰。",
        "",
        "请根据下面规则完成判断，并只输出最终 JSON，不要输出推理过程：",
        "",
        "1. topic_name 命名原则",
        "- `topic_name` 必须是一个中粒度、可复用、具备实际语义领域的话题名称",
        "- 不要过泛，例如：`日常闲聊`、`轻松聊天`、`聊天互动`",
        "- 不要过窄，例如：`宿舍申请 timing bug`、`今天突然降温`、`今晚这场雨`",
        "- 更合理的命名示例：`宿舍/住宿讨论`、`天气相关话题`、`学习/课程讨论`、`游戏相关话题`、`见面安排`、`关系试探`、`情绪安抚与支持`",
        "",
        "2. topic_summary 编写原则",
        "- `topic_summary` 描述这条 topic 主要覆盖的议题范围",
        "- 它应当说明：这类 topic 通常围绕什么事情展开，而不是只复述当前这一段",
        "- summary 要能容纳后续更多相关 segment，而不是写成一次性事件说明",
        "",
        "3. topic_status 判断原则",
        "- 优先使用保守判断，例如：`ongoing`、`dormant`、`resolved`、`sensitive_recurring`",
        "- 如果只有当前一个片段，通常优先判断为 `ongoing`",
        "- 只有证据明确显示该主题已收束，才判断为 `resolved`",
        "- 只有证据明确显示这是反复触发的敏感点，才判断为 `sensitive_recurring`",
        "",
        "4. relevance_reason 编写原则",
        "- `relevance_reason` 说明为什么当前片段足以支持创建这个新 topic",
        "- 要指出这条片段体现了哪类稳定议题、互动线或关系议题",
        "- 不要只写“内容相关”或“主题相似”",
        "",
        "边界示例：",
        "示例1：当前片段在聊“今天降温了、外面风很大、穿少了”",
        "正确倾向：更合适的新 topic 是 `天气相关话题`，不应新建成 `今天降温`",
        "",
        "示例2：当前片段在聊“宿舍办理 timing 卡点、流程规则、申请是否能过”",
        "正确倾向：更合适的新 topic 是 `宿舍/住宿讨论`，不应新建成 `宿舍 timing bug`",
        "",
        "示例3：当前片段在聊“今天打副本、掉装备、某个角色强度”",
        "正确倾向：更合适的新 topic 是 `游戏相关话题`，不应因为只提到某一把游戏过程，就把 topic 命名成一次性细节",
        "",
        "完整流程示例：",
        "当前会话段摘要示意：",
        "- summary_text = “双方聊到最近天气变化很大，一方提到降温后穿少了，另一方顺势接话讨论冷暖感受。”",
        "- main_topics = [\"降温\", \"天气变化\", \"穿衣感受\"]",
        "- emotional_tone = \"轻松\"",
        "- interaction_pattern = \"日常接话\"",
        "",
        "正确创建倾向：",
        "- `topic_name = 天气相关话题`",
        "- `topic_summary = 围绕天气变化、气温、冷热感受、下雨晴天等展开的持续讨论`",
        "- `topic_status = ongoing`",
        "- `relevance_reason = 当前片段明确围绕天气变化与体感展开，具备稳定的实际议题，不只是一次性的随机闲聊`",
        "",
        "请再次自检：",
        "- topic_name 是否过泛",
        "- topic_name 是否过窄",
        "- topic_summary 是否写成了当前单段复述",
        "- topic 是否具备后续复用价值",
        "- 有没有把局部子问题误当成独立长期 topic",
        "",
        "当前会话段摘要 JSON:",
        _to_json_line(current_segment_summary),
    ]
    return "\n".join(lines)


def _build_topic_merge_review_prompt(*, topics: list[dict]) -> str:
    lines = [
        "请审查下面这组 topic，判断哪些 topic 应当合并，并输出结构化 JSON。",
        "",
        "你的目标不是把 topic 越并越少，而是把它们整理为“中粒度、可复用、可持续命中”的主题集合。",
        "",
        "请根据下面规则完成判断，并只输出最终 JSON，不要输出推理过程：",
        "",
        "1. 合并原则",
        "- 如果多个 topic 本质上在讲同一个实际话题领域，只是名称不同、子问题不同、表述不同，应考虑合并",
        "- 如果多个 topic 未来大概率会命中同一类 segment，也应考虑合并",
        "- 合并后的 topic 应保留实际语义，不要变成空泛标签",
        "",
        "2. 不应合并的情况",
        "- 仅仅因为情绪相似、互动方式相似，不应合并",
        "- 仅仅因为都属于同一个大类，但在后续检索和推演中会服务不同用途，不应合并",
        "- 如果两个 topic 一个过宽、一个过窄，也不要简单保留过宽的那个吞掉一切；应判断它们是否应合并成一个更合理的中粒度 topic",
        "",
        "3. 合并后的 topic 粒度",
        "- 合并后的 `merged_topic_name` 必须是中粒度、可复用、具备实际语义领域的话题",
        "- 不要过泛，例如：`日常闲聊`、`轻松互动`、`聊天内容`",
        "- 不要过窄，例如：`宿舍申请 timing bug`、`今天突然降温`",
        "- 更合理的合并后命名示例：`宿舍/住宿讨论`、`天气相关话题`、`学习/课程讨论`、`游戏相关话题`、`关系试探`",
        "",
        "4. 合并结果说明",
        "- 对每组应合并的 topic，给出：哪些 topic 需要合并、合并后的 topic_name、topic_summary、topic_status、merge_reason",
        "- `merge_reason` 要说明为什么这些 topic 实际上是同一条主题线",
        "",
        "边界示例：",
        "示例1：topic A = `宿舍申请 timing 问题`；topic B = `宿舍办理流程`；topic C = `住宿安排讨论`",
        "正确倾向：这几条大概率应合并，更合理的合并后名字是 `宿舍/住宿讨论`",
        "",
        "示例2：topic A = `天气相关话题`；topic B = `学习/课程讨论`；虽然两个 topic 都经常以轻松语气出现",
        "正确倾向：不应合并，情绪相似不等于主题相同",
        "",
        "示例3：topic A = `关系试探`；topic B = `情绪安抚与支持`；这两个 topic 可能都与亲密关系相关",
        "正确倾向：不能因为都与关系相关就直接合并，只有在长期命中同一类 segment、后续用途也高度重合时才考虑合并",
        "",
        "完整流程示例：",
        "当前 topic 列表示意：",
        "1. topic_name = `宿舍申请 timing 问题`",
        "   topic_summary = `围绕宿舍申请时间窗口、流程卡点和 timing bug 的讨论`",
        "2. topic_name = `宿舍办理流程`",
        "   topic_summary = `围绕宿舍相关办理规则、手续和流程问题的讨论`",
        "3. topic_name = `天气相关话题`",
        "   topic_summary = `围绕天气变化、气温、冷热感受等展开的讨论`",
        "",
        "正确判断倾向：",
        "- topic 1 和 topic 2 应合并",
        "- 合并后更合理的名字应是 `宿舍/住宿讨论`",
        "- topic 3 不应参与合并，因为它属于完全不同的话题领域",
        "",
        "请再次自检：",
        "- 有没有只因为名字不同就漏掉应合并的 topic",
        "- 有没有只因为都很轻松就错误合并",
        "- 有没有把合并后的 topic 名称写得过泛",
        "- 有没有把局部子问题错误保留成独立长期 topic",
        "",
        "当前 topic 列表 JSONL:",
    ]
    lines.extend(_to_json_line(item) for item in topics)
    return "\n".join(lines)


def _build_jsonl_prompt(*, heading: str, items: list[dict]) -> str:
    lines = [heading]
    lines.extend(_to_json_line(item) for item in items)
    return "\n".join(lines)


def _to_json_line(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)
