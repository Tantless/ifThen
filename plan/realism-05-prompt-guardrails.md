# TODO 05：推演 Prompt 与泄漏护栏

## 问题

分层证据只有进入 prompt 后才真正影响推演。最关键的风险是：模型看到 future evidence 后，把它写成角色在 cutoff 当下知道的信息，造成未来泄漏。

## 目标

更新 branch assessment、first reply、next turn prompt，让模型遵守：

- cutoff-safe facts 可以作为角色已知事实。
- future evidence 只能影响概率、风险、置信度、保守程度。
- future evidence 不能被角色引用、复述、暗示成已知事实。
- branch facts 只能来自当前反事实分支 transcript。

## Prompt 合同

### branch assessment

- 可以读取 future evidence。
- 应根据 future evidence 调整：
  - `branch_direction`
  - `state_shift_summary`
  - `risk_flags`
  - `confidence`
- 不生成具体台词。
- 必须说明风险是否来自 modeler-only evidence，但不能让角色知道。

### first reply

- 可以被 future evidence 约束表达强度。
- 不能说出 cutoff 后才发生的事实。
- 如果 future evidence 显示对方长期不接受某类推进，回复应更保守、更有限。

### next turn / realtime reply

- 只能基于 branch transcript 继续。
- 不能把原时间线后续事件强行搬进分支。
- 如果用户在分支里改变了走向，future evidence 只作为人格稳定约束，不作为必然剧情。

## 实施 TODO

- [ ] 在 `_build_branch_prompt()` 中加入分层证据说明和 future evidence 使用规则。
- [ ] 在 `_build_first_reply_prompt()` 中加入禁止泄漏规则和表达强度约束。
- [ ] 在 `_build_next_turn_prompt()` 中加入 branch facts 与 future evidence 的边界。
- [ ] 修改 Pydantic payload 或字段说明，使 assessment 能记录 modeler-only 风险来源。
- [ ] 增加测试：future evidence 中出现明确拒绝，assessment 更保守，但 first reply 不直接引用未来拒绝内容。
- [ ] 增加测试：future evidence 中出现对方偏好，回复不得说“我后来告诉过你我喜欢……”
- [ ] 增加测试：没有 future evidence 时旧 prompt 行为保持兼容。

## 可能涉及文件

- `src/if_then_mvp/simulation.py`
- `tests/test_simulations.py`
- `tests/test_worker.py`

## 验收标准

- [ ] prompt 明确区分 character-known 与 modeler-only。
- [ ] 单元测试覆盖 future evidence 泄漏边界。
- [ ] assessment 可以更保守地判断高风险改写。
- [ ] first reply 和 next turn 不直接输出未来事实。
- [ ] 原 `single_reply` / `short_thread` 测试继续通过。

## 风险

- prompt 太长会增加推演延迟。
- 约束过强可能让模型过度保守，所有分支都失败。
- 需要避免把 future evidence 变成确定命运；它只是证据，不是分支必然结果。
