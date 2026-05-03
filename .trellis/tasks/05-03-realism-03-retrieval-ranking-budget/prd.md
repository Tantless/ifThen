# implement realism-03 retrieval ranking and context budget

## Goal

在现有 `realism-02` 分层证据合同之上，补齐第一版结构化检索排序与上下文预算，让 simulation / realtime branch 共用的 context pack 在固定预算内优先保留最相关、最能约束回复的证据。

## Requirements

- 为 `related_topic_digests` 和 `future_evidence_digests` 建立统一的候选排序逻辑，首版使用确定性信号：目标段 topic 重合、敏感度、时间接近度、稳定性。
- 为 context pack 增加显式预算控制：`current_segment_history` 始终保留，`same_day_prior_segments` 最多 1 条，`related_topic_digests` 最多 3 条，`future_evidence_digests` 最多 3 条。
- 为 context pack 输出 `retrieval_trace` 与 `retrieval_budget`，记录每类证据的预算、选中结果和主要命中原因。
- 当没有可用 topic link 时，系统仍需保留基于时间邻近的 `same_day_prior_segments` 和 cutoff-safe `base_relationship_snapshot`，不能因排序逻辑回退成空上下文。
- 保持现有 simulation / realtime branch 消费路径兼容，不修改 prompt 字段合同，不重新引入 future leakage。

## Acceptance Criteria

- [ ] `build_conversation_context_pack()` 生成的 `related_topic_digests` / `future_evidence_digests` 数量受预算约束。
- [ ] 同一敏感 topic 下的 future 拒绝/边界证据，排序优先级高于无关日常 future 闲聊。
- [ ] `context_pack` 新增 `retrieval_trace` 和 `retrieval_budget`，并能解释为什么选中当前证据。
- [ ] 没有 topic link 时，context pack 仍保留 `same_day_prior_segments` 与 `base_relationship_snapshot`，不会只剩空的 topic 结果。
- [ ] `PYTHONPATH=src pytest tests/test_retrieval.py tests/test_simulations.py -q` 通过。
- [ ] `PYTHONPATH=src pytest -q` 通过。

## Definition of Done

- Tests added or updated where behavior changes.
- Lint / typecheck / relevant test suites pass.
- Docs or Trellis notes updated if the retrieval contract changes.

## Technical Approach

- 在 `src/if_then_mvp/context_builder.py` 中集中实现候选收集、排序和预算裁剪，避免 API / worker / branch session 各自维护不同的检索逻辑。
- 保持 `src/if_then_mvp/retrieval.py` 负责 context pack 打包，同时为其增加 `retrieval_trace` / `retrieval_budget` 输出。
- 首版不引入 embedding，不新增 LLM 分析产物，只复用 `Topic`、`TopicLink`、`SegmentSummary`、`RelationshipSnapshot` 现有字段。

## Decision (ADR-lite)

**Context**: `realism-03` 的路线图目标是“少而准”的证据选择，但当前实现仍按简单顺序把 topic / future evidence 塞进 context pack，缺乏预算和可解释排序。  
**Decision**: 先做一版确定性结构化排序，只覆盖现有 context pack 的 topic / future evidence 选择，并把解释信息写进 `retrieval_trace`。  
**Consequences**: 可以在不引入新基础设施的情况下收敛 context 大小和相关性，但 prompt 还不会直接消费 `retrieval_trace`，更进一步的人格/guardrail 强化仍留给后续 `realism-04/05`。

## Out of Scope

- 不引入 embedding 或向量索引。
- 不重写 simulation / branch prompt 文案。
- 不新增全量分析阶段或新的持久化模型。
- 不修改 `single_reply` / `short_thread` 的外部 API 合同。

## Technical Notes

## Relevant Specs

- `.trellis/spec/shared/code-quality.md`: 约束改动保持类型安全、避免隐式兜底和无关重构。
- `.trellis/spec/shared/typescript.md`: 虽然本任务是 Python 后端，但共享规则仍要求接口合同显式、不要引入模糊类型思路。
- `.trellis/spec/shared/git-conventions.md`: 任务完成后提交需保持原子性和规范信息。
- `.trellis/spec/guides/cross-layer-thinking-guide.md`: context pack 同时被 API、worker、branch session 消费，需要把输出合同当作跨层边界处理。
- `.trellis/spec/guides/code-reuse-thinking-guide.md`: 检索排序逻辑要收敛到 `context_builder.py`，避免在多条路径复制。

## Code Patterns Found

- `src/if_then_mvp/context_builder.py`: 已经是 simulation / branch 共享的 context pack 装配入口，适合承接检索排序与预算。
- `src/if_then_mvp/retrieval.py`: 当前只负责 cutoff-safe 组装和 layered contract 打包，适合新增 trace / budget 元数据输出。
- `src/if_then_mvp/branch_sessions.py`: realtime branch memory pack 直接依赖 `context_pack_snapshot`，说明新增上下文字段应保持向后兼容。

## Files to Modify

- `src/if_then_mvp/context_builder.py`: 增加候选排序、预算裁剪和 fallback 选择。
- `src/if_then_mvp/retrieval.py`: 输出 `retrieval_trace` / `retrieval_budget` 并保留现有字段兼容。
- `tests/test_retrieval.py`: 补预算、排序解释和 fallback 回归。
- `tests/test_simulations.py`: 通过真实 DB 装配路径验证 ranking/budget 在共享 context builder 上生效。
