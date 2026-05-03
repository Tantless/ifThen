# realism-05 prompt guardrails

## Goal

在已有分层证据、检索预算和 persona/style 约束基础上，补齐 simulation 与 realtime branch 的 prompt 级泄漏护栏，确保 cutoff 后的 future evidence 只能影响风险、概率、置信度和表达保守程度，不能进入角色台词或被暗示为角色已知事实。

## Requirements

- 在 branch assessment prompt 中显式区分 `character-known cutoff-safe facts`、`modeler-only future evidence` 和 `branch-only facts`。
- assessment 可以使用 future evidence 调整 `branch_direction`、`state_shift_summary`、`risk_flags`、`confidence` 与保守程度，但不能把 future evidence 写成角色已知事实。
- 扩展 assessment payload 字段说明，使结果可以记录 modeler-only 风险来源和泄漏边界。
- 在 first reply prompt 中加入禁止泄漏规则：不得引用、复述或暗示 cutoff 后才发生的拒绝、偏好、解释或关系状态。
- 在 next turn 与 realtime branch reply prompt 中明确 branch transcript 优先，future evidence 只作为人格稳定和风险约束，不作为必然剧情或分支事实。
- 保持 `single_reply` / `short_thread` / realtime branch 现有入口兼容，不新增外部 API，不新增存储表，不新增 LLM 分析阶段。

## Acceptance Criteria

- [x] prompt 明确区分 character-known、modeler-only 和 branch-only 三类证据。
- [x] assessment schema/prompt 能表达 modeler-only 风险来源，并要求这些来源不得进入角色台词。
- [x] first reply prompt 和 next turn/realtime prompt 都包含 future evidence 泄漏禁止规则。
- [x] 测试覆盖 future evidence 中出现明确拒绝或偏好时，prompt 允许 assessment 更保守，但回复 prompt 不允许直接引用未来事实。
- [x] 没有 future evidence 时，旧 `single_reply` / `short_thread` prompt 行为保持兼容。
- [x] `PYTHONPATH=src pytest tests/test_simulations.py tests/test_branch_sessions.py -q` 通过。
- [x] `PYTHONPATH=src pytest -q` 通过。

## Definition of Done

- Tests added or updated where prompt behavior changes.
- Prompt contracts and assessment payload changes stay centralized in `src/if_then_mvp/simulation.py`.
- Trace, PRDS, and task metadata are updated so需求、实现和交付记录可追溯。

## Technical Approach

- 复用 `context_pack["evidence_policy"]`、`future_evidence_digests`、`branch_facts`、`retrieval_trace` 和 `persona_other.deterministic_style_profile`，不新增 context builder 字段。
- 在 `_build_branch_prompt()` 中加入 evidence boundary section 和 modeler-only risk reporting instructions。
- 在 `_build_first_reply_prompt()` 中加入 character-known boundary、future evidence leakage ban 和表达强度约束。
- 在 `_build_next_turn_prompt()` 与 `_build_realtime_branch_reply_prompt()` 中加入 branch facts 优先规则，禁止把原时间线后续事件搬入分支。
- 通过 prompt 字符串单元测试锁住关键合同，不依赖真实 LLM 输出做断言。

## Decision (ADR-lite)

**Context**: `realism-02` 已把证据分为 cutoff-safe、future evidence 和 branch facts，`realism-03` 已控制检索排序与预算，`realism-04` 已加入 style profile；但生成 prompt 仍需要更明确的行为边界，避免模型把 modeler-only future evidence 泄漏成角色台词。  
**Decision**: 在现有 prompt builder 内补充明确证据边界和 assessment 风险来源字段说明，首版只修改 prompt 合同与测试，不新增后处理器或持久化模型。  
**Consequences**: 回复生成会获得更强的泄漏护栏，并能在 assessment 中保守使用未来证据；风险是 prompt 变长，因此本轮只加入可直接验收的短规则。

## Out of Scope

- 不新增 LLM 后处理审核器或二次重写链路。
- 不修改 frontend 展示协议或 branch session 外部 API。
- 不引入 embedding、reranker 或新的 future evidence 来源。
- 不把 future evidence 变成确定剧情，只作为风险和人格稳定约束。

## Relevant Specs

- `.trellis/spec/shared/code-quality.md`: 保持改动范围收敛，测试覆盖行为变化。
- `.trellis/spec/shared/git-conventions.md`: 完成后使用规范原子提交。
- `.trellis/spec/guides/cross-layer-thinking-guide.md`: prompt 消费的证据分层合同跨 context pack、simulation 和 worker/realtime branch 边界。
- `.trellis/spec/guides/code-reuse-thinking-guide.md`: prompt 护栏应集中在 `simulation.py` 的现有 builder 中，避免多处重复文案漂移。

## Files to Modify

- `src/if_then_mvp/simulation.py`: 更新 assessment、first reply、next turn 和 realtime branch reply prompt，并扩展 assessment payload 字段说明。
- `tests/test_simulations.py`: 增加 future evidence 泄漏边界和兼容性回归。
- `tests/test_branch_sessions.py`: 必要时补 realtime branch reply prompt 护栏回归。
- `PRDS/PRD008-提示词护栏.md`: 绑定终版 PRD 与工作记录。
