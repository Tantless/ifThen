# 项目状态总览

更新时间：2026-04-12

> 本文档是项目当前唯一的状态 / 里程碑 / 迁移现状总览。`docs/superpowers/specs/` 保留设计文档，`docs/superpowers/plans/` 保留历史执行计划，`plan/TODO.md` 继续作为唯一待办清单。

## 一句话状态

`main` 当前已经跑通了“导入聊天记录 -> 异步分析 -> 历史浏览 -> 改写消息 -> 反事实推演 -> 桌面端展示”的完整闭环，桌面主界面与聊天记录弹窗也已完成一轮可用性打磨；当前剩余的最高优先级工作是 Windows 打包发布和项目结构重构。

## 当前验证基线

本次重构启动前，已重新验证：

- `python -m pytest -q` -> `86 passed`
- `cd desktop && npm test` -> `13 files / 110 tests passed`
- `cd desktop && npm run typecheck` -> 通过
- `cd desktop && npm run build` -> 通过
- GUI 手工验收仍需人工执行，本次自动流程未替代真实交互验证

## 里程碑时间线

### 2026-04-05：后端 MVP 与总规格成形

- 明确了“真实聊天历史上的反事实推演”产品定义
- 确立了 FastAPI + SQLite + worker 的后端主链路
- 建立 QQ 文本导入、消息解析、切段、摘要、topic、persona、snapshot、cutoff-safe 检索、simulation 的总体设计

### 2026-04-06：Simulation LLM 对齐与桌面化方向确定

- `/simulations` 从占位逻辑切到真实 LLM 驱动
- 运行时模型配置拆分为 API / worker 两套解析入口
- 明确 Electron + React + TypeScript 桌面化方案

### 2026-04-07：Electron 宿主层与桌面产品壳落地

- Electron 主进程、preload、renderer 基础结构落地
- 自动拉起 Python API / worker 与健康检查链路接通
- 欢迎引导、设置抽屉、导入弹窗、会话列表、聊天区、改写推演、分析侧栏形成闭环

### 2026-04-08：主界面视觉统一与 frontUI 迁移

- 主聊天区域切到 frontUI 三栏主壳
- 无边框窗口、自定义标题栏、全窗口铺满的桌面壳完成
- 桌面前端 visual polish 完成
- FastAPI `on_event("startup")` warning 清理为 lifespan
- 阶段成果已回归 `main`

### 2026-04-10：窗口现代化与现状审计

- Windows 原生标题栏观感做过一轮现代化整理
- 仓库曾做过前后端能力盘点，后续文档已以当前事实重新收口，不再保留独立审计文档

### 2026-04-11：推演进度反馈与 V2 准备

- simulation job 进度反馈链路补齐
- 桌面端继续进入 V2 小迭代准备阶段

### 2026-04-12：V1 / V2 体验打磨与聊天记录功能完成

- 已完成会话删除、模型设置拆分、导入后默认滚动到底部、时间显示规则等低工作量修复
- 已完成聊天记录弹窗、搜索、日期筛选、定位原消息、禁用无消息日期等能力
- 已修复真实导入时间戳解析与按天筛选串天问题
- 已完成改写气泡与聊天日期分隔线的多轮视觉修正

## 当前已经具备的产品能力

### 后端能力

- 导入 `QQChatExporter V5` 私聊文本
- 解析结构化消息并落库
- 会话切段与 `isolated / merged_isolated` 处理
- 生成段摘要、话题、人格画像、关系快照
- 基于时间截断组装 cutoff-safe 上下文
- 生成 `single_reply` / `short_thread` 反事实推演
- 支持任务查询、模拟任务查询、会话删除、重跑分析、消息上下文查询

### 桌面端能力

- Electron frameless shell + 自定义标题栏
- 自动拉起本地 API / worker
- 欢迎引导、设置抽屉、导入弹窗
- 会话列表、聊天浏览、历史消息懒加载
- 改写历史消息并发起推演
- 分支视图与分析侧栏
- 聊天记录弹窗搜索、日期筛选、定位原消息

## 当前仍是过渡态或未完成的部分

- 只支持 QQ 私聊文本导入，微信导入仍未进入主线
- 仍是规则检索，未接入 embedding
- Windows release、安装器、自动更新、正式打包链路未开始
- 通讯录 tab、文件 tab 仍是占位能力
- 聊天输入框“发送消息”仍是本地追加，不是持久化发送
- 后端已有但前端尚未暴露的入口主要包括：重新分析、消息上下文独立查看、segments 结果查看

## 当前推荐的文档入口

- `plan/TODO.md`：唯一待办清单
- `docs/project-status.md`：当前状态、里程碑与现状总览
- `docs/superpowers/specs/`：按日期沉淀的设计文档
- `docs/superpowers/plans/`：历史执行计划与交付过程记录

## 文档整理说明

本次重构已将以下“状态型”文档合并到本文档，不再单独维护：

- `docs/2026-04-06-agent-handoff.md`
- `docs/2026-04-08-milestone-progress-summary.md`
- `docs/desktop-frontui-migration-status.md`
- `docs/后端接口与前端使用盘点.md`
- 根目录 `requirement-new.md`
