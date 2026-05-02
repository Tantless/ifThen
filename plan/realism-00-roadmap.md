# TODO 00：真实性提升路线图

## 背景

当前项目已经完成“导入聊天记录 -> 分析 -> 改写 -> 反事实推演 -> 桌面展示”的闭环，也已经完成分析性能优化。下一阶段的主要矛盾是：我们要更充分地利用全量聊天历史里体现的人格、偏好、关系约束，但又不能破坏反事实推演的 cutoff-safe 原则。

2026-05-02 方向更新：真实性主线从“模型自动续写短链”转向“实时分支对话”。用户改写历史消息后继续扮演 self，LLM 只扮演 other；旧 `single_reply` / `short_thread` 保留为兼容入口，不再作为主要产品体验。

核心目标：在尽量不增加完整分析耗时的前提下，提高推演和实时会话的拟真性。

## 总原则

- 不把未来原时间线事实当成角色在 cutoff 时已经知道的事实。
- 不新增重型全量 LLM 分析阶段作为第一选择。
- 优先复用现有 messages、segment summaries、topics、persona profiles、relationship snapshots。
- 推演阶段允许做按需检索、排序、预算控制和 prompt 约束。
- 真实感优先来自：证据分层、检索准确、persona 可执行、用户参与实时分支会话。
- 实时分支对话优先于多轮自动推演；LLM 不再代写用户后续 self 消息。

## 阶段拆分

### 阶段 0：前置合成语料

- `realism-01-pre-synthetic-corpus.md`

目标：先生成可提交、可导入、可标注的合成拟真长消息测试集，避免在没有样本基础时直接进入评估集建设。

### 阶段 1：评估与产品主线切换

- `realism-01-baseline-and-evaluation.md`
- `realism-06-realtime-branch-backend.md`
- `realism-07-realtime-branch-frontend.md`

目标：先用固定样例描述当前失真，然后把改写后的主体验切到实时分支会话，避免 LLM 同时扮演双方造成的核心失真。

### 阶段 2：证据边界与泄漏护栏

- `realism-02-layered-evidence-context.md`
- `realism-05-prompt-guardrails.md`

目标：为实时分支会话建立“cutoff 前角色可知、cutoff 后 modeler-only、分支内新事实”的硬合同。

### 阶段 3：检索与人格增强

- `realism-03-retrieval-ranking-budget.md`
- `realism-04-persona-style-enrichment.md`

目标：在不明显增加分析耗时的前提下，让模型拿到更完整、更相关、更像本人的约束。

### 阶段 4：验收与上线

- `realism-08-quality-and-rollout.md`

目标：用固定样例、自动测试和人工验收标准防止真实性退化、未来泄漏和并发错乱。

## 总验收标准

- [x] 生成 3 段每段 1000+ 条消息、可导入、含标注的合成拟真长消息测试集。
- [x] 建立 10+ 个固定拟真性基线样例，并覆盖当前主要失败分类。
- [ ] 未来事实不会作为角色已知信息直接出现在回复中。
- [ ] 未来事实可以影响 branch assessment 的风险、置信度和保守程度。
- [ ] 推演输出更少出现过度乐观、过度成熟、过度会沟通的回复。
- [ ] 检索上下文能解释模型为什么应该保守、推进或收束。
- [ ] 不显著增加完整分析 pipeline 耗时。
- [ ] `single_reply` / `short_thread` 旧入口在迁移期仍可用。
- [ ] 实时分支会话成为改写后的主入口，LLM 只生成 other 消息。
- [ ] 实时分支会话中同一会话只允许一个 LLM 回复任务运行。

## 建议 PR 顺序

1. PR1-pre：构筑合成拟真长消息测试集。（已完成）
2. PR1：建立评估样例和当前失败分类。（已完成）
3. PR2：新增实时分支会话后端模型和接口。
4. PR3：新增实时分支会话前端体验。
5. PR4：扩展 context pack，加入分层证据结构和会话级 memory pack。
6. PR5：修改 prompt，加入未来证据使用、只生成 other、运行中消息合并的护栏。
7. PR6：实现检索排序和上下文预算。
8. PR7：加入 persona/style 低成本统计。
9. PR8：补齐质量验收、回归脚本和 rollout 文档。

## 不做

- 不在第一阶段引入 embedding 基础设施。
- 不让未来原时间线事实进入角色台词。
- 不让实时分支会话中的多个 LLM 回复并行生成。
- 不为了拟真性重跑一套昂贵的全量 LLM 分析链路。
- 不把 `short_thread` 继续作为主体验扩展。
