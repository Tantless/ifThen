# TODO 06：实时分支会话后端

## 问题

短链推演让模型同时续写 self 和 other，容易让 self 不像用户，也容易让对话为了完成轮次而变得不真实。用户明确希望改写后进入实时会话：用户扮演 self，LLM 只扮演 other。

本 TODO 已提升为真实性路线图的主要产品方向。旧 `single_reply` / `short_thread` 只作为迁移期兼容和回归入口保留。

## 目标

新增持久化实时分支会话后端能力，支持用户在反事实分支里继续发消息，并由 LLM 串行生成对方回复。

实时性目标：一次用户发送到进入 LLM 生成的热路径只做轻量数据库读取、会话状态拼装和必要的短检索；不要在每轮实时回复前追加重型全量 LLM 分析。

## 核心模型

建议新增：

- `BranchSession`
  - conversation_id
  - target_message_id
  - replacement_content
  - context_pack_snapshot
  - session_memory_pack
  - current_branch_state
  - input_revision
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
  - input_revision
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
  - 请求 LLM 生成 other 回复；如果已有运行中 job，则按“supersede”策略标记旧 job 过期。
- `GET /branch-sessions/{id}/reply-jobs`
  - 查询当前或历史回复任务。

## 串行规则

- 同一 branch session 同一时间只能有一个 running reply job。
- LLM 生成时必须读取最新 branch transcript。
- 如果用户在 LLM 运行中继续发消息，先保存消息并递增 `input_revision`。
- 如果旧 job 的回复还没有提交到 `BranchMessage`，旧 job 标记为 `superseded`，返回结果时必须丢弃。
- 新 reply job 使用“尚未被回复覆盖的 self 消息 + 完整分支 transcript + 当前 memory pack”重新生成 other 回复。
- 如果 old reply 已经开始逐条提交或前端已经展示，则不回滚已提交气泡，后续用户消息进入下一轮。
- 每个写入动作必须带 session 级 revision 校验，避免过期 LLM 结果写入当前分支。

## Persona 使用策略

- `persona_other` 是生成目标的主约束，控制 other 的语气、表达密度、回避/承接方式和关系推进上限。
- `persona_self` 仍然应进入 prompt，但权限低于用户实时输入；它用于帮助模型理解用户在历史中的表达习惯、对方通常如何理解 self，以及当前 self 消息是否显得突然。
- 用户实时输入是事实源，不能因为 `persona_self` 与输入不一致就改写或忽略用户刚发送的内容。

## 长期记忆热路径

- 创建 `BranchSession` 时预先生成或保存 `session_memory_pack`：target 附近 cutoff-safe history、base relationship snapshot、persona_other、persona_self、关键 topic digest、未来 modeler-only evidence 摘要。
- 每轮回复只拼接稳定 memory pack、最新 branch transcript、current_branch_state 和少量按需检索结果。
- branch transcript 超过预算后，保留最近 N 条原文，并把更早分支事实折叠进 `current_branch_state`。
- 未来原时间线事实只能作为 modeler-only evidence 影响概率、风险和保守程度，不能作为 other 在 cutoff 时已知的信息。

## 实施 TODO

- [ ] 新增数据库模型和迁移/初始化逻辑。
- [ ] 新增 schemas。
- [ ] 新增 API endpoint。
- [ ] 新增 worker job claim/processing 逻辑。
- [ ] 复用 `build_context_pack()` 和分层证据结构。
- [ ] 新增 realtime reply prompt，只生成 other 的一批消息，不生成 self。
- [ ] 将 `persona_other` 作为主约束、`persona_self` 作为理解 self 的辅助约束写入 prompt。
- [ ] 实现 `input_revision` 和 superseded job 丢弃逻辑。
- [ ] 每次 LLM 回复后更新 `current_branch_state`。
- [ ] 增加并发测试：同一 session 不允许两个 running job。
- [ ] 增加上下文测试：第二轮回复包含完整 branch transcript。
- [ ] 增加过期结果测试：用户在运行中追加消息后，旧 LLM 结果不能写入分支。

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
- [ ] 用户在 LLM 回复返回前追加 self 消息时，旧回复会被标记过期并基于合并后的 self 消息重新回复。
- [ ] 每轮生成使用最新 transcript 和分层 context。
- [ ] 旧 `/simulations` 入口不被破坏。

## 风险

- 新模型会扩大后端状态面，需要会话删除、重跑分析清理策略。
- 如果回复 job 与用户输入竞争，必须定义清楚队列行为。
- branch transcript 变长后需要摘要或窗口策略，避免 prompt 持续膨胀。
