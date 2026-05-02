# TODO 01-pre：LLM 构筑拟真长消息测试集

## 问题

当前 `realism-01-baseline-and-evaluation.md` 依赖固定样例，但仓库里没有适合提交的真实“可改写关键节点”聊天记录。直接进入评估集建设会缺少样本基础，也容易把隐私数据带入仓库。

本前置阶段先生成合成拟真长消息测试集，专门服务真实性路线图的核心产品亮点：只看 cutoff 前历史可能会误判，而使用 cutoff 后客观事实作为 modeler-only evidence 可以让推演更保守、更真实。

## 目标

生成 3 段每段 1000+ 条的可导入合成聊天记录。每段都必须包含关键可改写点、cutoff 后真相揭示和评估标注，并能用于后续 `single_reply` / `short_thread` 或实时分支会话的真实性评估。

## 输出

每段语料最终至少包含：

- `conversation.txt`：QQChatExporter 兼容文本，可被现有 `parse_qq_export()` 解析。
- `timeline.md`：关系时间线、阶段摘要和关键事件。
- `rewrite-points.md`：关键改写点、原句、建议改写、cutoff、预期评估。
- `truth-after-cutoff.md`：cutoff 后才揭示的客观事实，标注为 modeler-only evidence。
- `generation-notes.md`：生成约束、chunk 连续性摘要和人工校验记录。

建议目录结构：

```text
tests/fixtures/realism_synthetic/
  case-01-hidden-trauma-confession/
    conversation.txt
    timeline.md
    rewrite-points.md
    truth-after-cutoff.md
    generation-notes.md
  case-02-conflict-repair/
    ...
  case-03-missed-window/
    ...
```

## QQ 文本格式约束

`conversation.txt` 必须使用现有解析器能识别的结构：

```text
[QQChatExporter V5 / https://github.com/shuakami/qq-chat-exporter]

聊天名称: 对方昵称
聊天类型: 私聊
导出时间: 2026-05-02 20:00:00
消息总数: 1000
时间范围: 2026-02-01 09:00:00 - 2026-05-01 23:00:00


对方昵称:
时间: 2026-02-01 09:00:00
内容: 第一条消息


我:
时间: 2026-02-01 09:00:10
内容: 第二条消息
```

## 三段语料设计

### 1. 隐藏心理阴影导致告白失败

- 男女主 2 月偶然相识，加微信后迁移到日常聊天。
- 2-3 月围绕共同兴趣和日常生活聊天，逐渐出现轻微暧昧。
- 4 月暧昧增强，男主视角认为女主没有明显拒绝理由。
- 女主因过往心理阴影不敢进入关系，但告白前一直没有明说。
- 男主告白失败，女主犹豫拒绝。
- 拒绝后女主才解释背景和真实顾虑。
- 核心评估点：只看 cutoff 前会过度乐观；使用 cutoff 后真相应判断“更好说辞也不必然成功”。

### 2. 冲突修复型

- 双方关系稳定，但现实压力逐渐累积。
- 男主某条消息用玩笑或理性分析回应女主情绪，触发女主防御。
- 后续聊天揭示女主当时不是无理取闹，而是家庭、学业或工作事件叠加。
- 核心改写点：男主如果先承接情绪而不是解释道理，可能避免冲突升级。
- 核心评估点：系统需要区分“她在发脾气”与“她在求承接”。

### 3. 错过窗口型

- 双方长期暧昧但节奏不一致。
- 女主多次轻微试探邀请或表达靠近。
- 男主因为自卑、迟钝或回避，用轻描淡写或玩笑错过。
- 后续女主逐渐降温，并在后面透露“当时其实给过机会”。
- 核心改写点：男主某条冷处理或玩笑回复如果改成低压力承接，可能延续窗口。
- 核心评估点：不是所有改写都改变结局，但正确改写应提高首轮可接性和延缓冷却。

## 生成策略

- 不一次性要求 LLM 输出 1000+ 条消息。
- 每段先生成关系设定、人物表达风格、时间线跨度图、关键事件节点、关键改写点和 cutoff 后真相揭示点。
- 再按 chunk 生成聊天，每个 chunk 约 80-120 条消息。
- 每个 chunk 输入上一段 continuity summary，保持人物状态、称呼、节奏、未说出口的顾虑和关系温度连续。
- 每个 chunk 输出 QQChatExporter 兼容文本片段，最终人工或脚本拼接为 `conversation.txt`。
- 每段生成后校验消息总数、时间顺序、说话人名称、关键事件覆盖、cutoff 后事实位置和可解析性。

## 实施 TODO

- [ ] 为三段关系分别写出角色设定、表达风格、时间线跨度图和关键事件节点。
- [ ] 为每段至少设计 3 个关键可改写点，并记录 cutoff、原句和建议改写。
- [ ] 为每段至少设计 1 个 cutoff 后才揭示的关键事实，并标记为 modeler-only evidence。
- [ ] 分 chunk 生成每段 1000+ 条 QQChatExporter 兼容消息。
- [ ] 拼接并校验每段 `conversation.txt` 的 header、消息总数、时间范围和空行结构。
- [ ] 运行现有 `parse_qq_export()` 校验三段均可解析，且解析消息数不少于 1000。
- [ ] 导入三段语料并完成分析，确认每段至少能发起当前 `single_reply` 或 `short_thread` 推演。
- [ ] 补齐每段的 `timeline.md`、`rewrite-points.md`、`truth-after-cutoff.md` 和 `generation-notes.md`。

## 验收标准

- [ ] 三段 `conversation.txt` 都能被 `parse_qq_export()` 解析。
- [ ] 每段至少包含 1000 条消息。
- [ ] 每段至少包含 3 个关键可改写点。
- [ ] 每段至少包含 1 个 cutoff 后才揭示的关键事实。
- [ ] 每段标注能说明 cutoff 前判断与 modeler-only evidence 判断的差异。
- [ ] 每段至少能导入、分析、发起当前 `single_reply` 或 `short_thread` 推演。
- [ ] 不提交 API key；API key 只通过本地环境变量或运行时配置传入。
- [ ] 不使用真实姓名、真实学校、真实联系方式等可识别信息。

## 风险

- 合成语料可能过于规整，导致评估集无法暴露真实聊天的断裂、跳话题、重复和情绪噪声。
- LLM 分 chunk 生成可能出现人物设定漂移，需要 continuity summary 和人工校验兜底。
- 如果 cutoff 后真相写得太直白，后续 prompt 容易发生未来事实泄漏，需要在标注中明确 modeler-only evidence 边界。
- 3 段语料只能覆盖第一批代表场景，不能替代后续脱敏真实样例。
