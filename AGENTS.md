# AGENTS.md

本文档为 Claude Code 和 Codex 等 AI 编程助手提供协作开发规范，确保多个 agent 在同一项目中高效协作。

## 协作原则

### 1. 文档优先级

在开始任何工作前，按以下顺序阅读文档：

1. **AGENTS.md**（本文档）- 协作规范
2. **plan/TODO.md** - 项目待办事项（必读）
3. **CLAUDE.md** - 项目技术架构与开发命令
4. **README.md** - 项目概览与快速开始
5. **docs/2026-04-08-milestone-progress-summary.md** - 项目状态与里程碑进度
6. **docs/superpowers/specs/** - 具体功能的设计文档

### 2. 状态同步机制

**在开始工作前必须执行**：

```powershell
# 检查当前分支状态
git status
git log --oneline -10

# 检查测试基线
python -m pytest -q
cd desktop && npm test && npm run typecheck
```

**当前验证基线**（2026-04-12）：
- Python 测试：83 passed
- Desktop 测试：13 files / 104 tests passed
- TypeScript 类型检查：通过
- Desktop 构建：通过

### 3. 任务管理机制

**任务文件**：`plan/TODO.md`

项目使用单一 TODO 文件管理所有待办事项，按优先级分为 L3（低工作量）、L2（中）、L1（高工作量）。

**任务工作流**：

1. **开始工作前**：查看 `plan/TODO.md`，选择规定任务
2. **任务进行中**：接取任务后，请先在标题打上`已接取`标记，在任务描述中标注进展和遇到的问题
3. **任务完成后**：
   - 在 `plan/TODO.md` 中标记完成或移除该任务
   - 运行完整测试套件验证
4. **发现新需求**：添加到 `plan/TODO.md` 对应优先级分类下

### 4. 工作交接协议

#### 交接前（当前 agent）

1. **运行完整测试套件**，确保所有测试通过
2. **提交所有变更**，使用清晰的 commit message
3. **更新任务状态**：
   - 更新 `plan/TODO.md` 中的任务进度
   - 如果完成任务，标记完成或移除
   - 如果发现新需求，添加到 `plan/TODO.md`
4. **更新文档**：
   - 如果完成了里程碑任务，更新 `docs/2026-04-08-milestone-progress-summary.md`
   - 如果发现重要架构变更，更新 `CLAUDE.md`
5. **记录未完成工作**：
   - 在 `plan/TODO.md` 中标注阻塞原因
   - 在 commit message 中说明未完成的部分

#### 交接后（新 agent）

1. **阅读任务清单**：查看 `plan/TODO.md`，了解当前任务状态
2. **阅读最近 commit**：`git log --oneline -10`，理解最近的变更
3. **检查工作区状态**：`git status`，确认工作区干净
4. **运行测试基线**：确认环境正常，测试通过
5. **选择任务**：从 `plan/TODO.md` 选择优先级最高的任务
6. **阅读相关文档**：查看任务相关的设计文档和技术文档

## 开发规范

### 1. 分支策略

**主分支**：`main`
- 始终保持可运行状态
- 所有测试必须通过
- 不允许直接 push 未测试的代码

**功能开发**：
- 小型修改（< 3 个文件）：直接在 `main` 开发，频繁 commit
- 大型功能：使用 git worktree 隔离开发
  ```powershell
  git worktree add .worktrees/feature-name -b feature-name
  ```

### 2. Commit 规范

**Commit message 格式**：
```
<动词> <主语> <补充说明>

<详细说明（可选）>
```

**示例**：
```
Modernize the custom titlebar without disturbing the app body

- Extract titlebar height to CSS variable
- Keep window controls aligned with design spec
```

**动词选择**：
- Add - 新增功能或文件
- Update - 更新现有功能
- Fix - 修复 bug
- Refactor - 重构代码
- Remove - 删除功能或文件
- Document - 更新文档
- Test - 添加或修改测试

### 3. 测试要求

**必须测试的场景**：
- 修改后端代码 → 运行 `python -m pytest -q`
- 修改桌面代码 → 运行 `cd desktop && npm test && npm run typecheck`
- 修改 API 接口 → 手动测试接口或添加集成测试
- 修改 UI 组件 → 启动开发服务器手动验证

**测试文件位置**：
- 后端测试：`tests/test_*.py`
- 桌面测试：`desktop/tests/*.test.ts` 或 `*.test.tsx`

### 4. 代码风格

**Python**：
- 使用 type hints
- 遵循 PEP 8
- 函数和类使用 docstring（仅在复杂逻辑时）

**TypeScript**：
- 使用严格类型检查
- 优先使用函数式组件（React）
- 避免 `any` 类型

**通用原则**：
- 最小化变更范围
- 不要重构无关代码
- 不要添加未要求的功能
- 保持代码简洁，避免过度抽象

## 架构约束

### 1. 后端架构

**不可变更的核心约束**：
- 数据库：SQLite（不要切换到其他数据库）
- API 框架：FastAPI
- ORM：SQLAlchemy
- 数据目录：通过 `IF_THEN_DATA_DIR` 环境变量配置

**可扩展的部分**：
- 新增 API 端点
- 新增数据库模型（需要同步更新 schema）
- 新增分析阶段（在 `worker.py` 中扩展）

### 2. 桌面架构

**不可变更的核心约束**：
- 桌面框架：Electron
- UI 框架：React 19
- 构建工具：Vite
- 样式方案：Tailwind CSS 4
- 窗口模式：Frameless window + custom titlebar

**可扩展的部分**：
- 新增 UI 组件
- 新增 IPC 通道
- 新增页面或模态框

### 3. 时间安全约束

**关键原则**：所有上下文检索必须遵守 cutoff-safe 原则

- 推演时不能使用目标消息之后的任何信息
- `retrieval.py` 中的 `build_context_pack` 是唯一的上下文组装入口
- 修改上下文逻辑时必须保证时间截断正确性

## 常见任务指南

### 1. 添加新的 API 端点

```python
# 1. 在 src/if_then_mvp/api.py 添加路由
@app.get("/new-endpoint")
async def new_endpoint():
    # 实现逻辑
    pass

# 2. 在 src/if_then_mvp/schemas.py 添加 Pydantic schema（如需要）
class NewEndpointResponse(BaseModel):
    field: str

# 3. 在 tests/ 添加测试
def test_new_endpoint(client):
    response = client.get("/new-endpoint")
    assert response.status_code == 200
```

### 2. 添加新的分析阶段

```python
# 1. 在 src/if_then_mvp/analysis.py 添加 prompt 和 payload builder
def build_new_analysis_payload(...):
    # 构建 LLM payload
    pass

# 2. 在 src/if_then_mvp/worker.py 的 run_analysis_job 中添加阶段
# 3. 在 src/if_then_mvp/models.py 添加新的 ORM 模型（如需要）
# 4. 在 tests/test_analysis.py 添加测试
```

### 3. 添加新的 UI 组件

```typescript
// 1. 在 desktop/src/components/ 创建组件
export function NewComponent() {
  return <div>...</div>;
}

// 2. 在 desktop/tests/ 添加测试
describe('NewComponent', () => {
  it('renders correctly', () => {
    // 测试逻辑
  });
});

// 3. 在需要的地方导入使用
```

### 4. 修改 LLM Prompt

```python
# 1. 在 src/if_then_mvp/analysis.py 或 simulation.py 中找到对应 prompt
# 2. 修改 prompt 文本
# 3. 运行相关测试确保 payload 结构未破坏
# 4. 手动测试推演结果是否符合预期
```

## 冲突解决

### 1. 代码冲突

如果发现其他 agent 正在修改相同文件：

1. **检查最近的 commit**：`git log --oneline -20`
2. **理解变更意图**：阅读 commit message 和 diff
3. **协调变更**：
   - 如果是独立功能，考虑重构以减少耦合
   - 如果是相同功能，基于最新代码继续开发

### 2. 测试冲突

如果测试失败：

1. **确认是否是自己的变更导致**：`git diff`
2. **检查测试基线**：对比 AGENTS.md 中的基线数字
3. **修复测试**：
   - 如果是测试过时，更新测试
   - 如果是代码问题，修复代码
4. **更新基线**：如果测试数量变化，更新 AGENTS.md

### 3. 架构冲突

如果发现架构变更与文档不符：

1. **优先信任代码**：代码是真实状态
2. **更新文档**：修正 CLAUDE.md 或 AGENTS.md
3. **记录原因**：在 commit message 中说明为何架构变更

## 质量检查清单

在提交代码前，确认以下检查项：

- [ ] 所有测试通过（Python + Desktop）
- [ ] TypeScript 类型检查通过
- [ ] 代码符合项目风格
- [ ] 没有引入新的 warning（除非有充分理由）
- [ ] Commit message 清晰描述变更
- [ ] 相关文档已更新（如有架构变更）
- [ ] 没有提交敏感信息（API key、密码等）
- [ ] 没有提交本地配置文件（`local_llm_config.py`）
- [ ] **任务状态已更新**（`plan/TODO.md`）
- [ ] **如有新需求，已添加到 `plan/TODO.md`**

## 紧急情况处理

### 1. 测试全部失败

```powershell
# 检查环境
python --version  # 应该是 3.11+
node --version    # 应该是 20+

# 重新安装依赖
pip install -e .[dev]
cd desktop && npm install

# 检查数据目录
$env:IF_THEN_DATA_DIR = "D:\newProj\.data"
```

### 2. 桌面应用无法启动

```powershell
# 检查后端是否运行
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/health"

# 重新构建 Electron
cd desktop
npm run build:electron

# 检查环境变量
$env:IF_THEN_DESKTOP_RENDERER_URL = "http://127.0.0.1:5173"
```

### 3. Git 状态混乱

```powershell
# 查看当前状态
git status
git log --oneline -10

# 如果需要回退
git reset --hard HEAD  # 警告：会丢失未提交的变更

# 如果需要清理 worktree
git worktree list
git worktree remove .worktrees/feature-name
```

## 项目特定注意事项

### 1. 中文内容

- UI 文本使用中文
- LLM prompt 使用中文
- 代码注释和文档可以使用中文或英文
- Commit message 使用英文

### 2. Windows 环境

- 所有命令示例使用 PowerShell 语法
- 路径使用反斜杠 `\`（在代码中使用 `Path` 对象处理）
- 测试在 Windows 环境下运行

### 3. LLM 依赖

- 开发和测试需要配置 LLM 接口
- 测试使用 mock LLM client
- 不要在测试中调用真实 LLM（除非是集成测试）

### 4. 数据隐私

- 不要在 commit 中包含真实聊天记录
- 测试数据使用 `tests/fixtures/` 中的示例数据
- `local_llm_config.py` 已在 `.gitignore` 中

## 文档维护

### 何时更新 AGENTS.md

- 测试基线数字变化
- 新增重要开发规范
- 架构约束变更
- 新增常见任务类型

### 何时更新 CLAUDE.md

- 新增开发命令
- 架构模块变更
- 新增关键配置项
- 项目限制变化

### 何时创建新的设计文档

- 开始新的里程碑功能
- 重大架构重构
- 复杂的 prompt 工程变更

文档命名格式：`docs/superpowers/specs/YYYY-MM-DD-feature-name-design.md`

## 协作最佳实践

1. **查看任务清单**：每次开始工作前先查看 `plan/TODO.md`
2. **频繁 commit**：小步快跑，每个 commit 只做一件事
3. **清晰沟通**：通过 commit message 和任务更新传递意图
4. **保持同步**：定期 pull 最新代码，避免大规模冲突
5. **测试先行**：修改代码前先运行测试，确保基线正确
6. **文档同步**：代码变更后立即更新相关文档和任务状态
7. **最小变更**：只修改必要的代码，避免连带重构
8. **任务驱动**：所有工作应该对应 `plan/TODO.md` 中的某个任务
9. **及时更新**：完成任务后立即更新 `plan/TODO.md`
10. **保持谦逊**：如果不确定，查阅文档或保留原有实现

---

**最后更新**：2026-04-12  
**维护者**：项目协作 agents  
**版本**：1.1
