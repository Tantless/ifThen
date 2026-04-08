# Backend Deprecation Warning Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 用最小改动把 FastAPI `on_event("startup")` 的 deprecated warning 从后端测试路径中移除，同时保持现有 API 行为与测试结果稳定。

**Architecture:** 保持当前 `create_app()` 工厂与路由注册方式不变，只把数据库初始化入口从 `startup` 事件迁移到 FastAPI 官方推荐的 lifespan context。测试通过 `warnings.catch_warnings()` 锁定不再出现对应 warning，并在验证时显式让 Python 导入当前 worktree 的 `src`，避免 editable install 指向其他 worktree 干扰结果。

**Tech Stack:** Python, FastAPI, pytest, TestClient

---

## 执行状态（2026-04-08 同步）

- 状态：**已完成并已并入 `main`**
- 结果：FastAPI startup 初始化已从 `@app.on_event("startup")` 迁移到 lifespan，目标 deprecated warning 已完成清理并补上回归测试。
- 当前验证参考：`python -m pytest -q` 在 `main` 上为 `71 passed`。
- 说明：下方 `- [ ]` 复选框保留为原始执行脚本，不再表示当前待办；当前总体进度以 `docs/2026-04-08-milestone-progress-summary.md` 为准。

## File Map

### Existing files to modify
- `src/if_then_mvp/api.py`
- `tests/test_health.py`

### Files explicitly out of scope
- `desktop/**`
- `src/if_then_mvp/worker.py`
- `src/if_then_mvp/runtime_llm.py`
- packaging / editable install 机制本身

---

### Task 1: 用回归测试锁定 deprecated warning 清理目标

**Files:**
- Modify: `tests/test_health.py`

- [ ] **Step 1: 扩展健康检查测试，加入 warning 回归断言**

```python
import warnings

from fastapi.testclient import TestClient

from if_then_mvp.api import create_app


def test_health_returns_ok(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path))
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


def test_create_app_does_not_emit_fastapi_on_event_deprecation_warning(tmp_path, monkeypatch):
    monkeypatch.setenv("IF_THEN_DATA_DIR", str(tmp_path))

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with TestClient(create_app()) as client:
            response = client.get("/health")

    assert response.status_code == 200
    messages = [
        str(item.message)
        for item in caught
        if issubclass(item.category, DeprecationWarning)
    ]
    assert not any("on_event is deprecated" in message for message in messages)
```

- [ ] **Step 2: 先运行定向测试，确认新断言当前失败**

Run:

```powershell
cd D:\newProj\.worktrees\electron-shell-bootstrap
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pytest tests/test_health.py -q
```

Expected:
- `test_health_returns_ok` 通过
- 新 warning 回归测试失败，证明当前确实仍在走 deprecated 路径

- [ ] **Step 3: 提交前不要实现修复，先确认失败原因就是目标 warning**

预期失败点：
- 断言捕获到了包含 `on_event is deprecated` 的 `DeprecationWarning`

---

### Task 2: 把应用启动初始化迁移到 lifespan

**Files:**
- Modify: `src/if_then_mvp/api.py`

- [ ] **Step 1: 为 FastAPI app factory 引入 lifespan context**

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI, File, Form, HTTPException, Query, Response, UploadFile
```

- [ ] **Step 2: 用 lifespan 承接 `init_db()`，移除 `@app.on_event("startup")`**

```python
@asynccontextmanager
async def app_lifespan(_app: FastAPI):
    init_db()
    yield


def create_app(*, llm_client: ChatJSONClient | None = None) -> FastAPI:
    app = FastAPI(title="If Then MVP API", lifespan=app_lifespan)
```

要求：
- 删除原 `@app.on_event("startup")` 块
- 其余路由定义保持不变
- 不把 `init_db()` 挪到模块导入时执行

- [ ] **Step 3: 运行健康检查测试，确认回归测试转绿**

Run:

```powershell
cd D:\newProj\.worktrees\electron-shell-bootstrap
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pytest tests/test_health.py -q
```

Expected:
- 2 tests passed
- warning 回归测试不再失败

---

### Task 3: 扩大回归面并确认 warning 清理完成

**Files:**
- Verify: `tests/test_imports.py`
- Verify: `tests/test_queries.py`
- Verify: `tests/test_conversation_management.py`
- Verify: `tests/test_simulations.py`

- [ ] **Step 1: 跑依赖 app startup 的 focused backend suite**

Run:

```powershell
cd D:\newProj\.worktrees\electron-shell-bootstrap
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pytest tests/test_health.py tests/test_imports.py tests/test_queries.py tests/test_conversation_management.py tests/test_simulations.py -q
```

Expected:
- 全部通过
- 不再出现 `on_event is deprecated` warning

- [ ] **Step 2: 跑全量 pytest**

Run:

```powershell
cd D:\newProj\.worktrees\electron-shell-bootstrap
$env:PYTHONPATH = (Resolve-Path .\src).Path
python -m pytest -q
```

Expected:
- 全量通过
- 不再出现 FastAPI `on_event` deprecation warning

- [ ] **Step 3: 检查工作树仅包含本轮 warning 清理相关改动**

Run:

```powershell
git -C D:\newProj\.worktrees\electron-shell-bootstrap status --short
```

Expected:
- 仅出现 `src/if_then_mvp/api.py`
- `tests/test_health.py`
- `docs/superpowers/specs/2026-04-08-backend-deprecation-warning-cleanup-design.md`
- `docs/superpowers/plans/2026-04-08-backend-deprecation-warning-cleanup.md`

- [ ] **Step 4: 提交**

```powershell
git add src/if_then_mvp/api.py tests/test_health.py docs/superpowers/specs/2026-04-08-backend-deprecation-warning-cleanup-design.md docs/superpowers/plans/2026-04-08-backend-deprecation-warning-cleanup.md
git commit -m "Stop backend startup from relying on deprecated FastAPI hooks" -m "FastAPI has deprecated on_event startup hooks, so the app factory now initializes the database via lifespan and locks the behavior with a focused regression test.

Constraint: Must keep create_app startup behavior unchanged for existing TestClient-based backend tests
Rejected: Filter the warning in pytest | would hide the symptom instead of fixing the deprecated API usage
Confidence: high
Scope-risk: narrow
Directive: Keep database initialization in the application lifespan, not at module import time
Tested: python -m pytest tests/test_health.py -q; python -m pytest tests/test_health.py tests/test_imports.py tests/test_queries.py tests/test_conversation_management.py tests/test_simulations.py -q; python -m pytest -q
Not-tested: Non-pytest production boot paths outside current FastAPI/TestClient startup coverage"
```

---

## Self-Review Checklist

- Spec coverage:
  - root cause 明确：`on_event("startup")`
  - 采用 lifespan 替代
  - warning 清理有自动化断言
  - 全量 pytest 回归保留
- Placeholder scan:
  - 无 TBD / TODO / “类似前一任务”
- Type consistency:
  - `create_app()` 工厂接口不变
  - `TestClient(create_app())` 使用方式不变
  - 验证命令统一显式使用当前 worktree `src`
