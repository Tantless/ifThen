# TODO 03：检索排序与上下文预算

## 问题

即使有分层证据，如果检索内容过多、过远或不相关，推演会变慢，也会更容易跑偏。拟真性的关键不是塞入更多摘要，而是让模型拿到少而准的证据。

## 目标

建立一套结构化检索排序和预算策略，让 context pack 在固定 token/条目预算下优先包含最能约束当前改写的证据。

## 排序信号

- topic 重合度：目标消息所在 segment 与候选证据是否属于同一 topic。
- 敏感度：是否涉及关系试探、告白、冲突、拒绝、边界、冷淡、修复。
- 时间距离：cutoff 前最近证据优先；future evidence 中强约束事件优先于普通日常。
- 关系状态相关性：候选 snapshot 是否体现 tension、openness、defensiveness 的明显变化。
- 稳定性：多段重复出现的倾向优先于单次偶发。
- 角色相关性：是否直接体现 other 的偏好、表达习惯、拒绝/承接模式。

## 上下文预算建议

- 当前 segment 原文：最高优先级，不随预算被挤掉。
- cutoff 前关系状态：保留最近 snapshot。
- cutoff 前相关 topic：最多 3 条。
- future evidence：最多 3-5 条，且必须 modeler-only。
- persona/style：压缩成可执行约束，不放长篇分析。
- branch transcript：实时会话阶段按最近 N 条 + 摘要策略处理。

## 实施 TODO

- [ ] 把 topic/snapshot/segment 候选证据组装成统一候选结构。
- [ ] 为候选证据计算 ranking score。
- [ ] 按证据类型设置硬上限，避免某一类证据挤掉其他证据。
- [ ] 为 context pack 输出 `retrieval_trace`，记录为什么选中每条证据。
- [ ] 增加测试：同一敏感 topic 的后续拒绝证据应高于无关日常证据。
- [ ] 增加测试：普通未来闲聊不应挤掉 cutoff 前当前段上下文。
- [ ] 增加测试：没有 topic link 时，系统能退化为时间邻近和 snapshot 检索。

## 可能涉及文件

- `src/if_then_mvp/retrieval.py`
- `src/if_then_mvp/worker.py`
- `tests/test_simulations.py`

## 验收标准

- [ ] context pack 中每类证据数量受控。
- [ ] 选中证据带有可解释的 `retrieval_trace`。
- [ ] 推演请求不会因为有大量历史摘要而线性膨胀。
- [ ] 与目标敏感主题高度相关的 future evidence 能被召回。
- [ ] 无关未来证据不会进入 prompt。

## 后续增强

- 只有当结构化检索召回不足时，再考虑 embedding。
- embedding 如进入后续阶段，应异步索引、可重建、可关闭，不阻塞完整分析主链路。
