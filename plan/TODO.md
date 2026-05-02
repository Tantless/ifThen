# TODO 总览

## 当前阶段

真实性提升已从原始问题分析拆成阶段性 TODO 文档。本阶段目标不是立刻重写完整系统，而是按依赖顺序逐步提升拟真性，同时尽量不增加完整分析流程耗时。

## 已完成

- [x] 分析时间、推理时间、用户等待时间降低（已完成 2026-05-01）
  - 已完成有界 LLM 并发、summary 失败取消、topic/persona/snapshot 分支并行、全局并发限制、结构化进度与 5000 条性能复测。
  - 5000 条完整分析总耗时较旧链路下降 52.51%。

## 真实性提升阶段性 TODO

建议按下面顺序执行。每个文档都是一个独立 TODO，可单独进入实现、测试和提交。

1. [真实性路线图](./realism-00-roadmap.md)
   - 汇总阶段目标、依赖顺序、交付边界和总验收标准。
2. [拟真性基线与失败样例集](./realism-01-baseline-and-evaluation.md)
   - 建立可复测样例，明确当前推演到底哪里不真实。
3. [分层证据上下文](./realism-02-layered-evidence-context.md)
   - 将 cutoff 前事实、未来原时间线证据、分支事实分开，避免未来泄漏。
4. [检索排序与上下文预算](./realism-03-retrieval-ranking-budget.md)
   - 在不增加主分析耗时的前提下，让推演拿到少而准的上下文。
5. [人格与表达风格增强](./realism-04-persona-style-enrichment.md)
   - 用现有 persona 加低成本统计，让回复更像真实对方。
6. [推演 Prompt 与泄漏护栏](./realism-05-prompt-guardrails.md)
   - 让未来事实只影响概率和风险，不进入角色台词。
7. [实时分支会话后端](./realism-06-realtime-branch-backend.md)
   - 建立用户扮演 self、LLM 只扮演 other 的持久分支会话。
8. [实时聊天前端交互](./realism-07-realtime-branch-frontend.md)
   - 实现输入窗口、串行回复、拆泡延迟和 typing 状态。
9. [质量验收与回归策略](./realism-08-quality-and-rollout.md)
   - 统一泄漏、persona、并发、兼容性和上线验收。

## 当前推荐执行顺序

第一批最小闭环：

- [ ] 完成 `realism-01`，拿到失败样例与评估标准。
- [ ] 完成 `realism-02`，让 context pack 支持分层证据。
- [ ] 完成 `realism-05`，把未来证据使用规则写进 prompt 和测试。

第二批增强真实性：

- [ ] 完成 `realism-03`，优化相关证据召回与预算。
- [ ] 完成 `realism-04`，补充表达风格统计和 persona 证据定位。

第三批升级产品形态：

- [ ] 完成 `realism-06`，新增实时分支会话后端。
- [ ] 完成 `realism-07`，新增实时分支会话前端体验。
- [ ] 完成 `realism-08`，沉淀验收脚本、回归用例和 rollout 策略。
