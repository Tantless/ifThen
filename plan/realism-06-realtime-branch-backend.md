# TODO 06：实时分支会话后端

## 问题

短链推演让模型同时续写 self 和 other，容易让 self 不像用户，也容易让对话为了完成轮次而变得不真实。用户明确希望改写后进入实时会话：用户扮演 self，LLM 只扮演 other。

## 目标

新增持久化实时分支会话后端能力，支持用户在反事实分支里继续发消息，并由 LLM 串行生成对方回复。

## 核心模型

建议新增：

- `BranchSession`
  - conversation_id
  - target_message_id
  - replacement_content
  - context_pack_snapshot
  - current_branch_state
  - status
  - created_at / updated_at
- `BranchMessage`
  - branch_session_id
  - sequence_no
  - speaker_role
  - content_text
  - source
  - delivery_state
  - metadata_json
- `BranchReplyJob`
  - branch_session_id
  - status
  - current_stage
  - payload_json
  - error_message
  - started_at / finished_at

## 接口草案

- `POST /branch-sessions`
  - 创建分支会话，保存改写消息和 context pack。
- `GET /branch-sessions/{id}`
  - 读取会话、消息、状态。
- `POST /branch-sessions/{id}/messages`
  - 追加用户 self 消息。
- `POST /branch-sessions/{id}/reply-jobs`
  - 请求 LLM 生成 other 回复；如果已有运行中 job，则返回 409 或复用队列策略。
- `GET /branch-sessions/{id}/reply-jobs`
  - 查询当前或历史回复任务。

## 串行规则

- 同一 branch session 同一时间只能有一个 running reply job。
- LLM 生成时必须读取最新 branch transcript。
- 如果用户在 LLM 运行中继续发消息，先保存消息，但不启动第二个并行 LLM。
- 当前 job 完成后，下一次 idle window 再触发新 job。

## 实施 TODO

- [ ] 新增数据库模型和迁移/初始化逻辑。
- [ ] 新增 schemas。
- [ ] 新增 API endpoint。
- [ ] 新增 worker job claim/processing 逻辑。
- [ ] 复用 `build_context_pack()` 和分层证据结构。
- [ ] 新增 realtime reply prompt，只生成 other 的一批消息。
- [ ] 每次 LLM 回复后更新 `current_branch_state`。
- [ ] 增加并发测试：同一 session 不允许两个 running job。
- [ ] 增加上下文测试：第二轮回复包含完整 branch transcript。

## 可能涉及文件

- `src/if_then_mvp/models.py`
- `src/if_then_mvp/schemas.py`
- `src/if_then_mvp/api.py`
- `src/if_then_mvp/worker.py`
- `src/if_then_mvp/simulation.py`
- `src/if_then_mvp/retrieval.py`
- `tests/test_simulations.py`
- `tests/test_worker.py`

## 验收标准

- [ ] 可以创建 branch session。
- [ ] 用户 self 消息可以持久化追加。
- [ ] LLM 只生成 other 消息。
- [ ] 同一 session 回复任务严格串行。
- [ ] 每轮生成使用最新 transcript 和分层 context。
- [ ] 旧 `/simulations` 入口不被破坏。

## 风险

- 新模型会扩大后端状态面，需要会话删除、重跑分析清理策略。
- 如果回复 job 与用户输入竞争，必须定义清楚队列行为。
- branch transcript 变长后需要摘要或窗口策略，避免 prompt 持续膨胀。
