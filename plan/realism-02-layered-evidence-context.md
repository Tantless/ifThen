# TODO 02：分层证据上下文

## 问题

当前推演上下文严格只使用 cutoff 前证据，因此安全但不完整。用户指出：原时间线 cutoff 后发生的客观事实同样反映人物人格和关系约束，完全不用会导致模型过度乐观或判断失真。

难点是：未来原时间线事实可以帮助建模，但绝不能成为角色在当时已知的信息。

## 目标

扩展 simulation context pack，把证据明确分层：

- `cutoff_safe_facts`：cutoff 前，角色可知，可直接影响回复。
- `future_evidence_digests`：cutoff 后，模型可用来判断稳定人格、偏好、风险，不可被角色引用。
- `branch_facts`：改写后新分支内已经生成的事实，只属于反事实分支。

## 设计原则

- 分层在数据结构上显式存在，不只靠 prompt 口头约束。
- future evidence 必须带来源、时间位置、证据类型和禁止引用标记。
- 旧的 cutoff-safe 检索逻辑保持兼容。
- 第一版只用已有 segment summary、topic、snapshot，不新增全量 LLM 分析。

## 实施 TODO

- [ ] 为 context pack 设计字段：
  - `cutoff_safe_facts`
  - `future_evidence_digests`
  - `branch_facts`
  - `evidence_policy`
- [ ] 在 `build_context_pack()` 中保留现有字段，并新增分层字段。
- [ ] 新增 future evidence 加载函数，从 cutoff 后的 segment summary、topic link、relationship snapshot 中组装摘要。
- [ ] 每条 future evidence 至少包含：
  - `source_type`
  - `source_id`
  - `starts_at` / `ends_at`
  - `evidence_kind`
  - `summary`
  - `use_policy = modeler_only_not_character_known`
- [ ] 控制 future evidence 数量，第一版最多 3-5 条。
- [ ] 在 simulation 持久化的 `context_pack_snapshot` 中保存分层后的上下文，便于排查。
- [ ] 保持没有 future evidence 时旧推演路径仍能运行。

## 可能涉及文件

- `src/if_then_mvp/retrieval.py`
- `src/if_then_mvp/worker.py`
- `src/if_then_mvp/simulation.py`
- `tests/test_simulations.py`
- `tests/test_worker.py`

## 验收标准

- [ ] cutoff 前证据和 cutoff 后证据在 context pack 中分开。
- [ ] future evidence 不影响旧字段的兼容性。
- [ ] 当目标消息之后存在相关 segment/topic/snapshot 时，context pack 能返回 future evidence。
- [ ] 当目标消息接近会话末尾时，future evidence 可以为空且推演不报错。
- [ ] 测试覆盖：future evidence 不会混入 `related_topic_digests` 这类角色可知字段。

## 风险

- 字段命名模糊会让后续 prompt 误用未来证据。
- future evidence 太多会增加推演 token 和响应时间。
- 如果 future evidence 检索过宽，模型会被不相关后续事件带偏。

## 不做

- 不在本 TODO 中引入 embedding。
- 不修改数据库 schema，除非 context pack snapshot 无法承载。
- 不让 future evidence 直接改变原始 analysis 产物。
