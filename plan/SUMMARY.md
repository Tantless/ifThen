# 项目任务管理系统说明

更新时间：2026-04-11

## 概述

本项目现已建立完整的任务管理系统，位于 `plan/` 文件夹，用于协调多个 AI agent（Claude Code、Codex 等）的协作开发。

## 文件结构

```
plan/
├── README.md           # 任务管理系统说明
├── current-tasks.md    # 当前任务清单（必读）
├── backlog.md          # 待排期任务
└── completed.md        # 已完成任务归档
```

## 核心文档更新

### AGENTS.md
- 新增任务管理机制章节
- 更新文档优先级，将 `plan/current-tasks.md` 列为必读
- 更新工作交接协议，要求更新任务状态
- 更新质量检查清单，包含任务状态检查
- 更新协作最佳实践，强调任务驱动开发

### CLAUDE.md
- 新增"重要提示"章节，引导查看任务清单
- 新增"Task Management"章节，说明任务管理流程
- 列出当前优先级任务

## 当前任务概览

### 高优先级（P1）
- **M4：Windows Release / 打包发布准备**
  - Electron 打包配置
  - Python Runtime 随包分发
  - 数据目录策略
  - 日志系统
  - Release Smoke Test

### 中优先级（P2）
- **Desktop FrontUI 完整迁移**
  - 输入区真实发送能力
  - 分析侧栏/改写面板/分支视图 FrontUI 化
  - 旧桌面壳组件清理

- **Prompt 工程优化**
  - Persona/Snapshot/Branch Assessment 优化
  - First Reply/Next Turn 优化

### 低优先级（P3）
- 联系人/文件 Tab 真实数据接入
- 样式模块化
- 测试覆盖率提升

## 工作流程

1. **开始工作**：查看 `plan/current-tasks.md`，选择优先级最高的任务
2. **进行中**：更新任务状态为 `IN_PROGRESS`，记录进展
3. **完成**：移至 `plan/completed.md`，更新完成日期和验收结果
4. **新需求**：添加到 `plan/backlog.md`，标注优先级

## 协作规范

- 所有工作应对应 `plan/` 中的某个任务
- 完成任务后必须更新任务状态
- 发现新需求必须记录到 backlog
- 每周 review backlog，调整优先级

## 已完成里程碑

截至 2026-04-11，已完成：
- M0：后端 MVP 主链路
- M0.5：Simulation LLM 对齐
- M1：桌面后端产品化补口
- M2：Electron 桌面宿主层
- M3：桌面前端产品壳
- M3.1：桌面前端视觉精修
- M3.2：后端 Deprecated Warning 清理
- FrontUI 视觉迁移第一阶段

详见 `plan/completed.md`。

## 下一步

建议优先完成 **M4：Windows Release / 打包发布准备**，这是当前最高优先级任务，完成后可以进行真实用户测试。

详细任务分解和验收标准请查看 `plan/current-tasks.md`。
