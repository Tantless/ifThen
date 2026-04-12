# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 重要提示

**开始工作前必读**：
1. 查看 `plan/TODO.md` 了解当前待办任务
2. 查看 `AGENTS.md` 了解协作规范
3. 运行测试基线确认环境正常

## Project Overview

"如果那时" (If Then) is a counterfactual conversation simulator that allows users to revisit past chat conversations and explore alternative outcomes by rewriting specific messages. The system analyzes relationship history, context, and interaction patterns to simulate how conversations might have unfolded differently.

**Architecture**: Hybrid Python backend + Electron desktop application
- Backend: FastAPI REST API + background worker for LLM-powered analysis
- Frontend: Electron frameless shell with React + TypeScript UI
- Data: SQLite database with conversation history, analysis artifacts, and simulations

## Development Commands

### Python Backend

**Setup**:
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e .[dev]
```

**Testing**:
```powershell
python -m pytest -q                    # Run all tests (86 tests)
python -m pytest tests/test_*.py       # Run specific test file
python -m pytest -k "test_name"        # Run tests matching pattern
```

**Running Backend Services**:
```powershell
# Start API server (port 8000)
python scripts\run_api.py

# Start background worker (separate terminal)
python scripts\run_worker.py

# Health check
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"
```

**CLI Simulation Tool**:
```powershell
# List rewritable messages
python scripts\sim_cli.py list-self-text --conversation-id 1 --limit 20

# Run simulation
python scripts\sim_cli.py simulate --conversation-id 1 --target-message-id 12 --replacement "新的消息内容" --mode short_thread --turn-count 4
```

### Desktop Application

**Setup**:
```powershell
cd desktop
npm install
```

**Testing**:
```powershell
cd desktop
npm test                               # Run all tests (13 files / 110 tests)
npm run typecheck                      # Type check all TypeScript
```

**Development Mode**:
```powershell
# Terminal 1: Start Vite dev server
cd desktop
npm run dev

# Terminal 2: Build Electron main/preload (first time or after changes)
cd desktop
npm run build:electron

# Terminal 2: Launch Electron
cd desktop
$env:IF_THEN_DESKTOP_RENDERER_URL = "http://127.0.0.1:5173"
npx electron .
```

**Production Build**:
```powershell
cd desktop
npm run build                          # Builds both renderer and Electron
npx electron .                         # Run production build
```

## Configuration

### LLM Configuration

The system requires an OpenAI-compatible chat endpoint. Configuration priority:
1. Settings stored in database (`/settings` API endpoint)
2. Environment variables: `IF_THEN_LLM_BASE_URL`, `IF_THEN_LLM_API_KEY`, `IF_THEN_LLM_CHAT_MODEL`
3. `local_llm_config.py` in project root (copy from `local_llm_config.example.py`)

Both API and worker share the same configuration resolution logic via `runtime_llm.py`.

Simulation requests can optionally override the analysis endpoint by setting
`llm.simulation_base_url`, `llm.simulation_api_key`, and `llm.simulation_model`
in `/settings`, or `IF_THEN_LLM_SIMULATION_BASE_URL`,
`IF_THEN_LLM_SIMULATION_API_KEY`, and `IF_THEN_LLM_SIMULATION_MODEL` in the
environment. Any empty simulation-specific field falls back to the analysis
(`llm.*`) value.

### Data Directory

Set `IF_THEN_DATA_DIR` environment variable to specify data location (defaults to `.data/` in project root):
```powershell
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
```

Data structure:
- `db/` - SQLite database files
- `uploads/` - Imported chat text files

## Architecture Details

### Backend Pipeline

**Import → Parse → Analyze → Simulate**

1. **Import** (`api.py`): Accepts QQ chat export text files via `/imports/qq-text`
2. **Parse** (`parser.py`): Extracts messages with timestamps, sender info, and content
3. **Segment** (`segmentation.py`): Groups messages into conversation segments (normal/isolated/merged_isolated)
4. **Analyze** (`worker.py` + `analysis.py`): Background worker generates:
   - Segment summaries
   - Topics and topic links
   - Persona profiles (personality traits, communication style)
   - Relationship snapshots (emotional state, tension levels)
5. **Simulate** (`simulation.py`): Generates counterfactual conversation branches:
   - `single_reply`: Generate only the first response
   - `short_thread`: Auto-generate multi-turn conversation (default 4 turns)

### Context Retrieval

**Cutoff-safe context assembly** (`retrieval.py`):
- Never leaks information from after the target message timestamp
- Assembles context from: segment summaries, topics, persona profile, relationship snapshot
- Ensures simulations only use information available at that point in time

### Desktop Application

**Electron Architecture**:
- **Main process** (`desktop/electron/main.ts`): Window management, backend lifecycle
- **Backend manager** (`desktop/electron/backend/`): Auto-starts Python API + worker, health checks
- **Preload** (`desktop/electron/preload.cts`): IPC bridge between renderer and main
- **Renderer** (`desktop/src/`): React UI with frontUI visual system

**Backend Lifecycle**:
1. Electron detects `.venv` Python in project root
2. Spawns `python scripts/run_api.py`
3. Polls `/health` endpoint until ready
4. Spawns `python scripts/run_worker.py`
5. Desktop UI connects to `http://127.0.0.1:8000`

**UI Structure**:
- `frontui/` - Main chat interface (three-column layout: sidebar, chat list, chat window)
- `components/` - Reusable UI components (modals, settings, import flow)
- `lib/` - API client, state management, adapters

### Key Modules

**Backend**:
- `api.py` - FastAPI REST endpoints, simulation orchestration
- `worker.py` - Background analysis job processor
- `analysis.py` - LLM prompts and payloads for analysis stages
- `simulation.py` - LLM prompts for counterfactual generation
- `retrieval.py` - Context assembly with temporal cutoff safety
- `runtime_llm.py` - Unified LLM configuration resolution
- `conversation_lifecycle.py` - Delete conversations, rerun analysis
- `models.py` - SQLAlchemy ORM models
- `schemas.py` - Pydantic request/response schemas

**Desktop**:
- `electron/main.ts` - Electron app entry, window setup
- `electron/backend/processManager.ts` - Python process lifecycle
- `src/App.tsx` - Main React application
- `src/frontui/` - Primary chat UI shell
- `src/lib/apiClient.ts` - Backend API client
- `src/lib/desktopBridge.ts` - IPC communication layer

## Testing Strategy

**Backend**: Pytest with fixtures for database setup, mock LLM clients
- `tests/fixtures/` - Sample chat data for testing
- Tests cover: parsing, segmentation, analysis payloads, API endpoints, worker stages

**Desktop**: Vitest with jsdom for React component testing
- Tests cover: API client, IPC bridge, state management, UI adapters

## Current Limitations

- Only supports QQ private chat text import (QQChatExporter V5 format)
- No embedding-based retrieval (rule-based context assembly only)
- Two simulation modes only: `single_reply` and `short_thread`
- Development-stage desktop app (no installer, auto-update, or release builds)

## Development Notes

- **Windows-only**: Shell scripts use PowerShell syntax
- **Frameless window**: Custom title bar implementation, no native OS chrome
- **Chinese language**: UI and prompts are in Chinese; conversation data expected in Chinese
- **LLM dependency**: Both analysis and simulation require LLM access; no offline mode
- **Temporal safety**: All context retrieval enforces strict timestamp cutoffs to prevent future information leakage

## Task Management

**任务管理文件**：`plan/TODO.md`

项目使用单一 TODO 文件管理所有待办事项，按优先级分为 L1（高工作量）、L2（中工作量）、L3（低工作量）。

**工作流程**：
1. 从 `plan/TODO.md` 选择任务
2. 在任务描述中标注进展
3. 完成后标记完成或移除
4. 发现新需求添加到对应优先级分类下

**当前优先级**（2026-04-12）：
1. Windows 打包发布（L1）
2. 重构项目代码（L1）
3. 迭代任务按 `plan/TODO.md` 中的 L2 / L3 顺序继续推进
4. 设计与实现历史请参考 `docs/project-status.md`

详细任务分解请查看 `plan/TODO.md`。
