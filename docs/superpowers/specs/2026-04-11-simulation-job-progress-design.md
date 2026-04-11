# 推演实时进度与 Simulation Job 异步化设计

日期：2026-04-11

## 1. 背景

当前 `POST /simulations` 在 `src/if_then_mvp/api.py` 中仍是同步执行：

- API 线程内直接完成 `branch assessment`
- 直接生成 `first reply`
- `short_thread` 时继续同步逐轮生成
- 最终一次性返回 `SimulationRead`

这带来两个问题：

1. 前端在等待期间拿不到任何真实进度，只能显示占位文案。
2. 推演过程不可恢复、不可取消、不可在刷新后继续追踪。

本次设计要把推演链路改造成**后端阶段化执行 + 前端轮询 job 进度 + 完成后再拉最终结果**。

---

## 2. 目标

本次设计完成后，推演链路必须满足：

- `POST /simulations` 改为异步 job 创建接口
- 后端按阶段执行推演，并持续更新真实进度
- 前端只显示进度条和阶段文案，不显示任何中间推演产物
- 最终结果仍然只在完成后一次性展示
- simulation job 支持持久化恢复
- 同一会话再次发起推演时，旧 job 被软取消，前端只追踪最新 job

---

## 3. 已确认决策

基于本轮讨论，以下决策已固定：

- 前端需要细粒度阶段，而不是粗粒度占位
- 前端采用**轮询**，不做 SSE / WebSocket
- `POST /simulations` 可以正式切换为异步 job 返回
- simulation progress 需要持久化，支持刷新或重启后恢复
- 同一会话允许再次发起推演，但新的推演会接管旧 job
- 旧 job 的取消语义为**软取消**
  - `queued` job 可立即进入 `cancelled`
  - `running` job 只记录 `cancel_requested_at`，由 worker 在下一检查点转为 `cancelled`
  - 若某次 LLM 调用已发出，允许后台自然结束
  - 旧 job 的结果不写入最终可见 simulation 结果

---

## 4. 方案比较

### 方案 A：复用现有 `analysis_jobs`

优点：

- 表结构和轮询模型已有基础
- 前端可以部分复用现有 `JobRead`

缺点：

- `analysis_jobs` 语义会混入 simulation，边界变脏
- `/conversations/{id}/jobs` 结果会混杂分析和推演
- 现有分析进度 UI 需要额外过滤，维护成本高

结论：

- 不采用

### 方案 B：新增独立 `simulation_jobs`

优点：

- 分析 job 和推演 job 的职责边界清晰
- 取消、恢复、关联最终结果都更自然
- 前端可以单独演进 simulation 状态机

缺点：

- 需要新增模型、schema、endpoint 和 worker lane

结论：

- 采用该方案

### 方案 C：保持同步 `/simulations`，额外补一个临时进度通道

优点：

- 表面上接口变化较小

缺点：

- 与“持久化恢复”要求冲突
- 取消语义不稳定
- 容易形成同步结果接口 + 异步进度接口的双重复杂度

结论：

- 不采用

---

## 5. 核心设计结论

### 5.1 引入独立的 `simulation_jobs`

新增 `simulation_jobs`，作为推演执行期状态实体。

`simulations` 和 `simulation_turns` 仍只表示**最终完成后的正式结果**。

也就是说：

- `simulation_jobs` 负责执行期状态、进度、取消、恢复
- `simulations` 负责最终结果持久化

### 5.2 推演 job 完成前，不写任何中间推演文本

为了满足“前端只看进度，不看阶段性成果”，本次设计规定：

- job 运行过程中，不对前端暴露 `branch_assessment`
- 不对前端暴露 `first_reply_text`
- 不对前端暴露已生成的中间 turn
- 前端只能读取阶段名、百分比、状态文案

只有 `simulation_job.status = completed` 后，后端才写入正式 `Simulation` 结果，并允许前端读取。

### 5.3 新推演接管旧推演

同一 `conversation_id` 下：

- 新建 simulation job 前，先查找所有 `queued / running` job
- 对这些 job 发起软取消
- 前端只保存并轮询最新 job

这意味着产品语义是：

> 同一会话始终只有“当前正在追踪的最新推演”，旧 job 不再对用户可见。

---

## 6. 数据模型设计

### 6.1 新增 `simulation_jobs`

建议字段：

- `id`
- `conversation_id`
- `target_message_id`
- `mode`
- `turn_count`
- `replacement_content`
- `status`
- `current_stage`
- `progress_percent`
- `payload_json`
- `error_message`
- `cancel_requested_at`
- `result_simulation_id`
- `started_at`
- `finished_at`
- `created_at`

### 6.2 `status` 取值

- `queued`
- `running`
- `completed`
- `failed`
- `cancelled`

### 6.3 `current_stage` 取值

- `queued`
- `branch_assessment`
- `first_reply`
- `turn_generation`
- `completed`
- `failed`
- `cancelled`

### 6.4 `payload_json` 约束

`payload_json` 用于保存执行期元信息，例如：

- `current_stage_total_units`
- `current_stage_completed_units`
- `overall_total_units`
- `overall_completed_units`
- `status_message`

不保存前端可消费的中间推演文本。

---

## 7. API 设计

### 7.1 `POST /simulations`

输入保持现有 `SimulationCreate`：

- `conversation_id`
- `target_message_id`
- `replacement_content`
- `mode`
- `turn_count`

输出改为 `202 Accepted + SimulationJobRead`。

行为：

1. 校验 conversation 和 target message
2. 将同一会话下所有 `queued / running` simulation job 标记为取消中
   - `queued` job 可直接改为 `cancelled`
   - `running` job 只写入 `cancel_requested_at`
3. 创建新的 simulation job
4. 返回 job 元数据

### 7.2 `GET /simulation-jobs/{job_id}`

返回 `SimulationJobRead`，供前端轮询。

前端只依赖此接口获取：

- `status`
- `current_stage`
- `progress_percent`
- `current_stage_percent`
- `status_message`
- `result_simulation_id`

### 7.3 `GET /conversations/{conversation_id}/simulation-jobs?limit=1`

返回当前 conversation 最新 simulation job 列表。

用途：

- 刷新或重启后恢复进度
- 前端切回某个 conversation 时恢复“最新一条推演状态”

### 7.4 `GET /simulations/{simulation_id}`

读取正式 `SimulationRead` 结果。

用途：

- job `completed` 后前端单独拉最终结果
- 重启后恢复已完成的最新推演结果

---

## 8. 进度模型设计

### 8.1 细粒度阶段规则

#### `single_reply`

总单位数为 `2`：

1. `branch_assessment`
2. `first_reply`

#### `short_thread`

总单位数为 `turn_count + 1`：

1. `branch_assessment`
2. `first_reply`
3. 第 2 轮
4. 第 3 轮
5. ...

说明：

- 第 1 个单位表示分支判断
- 第 2 个单位表示首轮回复
- 从第 3 个单位开始，表示真实 short thread 的每一轮续写

### 8.2 前端展示文案建议

建议映射为：

- `branch_assessment` → `分支判断`
- `first_reply` → `首轮回复`
- `turn_generation` 且当前轮为 2 → `第 2 轮`
- `turn_generation` 且当前轮为 3 → `第 3 轮`
- ...
- `completed` → `推演完成`
- `failed` → `推演失败`
- `cancelled` → `已取消`

### 8.3 提前停止规则

若 `short_thread` 因自然收束或重复检测提前停止：

- `simulation_job` 仍应视为 `completed`
- `progress_percent` 直接补到 `100`
- `status_message` 可写为 `第 N 轮后自然收束`

前端不需要知道为什么停，只需要知道最终完成。

---

## 9. 后端执行流设计

### 9.1 引入独立 simulation worker lane

新增一条与分析 worker 平行的执行链：

- `run_next_simulation_job()`
- `run_simulation_forever()`

不建议继续在 API 请求线程中同步执行 simulation。

### 9.2 执行步骤

1. claim 一个 `queued` simulation job
2. 进入 `running`
3. 构建 `context_pack`
4. 执行 `branch_assessment`
5. 执行 `first_reply`
6. 如为 `short_thread`，从第 2 轮开始逐轮生成
7. 所有阶段成功后，一次性写入 `Simulation` 和 `SimulationTurn`
8. 将 `result_simulation_id` 回填到 `simulation_job`
9. job 标记为 `completed`

### 9.3 取消检查点

因为采用软取消，所以只需要在以下时机检查：

- claim job 后开始执行前
- 每次 LLM 调用前
- 每一轮 turn 生成前
- 最终结果落库前

如果发现 `cancel_requested_at` 已设置：

- job 标记 `cancelled`
- 不写入 `Simulation`
- 直接结束

### 9.4 错误处理

若以下任一步失败：

- context pack 构建失败
- LLM 请求失败
- 数据库写入失败

则：

- job 标记 `failed`
- 记录 `error_message`
- 不写入最终 `Simulation`

---

## 10. 前端状态流设计

### 10.1 提交推演

当前 `desktop/src/App.tsx` 直接等待 `createSimulation()` 返回最终结果。

改造后应变为：

1. 提交 `POST /simulations`
2. 得到 `SimulationJobRead`
3. 把当前 rewrite 视图切到 `pending`
4. 开始轮询 `GET /simulation-jobs/{job_id}`

### 10.2 只追踪最新 job

前端需要保存：

- 当前 conversation 正在追踪的 `simulationJobId`
- 当前请求 token
- 当前 job 快照
- 当前最终结果

规则：

- 只接受最新 request token 对应的 job 更新
- 旧 job 即使完成，也不能覆盖新 job 的界面状态

### 10.3 完成后读取结果

当 job 返回：

- `status = completed`
- `result_simulation_id != null`

前端再调用：

- `GET /simulations/{simulation_id}`

读取最终结果并切到现有 branch 结果视图。

### 10.4 刷新或重启恢复

切入 conversation 时：

1. 请求 `/conversations/{id}/simulation-jobs?limit=1`
2. 若最新 job 为 `queued / running`，恢复轮询
3. 若最新 job 为 `completed` 且有 `result_simulation_id`，可恢复结果态
4. 若最新 job 为 `failed / cancelled`，恢复到普通历史浏览态

### 10.5 新推演接管旧推演

同一 conversation 再次发起推演时：

- 前端立即放弃旧 job 追踪
- 后端会将旧 job 软取消
- 新 job 成为唯一被前端追踪的 job

---

## 11. 兼容性与迁移

### 11.1 `POST /simulations` 的语义变化

这是一次真实 API 语义切换：

- 旧语义：返回 `SimulationRead`
- 新语义：返回 `SimulationJobRead`

因此桌面前端必须同步改造，不能再按旧接口直接使用。

### 11.2 最终结果读取方式变化

新增 `GET /simulations/{simulation_id}` 后：

- `simulations` 表示正式完成的推演结果
- `simulation_jobs` 表示执行期状态

二者职责不能混淆。

### 11.3 历史 simulation 不受影响

旧的已完成 `simulations` 和 `simulation_turns` 记录继续保留。

本次迁移只新增 job 轨道，不需要改写历史结果。

---

## 12. 测试策略

### 12.1 后端测试

至少覆盖：

- `POST /simulations` 返回 job 而不是最终结果
- `single_reply` 的阶段进度正确
- `short_thread` 的逐轮阶段进度正确
- 新推演会软取消旧 job
- `cancelled` job 不写 `Simulation`
- `completed` job 会写 `Simulation` 并关联 `result_simulation_id`
- `failed` job 会正确持久化错误信息
- conversation 级最新 job 查询可恢复最新状态

### 12.2 前端测试

至少覆盖：

- 提交后进入真实轮询态
- 阶段文案按 job 实时变化
- 新 job 不会被旧 job 的轮询结果覆盖
- `completed` 后会二次请求最终 simulation 结果
- 刷新或重启后可恢复最新 simulation job
- `failed / cancelled` 时界面能正确退出 pending 状态

---

## 13. 非目标

本次设计不包含：

- 中间推演文本流式展示
- SSE / WebSocket
- 多个并发 simulation 结果同时可回看
- 用户显式点击“取消推演”按钮
- 分支树状管理

这些都可以在后续版本独立扩展。

---

## 14. 设计结论

本次正确方向不是继续在前端伪造等待态，而是：

> **将 `/simulations` 改造成独立的异步 simulation job 体系，由后端真实分阶段执行、前端轮询真实进度，并在完成后再一次性读取最终推演结果。**

这条路线能同时满足：

- 进度展示真实
- 中间产物不暴露
- 刷新/重启可恢复
- 新推演可接管旧推演
- 现有最终 simulation 结果模型继续保留
