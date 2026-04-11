# 多 Agent 并行任务分配指南

更新时间：2026-04-11

## 快速参考

### 任务编号系统

| 类别 | 前缀 | 说明 | 示例 |
|------|------|------|------|
| Windows Release | M4 | 打包发布相关 | TASK-M4-01 |
| 前端界面 | UI | FrontUI 迁移 | TASK-UI-01 |
| 用户体验 | UX | 交互优化 | TASK-UX-01 |
| AI Prompt | AI | Prompt 工程 | TASK-AI-01 |

### 并行性标记

| 标记 | 说明 | 可并行数 |
|------|------|----------|
| 🟢 | 可独立并行 | 无限制 |
| 🟡 | 部分依赖，需协调 | 2-3 个 |
| 🔴 | 顺序依赖，必须等待 | 1 个 |

---

## 推荐的 Agent 分配方案

### 方案 A：8 个 Agents 并行（最快）

```
Agent-1: TASK-M4-01 (Electron 打包配置)
Agent-2: TASK-M4-02 (Python Runtime 随包分发)
Agent-3: TASK-AI-01 (Persona Prompt 优化)
Agent-4: TASK-AI-02 (Snapshot Prompt 优化)
Agent-5: TASK-AI-03 (Branch Assessment Prompt 优化)
Agent-6: TASK-UI-05 (改写面板 FrontUI 化)
Agent-7: TASK-UI-06 (分支视图 FrontUI 化)
Agent-8: TASK-UX-01 (优化推演进度展示)
```

**预计完成时间**：1-2 周（取决于最慢的任务）

---

### 方案 B：5 个 Agents 并行（平衡）

```
Agent-1: M4 核心组
  - TASK-M4-01 (Electron 打包配置)
  - TASK-M4-02 (Python Runtime 随包分发)
  - TASK-M4-03 (数据目录策略)

Agent-2: Prompt 工程组 A
  - TASK-AI-01 (Persona Prompt 优化)
  - TASK-AI-02 (Snapshot Prompt 优化)

Agent-3: Prompt 工程组 B
  - TASK-AI-03 (Branch Assessment Prompt 优化)
  - TASK-AI-04 (First Reply Prompt 优化)
  - TASK-AI-05 (Next Turn Prompt 优化)

Agent-4: FrontUI 迁移组
  - TASK-UI-05 (改写面板 FrontUI 化)
  - TASK-UI-06 (分支视图 FrontUI 化)

Agent-5: 用户体验组
  - TASK-UX-01 (优化推演进度展示)
  - TASK-UX-02 (头像管理功能)
  - TASK-UX-05 (拆分导入和分析流程)
```

**预计完成时间**：2-3 周

---

### 方案 C：3 个 Agents 并行（保守）

```
Agent-1: M4 + 配置相关
  - TASK-M4-01 (Electron 打包配置)
  - TASK-M4-02 (Python Runtime 随包分发)
  - TASK-M4-03 (数据目录策略)
  - TASK-M4-04 (日志系统)
  - TASK-UX-03 (分离分析和推演模型配置)

Agent-2: 所有 Prompt 工程
  - TASK-AI-01 到 TASK-AI-05

Agent-3: 所有 FrontUI + UX
  - TASK-UI-05, TASK-UI-06
  - TASK-UX-01, TASK-UX-02, TASK-UX-05
```

**预计完成时间**：3-4 周

---

## 任务冲突矩阵

### 高冲突（不能同时执行）

| 任务 A | 任务 B | 冲突原因 | 解决方案 |
|--------|--------|----------|----------|
| TASK-UI-04 | TASK-UX-04 | 都修改分析侧栏 | 二选一或合并 |

### 中冲突（需要协调）

| 任务组 | 冲突点 | 协调方式 |
|--------|--------|----------|
| M4-03, M4-04, UX-03 | 配置模块 | 约定配置文件结构，分区域修改 |
| M4-03, M4-04 | 数据/日志目录 | 统一目录规划 |

### 低冲突（可并行）

所有其他任务组合都是低冲突或无冲突。

---

## Agent 领取流程

### 1. 查看可用任务

```bash
# 查看当前任务清单
cat plan/current-tasks.md | grep "🟢"
```

### 2. 选择任务

**优先级规则**：
1. 优先选择 P1 任务
2. 优先选择 🟢 标记的任务
3. 避免选择已有冲突的任务

**检查冲突**：
```bash
# 查看当前进行中的任务
cat plan/current-tasks.md | grep "IN_PROGRESS"
```

### 3. 领取任务

在 `plan/current-tasks.md` 中更新任务状态：

```markdown
**TASK-XX-XX：任务名称** (P2) 🟢
- **状态**：IN_PROGRESS
- **负责人**：Agent-Alice
- **开始时间**：2026-04-11 10:30
```

### 4. 提交变更

```bash
git add plan/current-tasks.md
git commit -m "Claim TASK-XX-XX: 任务名称

Agent: Agent-Alice
Start: 2026-04-11 10:30"
git push
```

### 5. 执行任务

按照任务清单中的步骤执行，定期更新进度。

### 6. 完成任务

```bash
# 运行测试
python -m pytest -q
cd desktop && npm test && npm run typecheck

# 提交代码
git add .
git commit -m "Complete TASK-XX-XX: 任务名称

- 完成项 1
- 完成项 2
- 验收标准已满足"

# 更新任务状态
# 将任务从 current-tasks.md 移至 completed.md
```

---

## 协调机制

### 配置模块协调（M4-03, M4-04, UX-03）

**约定**：
- M4-03 负责：`config.py` 中的数据目录配置
- M4-04 负责：`config.py` 中的日志配置
- UX-03 负责：`runtime_llm.py` 中的模型配置

**文件分区**：
```python
# config.py
class Settings:
    # M4-03 负责
    data_dir: str
    
    # M4-04 负责
    log_dir: str
    log_level: str
    
    # UX-03 不修改此文件
```

```python
# runtime_llm.py
# UX-03 负责
def load_effective_llm_config(role: str):
    # 添加 role 参数支持 "analysis" 和 "simulation"
    pass
```

### 分析侧栏冲突解决（UI-04 vs UX-04）

**需要用户决策**：
- 选项 A：保留侧栏，执行 TASK-UI-04
- 选项 B：改为弹窗，执行 TASK-UX-04
- 选项 C：合并任务，先 FrontUI 化再改弹窗

**建议**：先询问用户偏好，再分配任务。

---

## 进度跟踪

### 每日同步

每个 agent 在完成一天的工作后，更新任务进度：

```markdown
**TASK-XX-XX：任务名称** (P2) 🟢
- **状态**：IN_PROGRESS (60%)
- **负责人**：Agent-Alice
- **开始时间**：2026-04-11 10:30
- **进度更新**：
  - 2026-04-11: 完成配置文件设计 (30%)
  - 2026-04-12: 完成后端实现 (60%)
```

### 阻塞报告

如果遇到阻塞，立即更新：

```markdown
**TASK-XX-XX：任务名称** (P2) 🟢
- **状态**：BLOCKED
- **负责人**：Agent-Alice
- **阻塞原因**：等待用户确认产品方向
- **阻塞时间**：2026-04-12 14:00
```

---

## 最佳实践

### 1. 提前声明

在开始任务前，先 commit 任务领取，避免冲突。

### 2. 频繁同步

每完成一个子任务，就 commit 一次，方便其他 agent 了解进度。

### 3. 清晰沟通

在 commit message 中说明：
- 完成了什么
- 还剩什么
- 是否有阻塞

### 4. 测试先行

完成任务后，先运行测试，确保没有破坏现有功能。

### 5. 文档同步

如果修改了架构或接口，立即更新 CLAUDE.md 或 AGENTS.md。

---

## 常见问题

### Q1: 如何知道哪些任务可以并行？

查看任务的并行性标记：
- 🟢 = 可以随意并行
- 🟡 = 需要协调，但可以并行
- 🔴 = 必须等待其他任务完成

### Q2: 如果两个 agent 同时领取了同一个任务怎么办？

先 push 的 agent 获得任务，后 push 的 agent 需要选择其他任务。

### Q3: 如果任务被阻塞了怎么办？

1. 更新任务状态为 BLOCKED
2. 说明阻塞原因
3. 选择其他任务继续工作

### Q4: 如何处理紧急任务？

紧急任务应该标记为 P0，所有 agent 应优先处理 P0 任务。

### Q5: 完成任务后如何通知其他 agent？

通过 git commit message 和更新 `plan/completed.md` 来通知。

---

## 总结

- **最多可并行**：15+ 个任务（所有 🟢 标记的任务）
- **推荐并行数**：5-8 个 agents
- **关键冲突**：TASK-UI-04 vs TASK-UX-04（需要用户决策）
- **协调重点**：配置模块（M4-03, M4-04, UX-03）

选择合适的方案，开始并行开发吧！
