# 后端 Deprecated Warning 清理设计

日期：2026-04-08

## 1. 目标

清理当前后端测试过程中最显眼的一类 deprecated warning，使后端 API 在现有功能不变的前提下，切换到 FastAPI 当前推荐的生命周期写法。

本轮目标非常明确：

- 保持现有 API 行为不变
- 消除由 `@app.on_event("startup")` 引发的 FastAPI `DeprecationWarning`
- 保持现有后端测试通过
- 不把这次修复扩展成额外的框架升级或后端重构

---

## 2. 问题现状

当前运行后端测试：

```powershell
python -m pytest -q
```

测试本身可以通过，但会出现大量 warning 汇总。已确认的 warning 来源为：

- `src/if_then_mvp/api.py`
- `create_app()` 内部使用了 `@app.on_event("startup")`

FastAPI 当前已明确将 `on_event` 标记为 deprecated，并推荐改用 `lifespan` 事件处理。

---

## 3. 已确认根因

### 3.1 直接根因

在 `create_app()` 中：

- 应用启动时通过 `@app.on_event("startup")` 调用 `init_db()`
- 该写法在当前 FastAPI 版本中会触发 `DeprecationWarning`

### 3.2 验证环境注意事项

当前本机 Python editable install 指向：

```text
D:\newProj\.worktrees\desktop-backend-productization\src
```

因此如果直接在别的 worktree 中运行 `python -m pytest`，解释器可能会优先导入另一个 worktree 的包路径，而不是当前 checkout。

这说明两件事：

1. warning 的代码级根因仍然成立；
2. 本轮修复在验证时必须显式确保测试命中当前 worktree 的 `src`。

这项环境问题本身**不是本轮主要交付物**，但在实施与验证时必须被正视。

---

## 4. 设计边界

### 4.1 本轮包含

- 将 `create_app()` 的启动初始化从 `on_event("startup")` 迁移到 FastAPI 推荐的 lifespan 机制
- 增加最小回归测试，确保应用启动时不再抛出对应 deprecated warning
- 重新运行后端相关测试，确认行为与接口契约未回归

### 4.2 本轮不包含

- 全量清理所有第三方 warning
- 升级 FastAPI / Starlette / SQLAlchemy 大版本
- 重构 API 路由结构
- 修改 Electron / desktop renderer
- 处理 editable install 指向其他 worktree 的通用开发体验问题

---

## 5. 方案比较

### 方案 A：仅在测试里过滤 warning

做法：

- 通过 pytest warning filter 隐藏 `on_event` 的 warning

问题：

- 只是掩盖症状，没有修复根因
- 后续框架继续升级时风险仍在

结论：

- 不采用

### 方案 B：把 startup 初始化迁移到 lifespan

做法：

- 在 `create_app()` 中定义 lifespan context
- 在应用进入 lifespan 时执行 `init_db()`
- 保持现有路由与依赖关系不变

优点：

- 与 FastAPI 官方推荐一致
- 改动面小
- 易于验证

风险：

- 需要确认 `TestClient(create_app())` 场景下初始化仍然按预期执行

结论：

- **采用该方案**

### 方案 C：立即做更大范围的应用初始化重构

做法：

- 借机抽象完整 app factory / runtime bootstrap 层

问题：

- 超出本轮目标
- 风险和改动面明显增大

结论：

- 不采用

---

## 6. 核心设计结论

本轮采用：

> **用 FastAPI lifespan 替换 `@app.on_event("startup")`，在不改变现有 API 语义的前提下清除 deprecated warning。**

设计要求：

- `init_db()` 仍在应用启动期执行
- `TestClient` 场景下仍能正常初始化数据库
- 新增测试应直接锁定“不会再产生该 warning”这一结果，而不是仅靠人工观察 pytest 输出

---

## 7. 影响范围

重点文件：

- `src/if_then_mvp/api.py`
- `tests/test_health.py`

可能需要重跑的测试：

- `tests/test_health.py`
- `tests/test_imports.py`
- `tests/test_queries.py`
- `tests/test_conversation_management.py`
- `tests/test_simulations.py`
- 最终 `python -m pytest -q`

---

## 8. 验证策略

### 8.1 定向验证

先验证最小回归面：

- 健康检查可用
- `TestClient(create_app())` 不再触发 `on_event` deprecated warning

### 8.2 回归验证

再验证依赖 app startup / DB 初始化的主要后端测试。

### 8.3 完整验证

最后执行全量 pytest，并确认：

- 测试继续通过
- 原先这类 FastAPI `on_event` warning 不再出现

---

## 9. 设计结论

这不是一次“隐藏 warning”的清理，而是一次**对齐当前框架推荐写法的最小修复**。

本轮完成后，应达到：

- 后端应用生命周期写法不再使用已弃用接口
- pytest 输出中的对应 warning 被实际消除
- 现有后端能力与桌面前端集成契约不受影响
