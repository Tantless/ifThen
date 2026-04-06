# 推演模块 LLM 对齐设计增补

## 1. 背景

现有 MVP 在分析阶段已经生成了：

- 会话段摘要
- 主题归并结果
- 双方人格画像
- 时间点关系状态快照

并且在发起 `/simulations` 时已经将这些信息组装进 `ContextPack`。

但当前推演实现仍然使用确定性占位逻辑：

- `assess_branch` 未调用 LLM
- `generate_first_reply` 未调用 LLM
- `simulate_short_thread` 未调用 LLM

这与主设计文档中“先判断状态变化，再生成首轮回复与自动短链结果”“自动短链内部必须逐轮推进”的要求不一致。

## 2. 目标

本次增补只补齐推演模块，不改动导入、分析、检索主链路。

补齐后，推演模块必须满足：

- 分支状态判断使用 LLM
- 首轮回复生成使用 LLM
- `short_thread` 使用逐轮 LLM 推演
- 推演时显式利用 `ContextPack` 中的：
  - 当前段前文
  - 同日历史段摘要
  - 相关话题摘要
  - 双方人格画像
  - 截断安全的关系状态
- 推演结果继续写入现有 `simulations` 和 `simulation_turns`

## 3. 设计

### 3.1 保持 API 形状稳定

`POST /simulations` 的请求与响应结构保持不变：

- 继续返回 `first_reply_text`
- 继续返回 `impact_summary`
- 继续返回 `simulated_turns`

允许的行为变化：

- `simulated_turns` 的第 1 轮改为真实首轮回复
- 因重复检测或自然收束，`simulated_turns` 允许少于请求的 `turn_count`

### 3.2 推演分三步执行

#### 第一步：分支判断

LLM 输入：

- 原消息
- 改写消息
- 当前段前文
- 同日历史段
- 相关话题摘要
- 人格画像
- 当前关系状态

LLM 输出结构化 `BranchAssessment`：

- `branch_direction`
- `state_shift_summary`
- `other_immediate_feeling`
- `reply_strategy`
- `risk_flags`
- `confidence`

#### 第二步：首轮回复

LLM 输入：

- `ContextPack`
- `BranchAssessment`

LLM 输出结构化 `FirstReplyPayload`：

- `first_reply_text`
- `strategy_used`
- `first_reply_style_notes`
- `state_after_turn`

`first_reply_text` 同时：

- 存入 `simulations.first_reply_text`
- 作为 `short_thread` 的第 1 轮 `simulation_turn`

#### 第三步：逐轮短链

从第 2 轮开始，按轮调用 LLM。

每轮输入：

- `ContextPack`
- `BranchAssessment`
- 当前临时状态
- 当前已生成 transcript
- 指定下一位说话者（`self` 或 `other`）

每轮输出结构化 `NextTurnPayload`：

- `message_text`
- `strategy_used`
- `state_after_turn`
- `generation_notes`
- `should_stop`
- `stopping_reason`

### 3.3 角色与轮次规则

- 第 1 轮固定为 `other`，内容等于首轮回复
- 第 2 轮固定为 `self`
- 后续按 `other / self / other / self` 交替

### 3.4 重复检测与提前停止

为避免机械循环，本次补丁加入两层停止条件：

- LLM 显式返回 `should_stop = true`
- 新生成文本与最近同角色发言高度重复时，立即停止

停止后：

- 已生成轮次保留
- 不再强行补满 `turn_count`

## 4. 运行时配置

推演模块需要独立的 LLM 访问能力。

运行时按以下顺序解析模型配置：

1. 数据库 `app_settings`
   - `llm.base_url`
   - `llm.api_key`
   - `llm.chat_model`
2. 环境变量回退
   - `IF_THEN_LLM_BASE_URL`
   - `IF_THEN_LLM_API_KEY`
   - `IF_THEN_LLM_CHAT_MODEL`

若两者都缺失，则 `/simulations` 返回明确错误，不再 silently fallback 到占位逻辑。

## 5. 验证重点

- 推演阶段确实发生 LLM 调用
- prompt 中确实包含人格、话题、关系状态和截断安全上下文
- 首轮回复与短链第 1 轮一致
- 短链逐轮推进，不再使用固定模板
- 重复文本会被检测并提前停止

