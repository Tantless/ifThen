# TODO 00：真实性提升路线图

## 背景

当前项目已经完成“导入聊天记录 -> 分析 -> 改写 -> 反事实推演 -> 桌面展示”的闭环，也已经完成分析性能优化。下一阶段的主要矛盾是：我们要更充分地利用全量聊天历史里体现的人格、偏好、关系约束，但又不能破坏反事实推演的 cutoff-safe 原则。

核心目标：在尽量不增加完整分析耗时的前提下，提高推演和实时会话的拟真性。

## 总原则

- 不把未来原时间线事实当成角色在 cutoff 时已经知道的事实。
- 不新增重型全量 LLM 分析阶段作为第一选择。
- 优先复用现有 messages、segment summaries、topics、persona profiles、relationship snapshots。
- 推演阶段允许做按需检索、排序、预算控制和 prompt 约束。
- 真实感优先来自：证据分层、检索准确、persona 可执行、用户参与实时分支会话。

## 阶段拆分

### 阶段 0：前置合成语料

- `realism-01-pre-synthetic-corpus.md`

目标：先生成可提交、可导入、可标注的合成拟真长消息测试集，避免在没有样本基础时直接进入评估集建设。

### 阶段 1：评估与证据边界

- `realism-01-baseline-and-evaluation.md`
- `realism-02-layered-evidence-context.md`
- `realism-05-prompt-guardrails.md`

目标：基于前置合成语料先证明当前哪里不真实，并建立“未来证据可用于建模、不可用于角色台词”的硬合同。

### 阶段 2：检索与人格增强

- `realism-03-retrieval-ranking-budget.md`
- `realism-04-persona-style-enrichment.md`

目标：在不明显增加分析耗时的前提下，让模型拿到更完整、更相关、更像本人的约束。

### 阶段 3：实时分支会话

- `realism-06-realtime-branch-backend.md`
- `realism-07-realtime-branch-frontend.md`

目标：把短链自动推演升级为用户真实参与的分支会话，LLM 只扮演对方，避免模型同时代写双方导致失真。

### 阶段 4：验收与上线

- `realism-08-quality-and-rollout.md`

目标：用固定样例、自动测试和人工验收标准防止真实性退化、未来泄漏和并发错乱。

## 总验收标准

- [ ] 生成 3 段每段 1000+ 条消息、可导入、含标注的合成拟真长消息测试集。
- [ ] 未来事实不会作为角色已知信息直接出现在回复中。
- [ ] 未来事实可以影响 branch assessment 的风险、置信度和保守程度。
- [ ] 推演输出更少出现过度乐观、过度成熟、过度会沟通的回复。
- [ ] 检索上下文能解释模型为什么应该保守、推进或收束。
- [ ] 不显著增加完整分析 pipeline 耗时。
- [ ] `single_reply` / `short_thread` 旧入口在迁移期仍可用。
- [ ] 实时分支会话中同一会话只允许一个 LLM 回复任务运行。

## 建议 PR 顺序

1. PR1-pre：构筑合成拟真长消息测试集。
2. PR1：建立评估样例和当前失败分类。
3. PR2：扩展 context pack，加入分层证据结构。
4. PR3：修改 prompt，加入未来证据使用和泄漏护栏。
5. PR4：实现检索排序和上下文预算。
6. PR5：加入 persona/style 低成本统计。
7. PR6：新增实时分支会话后端模型和接口。
8. PR7：新增实时分支会话前端体验。
9. PR8：补齐质量验收、回归脚本和 rollout 文档。

## 不做

- 不在第一阶段引入 embedding 基础设施。
- 不让未来原时间线事实进入角色台词。
- 不让实时分支会话中的多个 LLM 回复并行生成。
- 不为了拟真性重跑一套昂贵的全量 LLM 分析链路。
