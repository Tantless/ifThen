# 代号：如果那时

> **如果那时，说了不同的话，结果是否不一样？**

大多数人在一段关系结束后的回望里，都曾被同一个问题击中过：  
**如果那一天，在那个关键节点，我说了另一句话，我们两个人的故事，会不会走向不同的结局？**

这个项目想做的，正是把这种迟来的反问，变成一次可以被认真推演的实验。它让用户回到某个**真实发生过的聊天时间点**，只改动自己说过的一句话，并在**绝不泄漏未来信息**的前提下，结合该节点之前已经发生的关系历史、话题脉络与互动状态，推演对方可能会如何回应，以及这段对话后续可能会如何分支发展。

它不是普通的聊天分析器，也不是单纯的“聊天对象复刻器”。  
它更接近一种**反事实对话模拟**：不是去宣称唯一正确的未来，而是尽可能还原“当时的那个人、当时的那段关系、当时的那个瞬间”，再去回答一个足够残酷、也足够动人的问题：

> **如果那时，真的换了一种说法，一切会不会不同？**

---

## 当前状态

当前 `main` 分支已经具备：

- Python 后端主链路（导入 / 解析 / 分析 / 检索 / 推演）
- Electron 桌面宿主层
- React + TypeScript 桌面前端主流程
- 一轮桌面前端 visual polish

当前验证基线：

- `python -m pytest -q` → `71 passed`
- `cd desktop && npm test` → `9 files / 46 tests passed`
- `cd desktop && npm run typecheck` → 通过
- `cd desktop && npm run build` → 通过

---

## 核心能力

### 后端能力

- 导入 `QQChatExporter V5` 私聊文本
- 解析消息、切段、生成 `normal / isolated / merged_isolated`
- 生成段摘要、多个 topic、人格画像、关系快照
- 按时间截断组装 cutoff-safe 上下文
- 调用真实 LLM 生成首轮回复和自动短链推演
- 提供本地 API、worker 和 CLI 演示脚本
- 支持会话删除、重跑分析、job 恢复查询、消息上下文查询

### 桌面端能力

- Electron 单窗口桌面应用壳
- 自动拉起本地 Python API / worker
- 欢迎引导、设置抽屉、导入弹窗
- 会话列表、历史聊天浏览、分析状态展示
- 改写并推演、分支视图、analysis inspector

---

## 环境要求

- Windows
- Python `3.11+`
- Node.js `20+`（建议）
- 一个可访问的 OpenAI 兼容聊天接口

说明：

- worker 在分析阶段会调用大模型
- API 在 `/simulations` 阶段也会调用大模型
- API 和 worker 共享同一套运行时配置解析逻辑
- 运行时模型配置优先级为：
  1. `/settings` 中保存的 `llm.base_url` / `llm.api_key` / `llm.chat_model`
  2. 环境变量 `IF_THEN_LLM_BASE_URL` / `IF_THEN_LLM_API_KEY` / `IF_THEN_LLM_CHAT_MODEL`
  3. 项目根目录的 `local_llm_config.py`

---

## 开发环境 Quickstart

### 1. 准备 Python 环境

在项目根目录执行：

```powershell
cd D:\newProj
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
```

可选：指定本地数据目录。默认是项目根目录下的 `.data`。

```powershell
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
```

### 2. 配置模型

先复制示例配置文件：

```powershell
Copy-Item local_llm_config.example.py local_llm_config.py
```

然后编辑 `local_llm_config.py`：

```python
API_LLM_CONFIG = {
    "base_url": "https://your-openai-compatible-endpoint/v1",
    "api_key": "your-api-key",
    "chat_model": "gpt-5.4-mini",
}

WORKER_LLM_CONFIG = {
    "base_url": "https://your-openai-compatible-endpoint/v1",
    "api_key": "your-api-key",
    "chat_model": "gpt-5.4-mini",
}
```

### 3. 准备桌面前端依赖

```powershell
cd D:\newProj\desktop
npm install
```

---

## 如何唤起后端

### 方式 A：手动单独启动 API 和 worker

适合后端调试、接口联调、CLI 演示。

#### 启动 API

```powershell
cd D:\newProj
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_api.py
```

#### 启动 worker

另开一个终端：

```powershell
cd D:\newProj
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_worker.py
```

#### 健康检查

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

期望返回：

```json
{"status":"ok"}
```

### 方式 B：通过 Electron 自动拉起后端

适合桌面端联调。

Electron 主进程会按以下顺序启动：

1. 解析仓库根目录与 `.venv` Python（若存在）
2. 启动 `python scripts/run_api.py`
3. 轮询 `/health`
4. API 健康后启动 `python scripts/run_worker.py`

也就是说，**桌面应用正常启动时，不需要你再手动单独开 API / worker**。

---

## 如何唤起前端 / 桌面端

### 开发模式

#### 终端 A：启动 renderer dev server

```powershell
cd D:\newProj\desktop
npm run dev
```

#### 终端 B：生成 Electron 主进程与 preload 产物

首次进入开发态，或修改了 `desktop/electron/*.ts` / `desktop/electron/**/*.ts` 之后执行：

```powershell
cd D:\newProj\desktop
npm run build:electron
```

#### 终端 B：启动 Electron

```powershell
cd D:\newProj\desktop
$env:IF_THEN_DESKTOP_RENDERER_URL = "http://127.0.0.1:5173"
npx electron .
```

开发态最小流程总结：

1. `cd D:\newProj\desktop && npm run dev`
2. `cd D:\newProj\desktop && npm run build:electron`
3. `cd D:\newProj\desktop && $env:IF_THEN_DESKTOP_RENDERER_URL = "http://127.0.0.1:5173"; npx electron .`

### 本地构建后运行

```powershell
cd D:\newProj\desktop
npm run build
npx electron .
```

`npm run build` 会同时生成：

- `desktop/dist/`：renderer 静态资源
- `desktop/dist-electron/electron/main.js`
- `desktop/dist-electron/electron/preload.js`

---

## 快速演示（后端 / CLI）

### 1. 导入聊天记录

把 `self_display_name` 改成聊天记录里你自己的昵称。

```powershell
curl.exe -X POST "http://127.0.0.1:8000/imports/qq-text" `
  -F "self_display_name=Tantless" `
  -F "file=@C:\Users\Tantless\Desktop\聊天记录.txt;type=text/plain"
```

返回里会包含：

- `conversation.id`
- `job.id`

### 2. 轮询分析任务

假设任务 ID 是 `1`：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/jobs/1"
```

当返回里出现：

- `status = completed`
- `current_stage = completed`

说明分析已经完成。

### 3. 列出可改写消息

```powershell
python scripts\sim_cli.py list-self-text --conversation-id 1 --limit 20
```

按关键字过滤：

```powershell
python scripts\sim_cli.py list-self-text --conversation-id 1 --keywords "你好" --limit 20
```

### 4. 发起推演

假设：

- `conversation_id = 1`
- `target_message_id = 12`

自动推演 4 轮：

```powershell
python scripts\sim_cli.py simulate `
  --conversation-id 1 `
  --target-message-id 12 `
  --replacement "如果你现在不想说也没关系，等你愿意的时候我们再慢慢聊。" `
  --mode short_thread `
  --turn-count 4
```

如果只想看第一条回复，可以用：

```powershell
python scripts\sim_cli.py simulate `
  --conversation-id 1 `
  --target-message-id 12 `
  --replacement "如果你现在不想说也没关系，等你愿意的时候我们再慢慢聊。" `
  --mode single_reply `
  --turn-count 1
```

---

## 常用接口

- `GET /health`
- `POST /imports/qq-text`
- `GET /conversations`
- `GET /conversations/{conversation_id}`
- `GET /jobs/{job_id}`
- `GET /conversations/{conversation_id}/jobs`
- `GET /conversations/{conversation_id}/messages`
- `GET /messages/{message_id}`
- `GET /messages/{message_id}/context?radius=20`
- `GET /conversations/{conversation_id}/segments`
- `GET /conversations/{conversation_id}/topics`
- `GET /conversations/{conversation_id}/profile`
- `GET /conversations/{conversation_id}/timeline-state?at=...`
- `GET /settings`
- `PUT /settings`
- `DELETE /conversations/{conversation_id}`
- `POST /conversations/{conversation_id}/rerun-analysis`
- `POST /simulations`

---

## 数据目录

程序会把数据写到 `IF_THEN_DATA_DIR` 对应目录下，默认是项目根目录 `.data`。

通常会看到：

- `db/`
  - SQLite 数据库
- `uploads/`
  - 导入的原始聊天文本

如果显式设置了：

```powershell
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
```

那么数据会写到 `D:\newProj\.data`。

---

## 项目结构

- `src/if_then_mvp/api.py`
  - API 主入口
- `src/if_then_mvp/worker.py`
  - 后台分析主流程
- `src/if_then_mvp/analysis.py`
  - 分析阶段 prompt 与 payload
- `src/if_then_mvp/simulation.py`
  - 推演阶段 prompt 与 payload
- `src/if_then_mvp/retrieval.py`
  - cutoff-safe 上下文检索
- `src/if_then_mvp/runtime_llm.py`
  - 运行时 LLM 配置解析与客户端构建
- `src/if_then_mvp/conversation_lifecycle.py`
  - 会话删除 / 重跑分析等生命周期操作
- `scripts/run_api.py`
  - API 启动入口
- `scripts/run_worker.py`
  - worker 启动入口
- `scripts/sim_cli.py`
  - 演示 CLI 入口
- `desktop/`
  - Electron + React + TypeScript 桌面工作区

---

## 已完成成果

### 后端阶段

- 后端 MVP 主链路完成
- Simulation LLM 对齐完成
- 桌面前置的后端产品化补口完成：
  - 模型配置统一生效
  - job 恢复查询
  - 消息上下文浏览
  - 删除会话
  - 重跑分析

### 桌面应用阶段

- Electron 桌面宿主层完成
- 桌面前端主流程完成：
  - 欢迎引导
  - 设置抽屉
  - 导入弹窗
  - 会话列表
  - 聊天浏览
  - 改写并推演
  - 分支视图
  - 分析侧栏
- 桌面前端 visual polish 完成

### 质量收口

- FastAPI `on_event("startup")` deprecated warning 已迁移到 lifespan
- 主分支成果已全部回归到 `main`
- 历史 worktree 已清理完成

---

## 当前已知限制

- 当前只支持 `QQ` 私聊文本导入
- 当前只做规则检索，不做 embedding
- 推演模式只有：
  - `single_reply`
  - `short_thread`
- 当前仍处于开发态桌面应用，不含正式 Windows release / 安装器 / 自动更新链路

---

## 相关文档

- `docs/2026-04-08-milestone-progress-summary.md`
- `docs/superpowers/specs/2026-04-05-counterfactual-conversation-mvp-design.md`
- `docs/superpowers/specs/2026-04-06-simulation-llm-alignment-design.md`
- `docs/superpowers/specs/2026-04-06-desktop-app-design.md`
- `docs/superpowers/specs/2026-04-07-desktop-frontend-product-shell-design.md`
- `docs/superpowers/specs/2026-04-08-desktop-frontend-visual-polish-design.md`
