# 代号：如果那时

> **如果那时，说了不同的话，结果是否不一样？**

大多数人在一段关系结束后的回望里，都曾被同一个问题击中过：  
**如果那一天，在那个关键节点，我说了另一句话，我们两个人的故事，会不会走向不同的结局？**

这个项目想做的，正是把这种迟来的反问，变成一次可以被认真推演的实验。它让用户回到某个**真实发生过的聊天时间点**，只改动自己说过的一句话，并在**绝不泄漏未来信息**的前提下，结合该节点之前已经发生的关系历史、话题脉络与互动状态，推演对方可能会如何回应，以及这段对话后续可能会如何分支发展。

它不是普通的聊天分析器，也不是单纯的“聊天对象复刻器”。  
它更接近一种**反事实对话模拟**：不是去宣称唯一正确的未来，而是尽可能还原“当时的那个人、当时的那段关系、当时的那个瞬间”，再去回答一个足够残酷、也足够动人的问题：

> **如果那时，真的换了一种说法，一切会不会不同？**

项目当前聚焦于这 3 件事：

- 尽量还原某个时间点下，对方当时的真实状态
- 在不泄漏未来信息的前提下，让用户修改一句自己当时说过的话
- 模拟这句改动是否可能引出不同的回复与后续对话走向

## 当前状态

- 仅支持 `Windows` 本地运行
- 仅支持 `QQ` 私聊文本导入
- 暂无前端页面
- 检索为 `cutoff-safe` 规则检索，不含 embedding
- 短链推演为自动模式，不是交互式续聊

## 核心能力

- 导入 `QQChatExporter V5` 私聊文本
- 解析消息、切段、生成 `normal / isolated / merged_isolated`
- 生成段摘要、多个 topic、人格画像、关系快照
- 按时间截断组装上下文
- 调用真实 LLM 生成首轮回复和自动短链推演
- 提供本地 API、worker 和 CLI 演示脚本

## 环境要求

- Python `3.11+`
- 一个可访问的 OpenAI 兼容聊天接口

说明：

- worker 在分析阶段会调用大模型
- API 在 `/simulations` 阶段也会调用大模型
- API 和 worker 都从项目根目录的 `local_llm_config.py` 读取配置
- 你可以为 API 和 worker 分别配置不同模型

## 安装

在项目根目录执行：

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -e .[dev]
```

可选：指定本地数据目录。默认是项目根目录下的 `.data`。

```powershell
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
```

## 配置模型

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

## 启动

启动 API：

```powershell
cd D:\newProj
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_api.py
```

启动 worker：

```powershell
cd D:\newProj
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_worker.py
```

健康检查：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

期望返回：

```json
{"status":"ok"}
```

## 快速演示

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

直接用 CLI 列出我方文本消息：

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

重点看输出里的：

- `first_reply_text`
- `impact_summary`
- `simulated_turns`

如果只想看第一条回复，可以用：

```powershell
python scripts\sim_cli.py simulate `
  --conversation-id 1 `
  --target-message-id 12 `
  --replacement "如果你现在不想说也没关系，等你愿意的时候我们再慢慢聊。" `
  --mode single_reply `
  --turn-count 1
```

## 常用接口

- `GET /health`
- `POST /imports/qq-text`
- `GET /conversations`
- `GET /conversations/{conversation_id}`
- `GET /jobs/{job_id}`
- `GET /conversations/{conversation_id}/messages`
- `GET /messages/{message_id}`
- `GET /conversations/{conversation_id}/segments`
- `GET /conversations/{conversation_id}/topics`
- `GET /conversations/{conversation_id}/profile`
- `GET /conversations/{conversation_id}/timeline-state?at=...`
- `GET /settings`
- `PUT /settings`
- `POST /simulations`

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

## 项目结构

- `src/if_then_mvp/api.py`
  API 主入口
- `src/if_then_mvp/worker.py`
  后台分析主流程
- `src/if_then_mvp/analysis.py`
  分析阶段 prompt 与 payload
- `src/if_then_mvp/simulation.py`
  推演阶段 prompt 与 payload
- `src/if_then_mvp/retrieval.py`
  cutoff-safe 上下文检索
- `src/if_then_mvp/runtime_llm.py`
  本地 LLM 配置加载
- `scripts/run_api.py`
  API 启动入口
- `scripts/run_worker.py`
  worker 启动入口
- `scripts/sim_cli.py`
  演示 CLI 入口

## 已知限制

- 当前没有桌面壳和前端页面
- 当前只做规则检索，不做 embedding
- 推演模式只有：
  - `single_reply`
  - `short_thread`
- FastAPI 目前仍使用 `on_event("startup")`，测试时会看到弃用 warning，但不影响功能

## 相关文档

- `docs/superpowers/specs/2026-04-05-counterfactual-conversation-mvp-design.md`
- `docs/superpowers/specs/2026-04-06-simulation-llm-alignment-design.md`
- `docs/2026-04-06-agent-handoff.md`
