# realism-08 quality rollout

## Goal

为真实性路线图建立首版可执行质量门禁和 rollout 记录：用后端回归测试锁住分层证据、future evidence 泄漏、realtime branch 串行与旧入口兼容，并提供可关闭 future evidence 的 feature flag 和从短链入口切到实时分支入口的 rollout 文档。

## Requirements

- 建立后端 realism quality gate 测试，集中覆盖 context pack 分层合同、future evidence 与 cutoff-safe 隔离、assessment 风险字段、first reply 泄漏边界、realtime branch 串行 job、branch transcript 顺序和删除会话清理。
- 将固定拟真性 baseline 样例纳入质量门禁，至少验证 baseline 样例数量、失败类型覆盖和 future leakage 标注合同。
- 增加 `IF_THEN_ENABLE_FUTURE_EVIDENCE` 环境开关，默认启用；关闭时 context pack 不加载 future evidence，并给出明确 retrieval warning / budget 元数据。
- 增加 rollout 文档，记录短链兼容入口、实时分支主入口、future evidence 开关、必跑测试命令、人工验收标准和观测指标。
- 更新 `plan/realism-08-quality-and-rollout.md` 的自动测试矩阵和 rollout checklist，使路线图状态与实际回归测试一致。
- 保持外部 API、数据库 schema 与前端实现不变；前端自动化 E2E 不纳入本轮。

## Acceptance Criteria

- [x] 新增后端 quality gate 测试，并能作为 `PYTHONPATH=src pytest tests/test_realism_quality_gate.py -q` 单独运行。
- [x] 关闭 `IF_THEN_ENABLE_FUTURE_EVIDENCE` 后，`future_evidence_digests` 与相关 trace 为空，并保留 cutoff-safe topic digest 与旧入口兼容。
- [x] 固定 baseline 样例被 quality gate 引用，未来泄漏样例合同仍可检查。
- [x] Rollout 文档明确上线步骤、回滚开关、必跑测试、人工验收标准和观测指标。
- [x] `PYTHONPATH=src pytest -q` 通过。

## Definition of Done

- Tests added or updated for behavior changes.
- Rollout and PRD records document how to operate the new quality gate.
- Trace, PRDS, and task metadata are updated before commit.

## Technical Approach

- 在 `src/if_then_mvp/config.py` 增加布尔型 `enable_future_evidence` 设置，读取 `IF_THEN_ENABLE_FUTURE_EVIDENCE`，默认 `true`。
- 在 `src/if_then_mvp/context_builder.py` 的 `build_conversation_context_pack()` 中根据设置决定是否加载 future evidence；关闭时仍通过 `build_context_pack()` 输出稳定空列表、budget 与 warning。
- 新增 `tests/test_realism_quality_gate.py`，优先复用现有 public API、context builder、branch session worker 和 fixture 文件，不导入其他 test module 的私有 helper。
- 新增 `docs/realism-quality-rollout.md`，记录上线、回滚与验收命令。

## Decision (ADR-lite)

**Context**: 真实性路线图已完成证据分层、检索预算、persona/style 和 prompt 泄漏护栏，但这些能力分散在多组测试与计划文档里，缺少一个可被发布前直接运行的质量门禁。  
**Decision**: 首版 `realism-08` 聚焦后端可执行 quality gate、future evidence 环境开关和 rollout 文档，不在同一任务里引入前端 E2E 或新的 LLM 评估链路。  
**Consequences**: 发布前能用一个后端命令验证核心真实性合同，并能通过开关回滚 future evidence；前端 debounce/typing/retry 的深度自动化仍依赖现有 desktop test suite 与人工验收矩阵。

## Out of Scope

- 不新增前端 E2E、Playwright 或视觉测试。
- 不新增真实 LLM 批量评测链路。
- 不修改外部 API、数据库 schema 或 frontend runtime behavior。
- 不删除 `single_reply` / `short_thread` 兼容入口。

## Relevant Specs

- `.trellis/spec/shared/code-quality.md`: 保持测试可读、范围收敛，提交前运行验证。
- `.trellis/spec/guides/cross-layer-thinking-guide.md`: quality gate 跨 context pack、simulation prompt、branch session 和 worker。
- `.trellis/spec/guides/code-reuse-thinking-guide.md`: 测试应复用现有公开函数和 fixtures，避免复制大块业务逻辑。

## Files to Modify

- `src/if_then_mvp/config.py`: 增加 future evidence feature flag。
- `src/if_then_mvp/context_builder.py`: 应用 feature flag。
- `tests/test_realism_quality_gate.py`: 新增后端 quality gate。
- `docs/realism-quality-rollout.md`: 新增 rollout 文档。
- `plan/realism-08-quality-and-rollout.md`: 勾选已落地矩阵并记录命令。
- `PRDS/PRD009-质量验收.md`: 绑定终版 PRD 与工作记录。
