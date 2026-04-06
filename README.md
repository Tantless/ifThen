# If Then MVP

基于 QQ 私聊导出文本的反事实聊天推演 MVP。

当前版本先提供本地 API 和后台 worker，用来验证这条主链是否成立：

- 导入 `QQChatExporter V5` 私聊文本
- 异步完成解析、切段、摘要、主题、画像、关系快照
- 查询消息与分析产物
- 选择一条历史消息进行改写，并自动推演后续对话分支

## 当前范围

- 仅支持 Windows 本地运行
- 仅支持 QQ 私聊文本导入
- 暂无前端页面
- 检索为 cutoff-safe 规则检索，不含 embedding
- 短链推演为自动模式，不是交互式续聊

## 环境要求

- Python `3.11+`
- 一个可访问的 OpenAI 兼容聊天接口

说明：

- worker 在分析阶段会调用大模型
- API 在 `/simulations` 阶段也会调用大模型
- 两个进程都从项目根目录的 [local_llm_config.py](D:/newProj/local_llm_config.py) 读取模型配置
- 你可以为 API 和 worker 分别配置不同的模型

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

## 本地启动

先基于示例文件创建本地模型配置文件：

```powershell
Copy-Item local_llm_config.example.py local_llm_config.py
```

然后编辑 [local_llm_config.py](D:/newProj/local_llm_config.py)：

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

再开 API：

```powershell
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_api.py
```

再开 worker：

```powershell
.venv\Scripts\Activate.ps1
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
python scripts\run_worker.py
```

启动后可先检查健康状态：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

期望返回：

```json
{"status":"ok"}
```

## 一次完整演示

下面这组命令适合直接在 PowerShell 里跑通一条最小闭环。

### 1. 导入聊天记录

把 `self_display_name` 改成聊天记录里“你自己”的昵称。

```powershell
curl.exe -X POST "http://127.0.0.1:8000/imports/qq-text" `
  -F "self_display_name=Tantless" `
  -F "file=@C:\Users\Tantless\Desktop\聊天记录.txt;type=text/plain"
```

返回结果会包含：

- `conversation.id`
- `job.id`

你后面会一直用到这两个值。

### 2. 轮询分析任务状态

假设刚才拿到的任务 ID 是 `1`：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/jobs/1"
```

当返回里出现：

- `status = completed`
- `current_stage = completed`

说明分析已经跑完，可以进入查询和推演。

### 3. 查看会话列表

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/conversations"
```

### 4. 浏览消息，找到要改写的 `message_id`

假设会话 ID 是 `1`：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/conversations/1/messages?limit=20"
```

你会看到每条消息的：

- `id`
- `sequence_no`
- `speaker_role`
- `timestamp`
- `content_text`

建议挑一条 `speaker_role = self` 的消息作为改写目标。

如果消息很多，也可以先按关键词过滤：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/conversations/1/messages?keyword=晚安"
```

现在也可以直接用脚本列候选消息：

```powershell
python scripts\sim_cli.py list-self-text --conversation-id 1 --limit 20
```

如果你只想看包含某个关键词的我方文本消息：

```powershell
python scripts\sim_cli.py list-self-text --conversation-id 1 --keywords "你好" --limit 20
```

### 5. 看一下切段和画像

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/conversations/1/segments"
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/conversations/1/topics"
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/conversations/1/profile"
```

如果你想看某个时间点之前的关系状态：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/conversations/1/timeline-state?at=2025-03-02 20:30:00"
```

### 6. 发起一次改写推演

假设：

- `conversation_id = 1`
- `target_message_id = 12`

下面例子会自动推演 4 轮：

```powershell
python scripts\sim_cli.py simulate `
  --conversation-id 1 `
  --target-message-id 12 `
  --replacement "如果你现在不想说也没关系，等你愿意的时候我们再慢慢聊。" `
  --mode short_thread `
  --turn-count 4
```

返回结果里最值得先看的字段是：

- `first_reply_text`
- `impact_summary`
- `simulated_turns`

如果你只想看第一条回复，可以把 `mode` 改成 `single_reply`。

注意：`/simulations` 现在会真实调用 LLM，不再使用占位回复。  
如果 [local_llm_config.py](D:/newProj/local_llm_config.py) 缺失或字段不完整，API 或 worker 启动时会直接报错。

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

## 数据存放位置

程序会把数据放在 `IF_THEN_DATA_DIR` 对应目录下，默认是项目根目录 `.data`。

通常会看到这些内容：

- `db/`
  - SQLite 数据库
- `uploads/`
  - 导入的原始聊天文本

如果你显式设置了：

```powershell
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
```

那数据就会写到 `D:\newProj\.data`。

## 已知限制

- 现在没有桌面壳和前端页面
- API 和 worker 当前都通过 [local_llm_config.py](D:/newProj/local_llm_config.py) 读取本地模型配置
- 当前只做规则检索，不做 embedding
- 推演模式只有：
  - `single_reply`
  - `short_thread`
- FastAPI 目前仍使用 `on_event("startup")`，启动测试时会看到弃用 warning，但不影响功能

## 代码入口

- API 启动入口：[scripts/run_api.py](D:/newProj/scripts/run_api.py)
- Worker 启动入口：[scripts/run_worker.py](D:/newProj/scripts/run_worker.py)
- 推演 CLI：[scripts/sim_cli.py](D:/newProj/scripts/sim_cli.py)
- API 主体：[src/if_then_mvp/api.py](D:/newProj/src/if_then_mvp/api.py)
- Worker 主体：[src/if_then_mvp/worker.py](D:/newProj/src/if_then_mvp/worker.py)
- CLI 主体：[src/if_then_mvp/sim_cli.py](D:/newProj/src/if_then_mvp/sim_cli.py)
- 数据目录配置：[src/if_then_mvp/config.py](D:/newProj/src/if_then_mvp/config.py)
