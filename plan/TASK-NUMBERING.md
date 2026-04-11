# 任务编号系统使用说明

更新时间：2026-04-11

## 概述

项目现已建立完整的任务编号系统，支持多个 AI agent 并行协作开发。

## 文件结构

```
plan/
├── README.md              # 任务管理系统说明
├── SUMMARY.md             # 任务系统概览
├── PARALLEL-GUIDE.md      # 多 Agent 并行指南（新增）
├── current-tasks.md       # 当前任务清单（已更新，包含任务编号）
├── backlog.md             # 待排期任务
└── completed.md           # 已完成任务归档
```

## 任务编号系统

### 编号格式

```
TASK-<类别>-<序号>
```

### 类别说明

| 类别 | 前缀 | 说明 | 任务数 |
|------|------|------|--------|
| Windows Release | M4 | 打包发布相关 | 5 个 |
| 前端界面 | UI | FrontUI 迁移 | 7 个 |
| 用户体验 | UX | 交互优化 | 5 个 |
| AI Prompt | AI | Prompt 工程 | 5 个 |

**总计**：22 个已编号任务

### 并行性标记

| 标记 | 说明 | 数量 |
|------|------|------|
| 🟢 | 可独立并行 | 18 个 |
| 🟡 | 部分依赖，需协调 | 2 个 |
| 🔴 | 顺序依赖，必须等待 | 2 个 |

## 任务清单

### M4：Windows Release（5 个任务）

1. **TASK-M4-01**：Electron 打包配置 🟢
2. **TASK-M4-02**：Python Runtime 随包分发 🟢
3. **TASK-M4-03**：数据目录策略 🟢
4. **TASK-M4-04**：日志系统 🟢
5. **TASK-M4-05**：Release Smoke Test 🔴（依赖 M4-01, M4-02, M4-03）

### UI：FrontUI 迁移（7 个任务）

1. **TASK-UI-01**：输入区真实发送能力 🟢
2. **TASK-UI-02**：联系人 Tab 真实数据接入 🟢
3. **TASK-UI-03**：文件 Tab 真实能力 🟢
4. **TASK-UI-04**：分析侧栏 FrontUI 化 🟡（与 UX-04 冲突）
5. **TASK-UI-05**：改写面板 FrontUI 化 🟢
6. **TASK-UI-06**：分支视图 FrontUI 化 🟢
7. **TASK-UI-07**：旧桌面壳组件清理 🔴（依赖 UI-04, UI-05, UI-06）

### UX：用户体验优化（5 个任务）

1. **TASK-UX-01**：优化推演进度展示 🟢
2. **TASK-UX-02**：头像管理功能 🟢
3. **TASK-UX-03**：分离分析和推演模型配置 🟡
4. **TASK-UX-04**：分析侧栏改为弹窗 🟡（与 UI-04 冲突）
5. **TASK-UX-05**：拆分导入和分析流程 🟢

### AI：Prompt 工程优化（5 个任务）

1. **TASK-AI-01**：Persona Prompt 优化 🟢
2. **TASK-AI-02**：Snapshot Prompt 优化 🟢
3. **TASK-AI-03**：Branch Assessment Prompt 优化 🟢
4. **TASK-AI-04**：First Reply Prompt 优化 🟢
5. **TASK-AI-05**：Next Turn Prompt 优化 🟢

## 并行执行能力

### 最大并行数

- **理论最大**：18 个任务（所有 🟢 标记的任务）
- **推荐并行**：5-8 个 agents
- **最小并行**：3 个 agents

### 推荐方案

#### 方案 A：8 个 Agents（最快，1-2 周）

```
Agent-1: TASK-M4-01
Agent-2: TASK-M4-02
Agent-3: TASK-AI-01
Agent-4: TASK-AI-02
Agent-5: TASK-AI-03
Agent-6: TASK-UI-05
Agent-7: TASK-UI-06
Agent-8: TASK-UX-01
```

#### 方案 B：5 个 Agents（平衡，2-3 周）

```
Agent-1: M4 核心组 (M4-01, M4-02, M4-03)
Agent-2: Prompt 工程组 A (AI-01, AI-02)
Agent-3: Prompt 工程组 B (AI-03, AI-04, AI-05)
Agent-4: FrontUI 迁移组 (UI-05, UI-06)
Agent-5: 用户体验组 (UX-01, UX-02, UX-05)
```

#### 方案 C：3 个 Agents（保守，3-4 周）

```
Agent-1: M4 + 配置相关
Agent-2: 所有 Prompt 工程
Agent-3: 所有 FrontUI + UX
```

## 任务冲突

### 高冲突（必须二选一）

- **TASK-UI-04** vs **TASK-UX-04**
  - 冲突原因：都修改分析侧栏
  - 解决方案：需要用户决策产品方向

### 中冲突（需要协调）

- **TASK-M4-03, M4-04, UX-03**
  - 冲突点：配置模块
  - 解决方案：约定文件分区，各自负责不同配置项

## Agent 使用指南

### 1. 查看任务

```bash
# 查看所有任务
cat plan/current-tasks.md

# 查看可并行任务
cat plan/current-tasks.md | grep "🟢"

# 查看并行指南
cat plan/PARALLEL-GUIDE.md
```

### 2. 领取任务

在 `plan/current-tasks.md` 中更新：

```markdown
**TASK-XX-XX：任务名称** (P2) 🟢
- **状态**：IN_PROGRESS
- **负责人**：Agent-Name
- **开始时间**：2026-04-11 10:30
```

### 3. 提交变更

```bash
git add plan/current-tasks.md
git commit -m "Claim TASK-XX-XX: 任务名称"
git push
```

### 4. 完成任务

```bash
# 运行测试
python -m pytest -q
cd desktop && npm test && npm run typecheck

# 提交代码
git commit -m "Complete TASK-XX-XX: 任务名称"

# 更新任务状态（移至 completed.md）
```

## 优先级建议

### P1 任务（最高优先级）

- TASK-M4-01：Electron 打包配置
- TASK-M4-02：Python Runtime 随包分发
- TASK-M4-03：数据目录策略
- TASK-M4-05：Release Smoke Test

### P2 任务（中优先级）

- 所有 UI 任务（UI-01 到 UI-06）
- 所有 UX 任务（UX-01 到 UX-05）
- 所有 AI 任务（AI-01 到 AI-05）
- TASK-M4-04：日志系统

### P3 任务（低优先级）

- TASK-UI-02：联系人 Tab
- TASK-UI-03：文件 Tab
- TASK-UI-07：旧桌面壳清理

## 进度跟踪

### 当前状态（2026-04-11）

- **总任务数**：22 个
- **已完成**：0 个
- **进行中**：0 个
- **待开始**：22 个

### 预计完成时间

- **方案 A（8 agents）**：1-2 周
- **方案 B（5 agents）**：2-3 周
- **方案 C（3 agents）**：3-4 周

## 相关文档

- `plan/current-tasks.md` - 详细任务清单
- `plan/PARALLEL-GUIDE.md` - 并行执行指南
- `AGENTS.md` - Agent 协作规范
- `CLAUDE.md` - 项目技术文档

## 下一步

1. 确定使用哪个并行方案（A/B/C）
2. 分配 agents 到具体任务
3. 解决 TASK-UI-04 vs TASK-UX-04 冲突（需要用户决策）
4. 开始并行开发

---

**最后更新**：2026-04-11  
**维护者**：项目协作团队  
**版本**：1.0
