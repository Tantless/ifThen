# Trace Summary

## 2026/05/03
- 完成 `realism-02` 分层证据上下文：新增 `src/if_then_mvp/context_builder.py` 统一 API/worker 的 context pack 装配，`src/if_then_mvp/retrieval.py` 输出 `cutoff_safe_facts`、`future_evidence_digests`、`branch_facts`、`evidence_policy`，并把 `src/if_then_mvp/branch_sessions.py` 的 realtime `session_memory_pack` 升级为显式 layered 结构且保留兼容投影；同时更新 retrieval、branch session、simulation 测试，`PYTHONPATH=src pytest -q` 共 104 项通过。
- 修复 `realism-02` memory pack review 问题：`src/if_then_mvp/branch_sessions.py` 将 `compatibility.cutoff_safe_context_pack` 收窄为 cutoff-safe 白名单投影，并在分支 session 创建、追加 self、提交 other 后刷新 `layered_context_pack.branch_facts.generated_branch_messages`；`src/if_then_mvp/worker.py` 在 realtime reply 写入后同步回刷持久化 memory pack；`tests/test_branch_sessions.py` 补充 future evidence 隔离和 branch facts 同步回归，`PYTHONPATH=src pytest -q` 104 项通过。
- 完成 `realism-03` 检索排序与上下文预算：`src/if_then_mvp/context_builder.py` 为 topic / future evidence 引入共享候选排序、预算裁剪与 trace 输出，`src/if_then_mvp/retrieval.py` 新增 `retrieval_trace` / `retrieval_budget` 元数据；`tests/test_retrieval.py`、`tests/test_simulations.py` 覆盖排序优先级、预算信息和无 topic link 的退化路径，`PYTHONPATH=src pytest -q` 107 项通过。
