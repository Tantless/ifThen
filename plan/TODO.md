# TODO 总览

## 当前阶段

真实性提升已从原始问题分析拆成阶段性 TODO 文档。本阶段目标不是立刻重写完整系统，而是按依赖顺序逐步提升拟真性，同时尽量不增加完整分析流程耗时。

2026-05-02 同步：实时分支会话升级为主要产品路径。旧的 `single_reply` / `short_thread` 只作为迁移期兼容与回归入口保留，不再作为最终体验目标。

## 已完成

- [x] 分析时间、推理时间、用户等待时间降低（已完成 2026-05-01）
  - 已完成有界 LLM 并发、summary 失败取消、topic/persona/snapshot 分支并行、全局并发限制、结构化进度与 5000 条性能复测。
  - 5000 条完整分析总耗时较旧链路下降 52.51%。
- [x] `realism-01-pre` 合成拟真长消息测试集（已完成 2026-05-02）
  - 已生成 3 段可导入、可解析、每段 1000+ 消息的合成 QQChatExporter 语料，并标注关键改写点与 cutoff 后 modeler-only evidence。
- [x] `realism-01` 拟真性基线与失败样例集（已完成 2026-05-02）
  - 已新增 12 个固定基线样例，覆盖 8 类失真类型，并用测试验证样例能回指到合成原语料。

## 真实性提升阶段性 TODO

建议按下面顺序执行。每个文档都是一个独立 TODO，可单独进入实现、测试和提交。

1. [真实性路线图](./realism-00-roadmap.md)
   - 汇总阶段目标、依赖顺序、交付边界和总验收标准。
2. [LLM 构筑拟真长消息测试集](./realism-01-pre-synthetic-corpus.md)
   - 已生成 3 段可导入的 1000+ 消息合成语料，为基线评估提供样本基础。
3. [拟真性基线与失败样例集](./realism-01-baseline-and-evaluation.md)
   - 已建立可复测样例，明确当前推演到底哪里不真实。
4. [分层证据上下文](./realism-02-layered-evidence-context.md)
   - 将 cutoff 前事实、未来原时间线证据、分支事实分开，避免未来泄漏。
5. [检索排序与上下文预算](./realism-03-retrieval-ranking-budget.md)
   - 在不增加主分析耗时的前提下，让推演拿到少而准的上下文。
6. [人格与表达风格增强](./realism-04-persona-style-enrichment.md)
   - 用现有 persona 加低成本统计，让回复更像真实对方。
7. [推演 Prompt 与泄漏护栏](./realism-05-prompt-guardrails.md)
   - 让未来事实只影响概率和风险，不进入角色台词。
8. [实时分支会话后端](./realism-06-realtime-branch-backend.md)
   - 建立用户扮演 self、LLM 只扮演 other 的持久分支会话；该项已提升为真实性主线，而不是后期附加体验。
9. [实时聊天前端交互](./realism-07-realtime-branch-frontend.md)
   - 实现输入窗口、运行中消息合并/旧回复丢弃、串行回复、拆泡延迟和 typing 状态。
10. [质量验收与回归策略](./realism-08-quality-and-rollout.md)
   - 统一泄漏、persona、并发、兼容性和上线验收。

## 当前推荐执行顺序

第一批实时最小闭环：

- [x] 完成 `realism-01-pre`，拿到 3 段可导入的合成拟真长消息测试集。
- [x] 完成 `realism-01`，拿到失败样例与评估标准。
- [ ] 完成 `realism-06` 的最小后端闭环，新增 branch session/message/reply job，并让 LLM 只回复 other。
- [ ] 完成 `realism-07` 的最小前端闭环，用户改写后进入实时分支聊天。
- [ ] 完成 `realism-05` 的实时版 prompt 护栏，禁止 LLM 生成 self 台词，并确保未来证据不进入角色台词。

第二批增强长期记忆真实性：

- [ ] 完成 `realism-02`，让 context pack 支持分层证据，并为实时分支提供会话级 memory pack。
- [ ] 完成 `realism-03`，优化相关证据召回与预算。
- [ ] 完成 `realism-04`，补充表达风格统计和 persona 证据定位。

第三批收敛质量与兼容：

- [ ] 完成 `realism-08`，沉淀验收脚本、回归用例和 rollout 策略。
