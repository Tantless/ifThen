# Fix realism-02 memory pack review findings

## Goal

修复 `realism-02` 分层 memory pack 的两个 review 问题，保证：

- cutoff-safe 兼容投影不再重新引入 future evidence；
- realtime branch session 持久化的 `branch_facts.generated_branch_messages` 始终与已提交分支消息同步。

## Requirements

- `compatibility.cutoff_safe_context_pack` 只能保留 cutoff-safe 兼容字段，不能包含 `future_evidence_digests`、`branch_facts`、`evidence_policy`。
- branch session 创建后和后续每次提交分支消息后，都要刷新 `session_memory_pack.layered_context_pack.branch_facts.generated_branch_messages`。
- realtime reply worker 在写入新的 `other` 消息后必须同步刷新持久化 memory pack。
- 为以上两个问题补充回归测试，并保持现有 `realism-02` 路径兼容。

## Acceptance Criteria

- [x] 新创建的 branch session 中，`compatibility.cutoff_safe_context_pack` 不再包含 future evidence 或 branch-only 字段。
- [x] 首次 `other` 回复提交后，持久化 `generated_branch_messages` 已包含最新 committed 分支消息。
- [x] 第二轮及以后分支对话继续推进时，持久化 `generated_branch_messages` 仍与实际 transcript 保持一致。
- [x] `PYTHONPATH=src pytest -q` 通过。

## Technical Notes

- 在 `src/if_then_mvp/branch_sessions.py` 中新增 cutoff-safe 兼容投影构造与 branch facts 刷新 helper。
- 在 `src/if_then_mvp/worker.py` 中于写入 `other` 回复后回刷 session memory pack。
- 在 `tests/test_branch_sessions.py` 中增加 future evidence 隔离与 branch facts 同步断言。
