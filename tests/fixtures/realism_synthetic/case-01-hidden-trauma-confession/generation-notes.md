# 隐藏心理阴影导致告白失败：生成记录

## 生成约束

- 通过 `scripts/generate_realism_synthetic_corpus.py` 调用本地 `llm_match_config.env` 中的 Responses API 配置生成。
- API key 只在本地读取，未写入本文件或语料。
- LLM 输出 JSON 消息数组，脚本统一写成 QQChatExporter 兼容文本。
- 脚本校验消息数量、说话人、锚点消息、单行内容和隐私风险词。

## 数量与跨度

- 消息数：3523
- 时间范围：2026-02-03 11:34:09 - 2026-05-05 22:03:04
- chunk 数：12

## prompt 结构

- system/instructions：限定为中文合成私聊消息生成器，只输出 JSON，固定双方说话人，禁止真实 PII。
- user/input：提供关系设定、上一 chunk 连续性摘要、当前 chunk 时间范围、关系状态、必含事件和逐字锚点消息。
- output：`messages`、`continuity_summary`、`quality_notes`。

## 自动复核

- 拟真性评分：4
- 故事一致性评分：5
- 项目标准评分：4
- 是否通过：True
- 复核摘要：整体像日常私聊，暧昧推进、告白受挫和事后阴影解释清晰，锚点支撑改写点。仅少量时间表述略不自然。
- 缺陷记录：
  - 未发现阻断问题。
