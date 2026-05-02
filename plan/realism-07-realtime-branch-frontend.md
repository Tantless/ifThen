# TODO 07：实时聊天前端交互

## 问题

当前前端展示的是完成后的推演结果。真实聊天体验需要用户连续发消息、等待对方输入、看到对方一条条短句发出，而不是等待一个完整短链结果一次性出现。

本 TODO 已提升为改写后的主体验。旧完成后展示短链的方式只在迁移期保留为兼容入口。

## 目标

新增实时分支会话 UI：用户改写历史消息后进入分支聊天，继续发送 self 消息；系统等待输入窗口后触发 LLM，LLM 的 other 回复按短句和延迟逐条展示。

## 交互规则

- 用户可以连续发送多条 self 消息。
- MVP 默认使用 1.5 到 2 秒 idle window：最后一条 self 消息后 1.5 到 2 秒无新消息再触发 LLM。
- LLM 回复期间显示 typing 状态。
- LLM 回复返回后，按短句拆成多条 other 气泡。
- 每条 other 气泡按文本长度设置发送延迟：
  - 极短：约 1 秒。
  - 中短句：约 2 秒。
  - 较长句：约 3 秒或拆分。
- LLM 未完成且 other 气泡尚未提交时，新用户消息保存并让旧 reply job 过期；下一次回复必须合并这些 self 消息一起回答。
- LLM 已开始展示 other 气泡后，新用户消息不回滚已展示内容，而是进入下一轮回复窗口。
- 分支消息视觉上必须区别于原时间线消息。

## UI 状态

- `idle`：用户可输入，暂无待回复。
- `collecting_user_window`：用户刚发送，等待 idle window。
- `reply_queued`：回复任务已排队。
- `other_typing`：LLM 正在生成。
- `reply_superseded`：运行中回复已因新 self 消息过期，等待新一轮。
- `delivering_reply`：LLM 已返回，正在逐条展示。
- `error`：回复失败，可重试。

## 实施 TODO

- [ ] 增加 branch session service。
- [ ] 增加 branch session 状态管理。
- [ ] 在改写完成后提供进入实时分支会话的入口。
- [ ] 实现用户消息本地乐观展示和后端持久化。
- [ ] 实现 idle window debounce，MVP 默认 1.5 到 2 秒；如果后续人工验收认为过短，再改为可配置。
- [ ] 实现 reply job polling。
- [ ] 实现 other typing 状态。
- [ ] 实现回复拆泡和延迟展示。
- [ ] 实现运行中禁止并行触发 LLM，并在新 self 消息到来时标记旧回复过期。
- [ ] 用 session/input revision 防止过期回复进入 UI。
- [ ] 增加失败重试与错误展示。

## 可能涉及文件

- `desktop/src/App.tsx`
- `desktop/src/types/api.ts`
- `desktop/src/types/desktop.ts`
- `desktop/src/lib/services/*`
- `desktop/src/lib/frontUiAdapters.ts`
- `desktop/src/frontui/ChatWindow.tsx`
- `desktop/tests/visualShell.test.tsx`
- `desktop/tests/frontUiAdapters.test.ts`

## 验收标准

- [ ] 用户改写后可以进入实时分支会话。
- [ ] 用户连续发送多条消息时，只在 idle window 后触发一次 LLM。
- [ ] LLM 回复期间不会并行触发第二个有效回复任务。
- [ ] LLM 未返回前用户追加消息时，最终只展示基于合并后 self 消息生成的 other 回复。
- [ ] other 回复会按短句逐条出现。
- [ ] typing 和失败状态可见。
- [ ] 原有 short-thread 展示仍可用。

## 风险

- 前端状态机会比当前 rewrite draft 更复杂，需要避免把原聊天态和分支聊天态混在一起。
- 延迟展示要能被测试稳定控制，避免 flaky 测试。
- 如果用户切换会话或关闭窗口，需要定义未完成任务的恢复显示策略。
