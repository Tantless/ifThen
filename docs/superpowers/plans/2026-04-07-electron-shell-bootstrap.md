# Electron Shell Bootstrap Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在现有 Python 后端之上落地一个可运行的 Electron Windows 桌面壳，自动拉起 API / worker，并提供最小可用桌面窗口与 bridge 能力，为后续 React 产品壳改造打通 M2。

**Architecture:** 在仓库内新增 `desktop/` 前端工作区，采用 Electron 主进程 + preload bridge + React renderer 的三层结构。Electron 主进程负责拉起和关闭 Python API / worker、轮询 `/health`、向 renderer 暴露服务状态；renderer 本阶段只实现启动态与最小窗口骨架，不提前进入完整产品交互改造。

**Tech Stack:** Electron, React, TypeScript, Vite, Vitest, Python FastAPI backend

---

## 执行状态（2026-04-08 同步）

- 状态：**已完成并已并入 `main`**
- 结果：`desktop/` 工作区、Electron 主进程、preload bridge、API/worker 启动与健康检查链路都已落地。
- 当前验证参考：`cd desktop && npm test` 为 `9 files / 46 tests passed`，`npm run typecheck` / `npm run build` 通过。
- 说明：下方 `- [ ]` 复选框保留为原始执行脚本，不再表示当前待办；当前总体进度以 `docs/2026-04-08-milestone-progress-summary.md` 为准。

**Scope Note:** 本计划只覆盖桌面宿主层（M2）。`D:\frontUI\src` 当前仅作为视觉/布局参考来源，本计划不会完成完整前端产品接线；那部分将在后续单独计划中处理。

## File Map

### Existing files to modify

- `README.md`
  - 增加桌面工作区开发方式、Electron 启动命令、开发期依赖说明。
- `pyproject.toml`
  - 若需要补充更稳定的 API/worker 启动入口说明，仅做最小文档级修改；不改 Python 包结构。

### New files to create

- `desktop/package.json`
  - Electron + Vite + React 工作区依赖与脚本。
- `desktop/tsconfig.json`
  - renderer TypeScript 配置。
- `desktop/tsconfig.node.json`
  - Electron main/preload 与 Vitest 的 Node 侧 TS 配置。
- `desktop/vite.config.ts`
  - React renderer 的 Vite 配置。
- `desktop/index.html`
  - renderer 入口 HTML。
- `desktop/src/main.tsx`
  - React renderer 启动入口。
- `desktop/src/App.tsx`
  - 本阶段桌面壳根组件，展示 boot screen 与最小 shell 占位。
- `desktop/src/styles.css`
  - renderer 基础样式。
- `desktop/src/types/desktop.d.ts`
  - `window.desktop` bridge 类型声明。
- `desktop/src/lib/desktop.ts`
  - renderer 侧 bridge 调用封装。
- `desktop/src/components/BootScreen.tsx`
  - 后端启动/健康检查状态界面。
- `desktop/src/components/DesktopShellPlaceholder.tsx`
  - 最小三栏桌面骨架占位，明确后续前端接入边界。
- `desktop/electron/main.ts`
  - Electron 主进程入口，创建窗口并管理后端子进程。
- `desktop/electron/preload.ts`
  - 通过 `contextBridge` 暴露受控 IPC API。
- `desktop/electron/backend/paths.ts`
  - 统一计算 Python、脚本路径、日志目录、data dir。
- `desktop/electron/backend/health.ts`
  - `/health` 轮询与重试逻辑。
- `desktop/electron/backend/processManager.ts`
  - API / worker 生命周期管理。
- `desktop/electron/backend/contracts.ts`
  - 主进程内部状态与 IPC 返回类型。
- `desktop/electron/ipc.ts`
  - IPC channel 注册。
- `desktop/tests/health.test.ts`
  - 健康检查辅助逻辑测试。
- `desktop/tests/processManager.test.ts`
  - 路径解析与状态转换测试。
- `desktop/README.md`
  - desktop 工作区本地开发说明。

## Task 1: Scaffold the Desktop Workspace

**Files:**
- Create: `desktop/package.json`
- Create: `desktop/tsconfig.json`
- Create: `desktop/tsconfig.node.json`
- Create: `desktop/vite.config.ts`
- Create: `desktop/index.html`
- Create: `desktop/src/main.tsx`
- Create: `desktop/src/App.tsx`
- Create: `desktop/src/styles.css`
- Create: `desktop/src/types/desktop.d.ts`
- Create: `desktop/src/components/BootScreen.tsx`
- Create: `desktop/src/components/DesktopShellPlaceholder.tsx`
- Create: `desktop/src/lib/desktop.ts`

- [ ] **Step 1: Write the failing test for renderer boot state contract**

```ts
// desktop/tests/health.test.ts
import { describe, expect, it } from 'vitest'
import { getBootLabel } from '../src/lib/desktop'

describe('getBootLabel', () => {
  it('maps waiting-api state to a user-facing label', () => {
    expect(getBootLabel({ phase: 'waiting-api', detail: 'polling /health' })).toBe('正在启动本地分析服务…')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
cd D:\newProj\desktop
npm test -- --run desktop/tests/health.test.ts
```

Expected:

- `Cannot find module '../src/lib/desktop'`
- 或 `getBootLabel is not exported`

- [ ] **Step 3: Add the minimal desktop workspace files and renderer bootstrap**

```json
// desktop/package.json
{
  "name": "if-then-desktop",
  "private": true,
  "version": "0.1.0",
  "type": "module",
  "main": "dist-electron/main.js",
  "scripts": {
    "dev": "vite",
    "build": "vite build && tsc -p tsconfig.node.json",
    "typecheck": "tsc -p tsconfig.json --noEmit && tsc -p tsconfig.node.json --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@types/node": "^24.0.0",
    "@types/react": "^19.0.0",
    "@types/react-dom": "^19.0.0",
    "@vitejs/plugin-react": "^5.0.0",
    "electron": "^37.0.0",
    "typescript": "^5.8.0",
    "vite": "^7.0.0",
    "vitest": "^3.2.0"
  }
}
```

```ts
// desktop/src/lib/desktop.ts
export type BootState = {
  phase: 'booting' | 'starting-api' | 'starting-worker' | 'waiting-api' | 'ready' | 'error'
  detail?: string
}

export function getBootLabel(state: BootState): string {
  switch (state.phase) {
    case 'waiting-api':
    case 'starting-api':
      return '正在启动本地分析服务…'
    case 'starting-worker':
      return '正在启动后台分析进程…'
    case 'ready':
      return '服务已就绪'
    case 'error':
      return '桌面服务启动失败'
    default:
      return '桌面应用正在初始化…'
  }
}
```

```tsx
// desktop/src/App.tsx
import { useMemo } from 'react'
import { BootScreen } from './components/BootScreen'
import { DesktopShellPlaceholder } from './components/DesktopShellPlaceholder'
import { getBootLabel, type BootState } from './lib/desktop'

const initialState: BootState = { phase: 'booting' }

export default function App() {
  const label = useMemo(() => getBootLabel(initialState), [])

  if (initialState.phase !== 'ready') {
    return <BootScreen label={label} detail="等待 Electron 主进程接入…" />
  }

  return <DesktopShellPlaceholder />
}
```

```tsx
// desktop/src/components/BootScreen.tsx
export function BootScreen({ label, detail }: { label: string; detail?: string }) {
  return (
    <main className="boot-screen">
      <div className="boot-card">
        <h1>{label}</h1>
        <p>{detail ?? '应用即将进入主界面'}</p>
      </div>
    </main>
  )
}
```

```tsx
// desktop/src/components/DesktopShellPlaceholder.tsx
export function DesktopShellPlaceholder() {
  return (
    <main className="shell-root">
      <aside className="shell-sidebar">导航栏</aside>
      <section className="shell-list">会话列表</section>
      <section className="shell-content">聊天主视图</section>
    </main>
  )
}
```

- [ ] **Step 4: Run test and typecheck to verify green**

Run:

```powershell
cd D:\newProj\desktop
npm test -- --run desktop/tests/health.test.ts
npm run typecheck
```

Expected:

- `1 passed`
- `typecheck` 无错误

- [ ] **Step 5: Commit**

```powershell
git add desktop/package.json desktop/tsconfig.json desktop/tsconfig.node.json desktop/vite.config.ts desktop/index.html desktop/src/main.tsx desktop/src/App.tsx desktop/src/styles.css desktop/src/types/desktop.d.ts desktop/src/components/BootScreen.tsx desktop/src/components/DesktopShellPlaceholder.tsx desktop/src/lib/desktop.ts desktop/tests/health.test.ts
git commit -m "Create the Electron desktop workspace skeleton" -m "The desktop phase needs its own isolated TypeScript workspace before we can manage Python processes or attach the real React product shell. This commit adds the minimal Electron/React/Vite scaffold and a boot-state renderer contract." -m "Constraint: Keep the first renderer shell intentionally minimal so frontend product refactor stays in a later milestone
Rejected: Copy the full Figma export into the repo immediately | would mix visual migration with process bootstrap concerns
Confidence: high
Scope-risk: moderate
Directive: Do not add product mock data to the desktop workspace; keep M2 focused on shell readiness
Tested: cd desktop; npm test -- --run desktop/tests/health.test.ts; npm run typecheck
Not-tested: Actual Electron window launch"
```

### Task 2: Add Python Backend Process Management in Electron Main

**Files:**
- Create: `desktop/electron/backend/contracts.ts`
- Create: `desktop/electron/backend/paths.ts`
- Create: `desktop/electron/backend/health.ts`
- Create: `desktop/electron/backend/processManager.ts`
- Create: `desktop/electron/main.ts`
- Test: `desktop/tests/processManager.test.ts`

- [ ] **Step 1: Write the failing tests for managed backend state transitions**

```ts
// desktop/tests/processManager.test.ts
import { describe, expect, it } from 'vitest'
import { toManagedServiceState } from '../electron/backend/processManager'

describe('toManagedServiceState', () => {
  it('marks both processes healthy as ready', () => {
    expect(
      toManagedServiceState({
        api: { running: true, healthy: true },
        worker: { running: true, healthy: true },
      }),
    ).toMatchObject({ phase: 'ready' })
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
cd D:\newProj\desktop
npm test -- --run desktop/tests/processManager.test.ts
```

Expected:

- `Cannot find module '../electron/backend/processManager'`

- [ ] **Step 3: Implement the minimal process manager and main process bootstrap**

```ts
// desktop/electron/backend/contracts.ts
export type ServiceState = {
  running: boolean
  healthy: boolean
  pid?: number
  detail?: string
}

export type ManagedServiceState = {
  phase: 'booting' | 'starting-api' | 'starting-worker' | 'waiting-api' | 'ready' | 'error'
  api: ServiceState
  worker: ServiceState
  detail?: string
}
```

```ts
// desktop/electron/backend/processManager.ts
import { spawn, type ChildProcess } from 'node:child_process'
import type { ManagedServiceState, ServiceState } from './contracts'

export function toManagedServiceState(input: { api: ServiceState; worker: ServiceState }): ManagedServiceState {
  if (input.api.running && input.api.healthy && input.worker.running) {
    return { phase: 'ready', api: input.api, worker: input.worker }
  }
  if (input.api.running && !input.api.healthy) {
    return { phase: 'waiting-api', api: input.api, worker: input.worker, detail: 'waiting for /health' }
  }
  if (input.api.running) {
    return { phase: 'starting-worker', api: input.api, worker: input.worker }
  }
  return { phase: 'starting-api', api: input.api, worker: input.worker }
}

export class BackendProcessManager {
  private apiProcess: ChildProcess | null = null
  private workerProcess: ChildProcess | null = null

  startApi(command: string, args: string[], cwd: string, env: NodeJS.ProcessEnv) {
    this.apiProcess = spawn(command, args, { cwd, env, stdio: 'pipe' })
    return this.apiProcess
  }

  startWorker(command: string, args: string[], cwd: string, env: NodeJS.ProcessEnv) {
    this.workerProcess = spawn(command, args, { cwd, env, stdio: 'pipe' })
    return this.workerProcess
  }

  stopAll() {
    this.apiProcess?.kill()
    this.workerProcess?.kill()
  }
}
```

```ts
// desktop/electron/main.ts
import { app, BrowserWindow } from 'electron'

async function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    show: false,
    webPreferences: {
      preload: new URL('./preload.js', import.meta.url).pathname,
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  await win.loadURL(process.env.IF_THEN_DESKTOP_RENDERER_URL ?? 'http://127.0.0.1:5173')
  win.show()
}

app.whenReady().then(createWindow)
app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') app.quit()
})
```

- [ ] **Step 4: Run tests and typecheck**

Run:

```powershell
cd D:\newProj\desktop
npm test -- --run desktop/tests/processManager.test.ts
npm run typecheck
```

Expected:

- `1 passed`
- `typecheck` 无错误

- [ ] **Step 5: Commit**

```powershell
git add desktop/electron/backend/contracts.ts desktop/electron/backend/paths.ts desktop/electron/backend/health.ts desktop/electron/backend/processManager.ts desktop/electron/main.ts desktop/tests/processManager.test.ts
git commit -m "Teach the desktop shell to manage Python backend processes" -m "The Electron shell must own backend startup instead of asking users to run Python manually. This commit adds the first process manager abstraction and main-process window bootstrap for the local API and worker." -m "Constraint: Reuse the existing Python scripts rather than repackaging Python at the M2 milestone
Rejected: Call the API directly from renderer dev tools | would break desktop lifecycle ownership
Confidence: medium
Scope-risk: moderate
Directive: Keep process spawning and health polling in main-process modules, never inside React components
Tested: cd desktop; npm test -- --run desktop/tests/processManager.test.ts; npm run typecheck
Not-tested: Full API/worker child-process launch on a clean Windows machine"
```

### Task 3: Expose a Safe Desktop Bridge and Real Boot Status UI

**Files:**
- Create: `desktop/electron/preload.ts`
- Create: `desktop/electron/ipc.ts`
- Modify: `desktop/electron/main.ts`
- Modify: `desktop/src/lib/desktop.ts`
- Modify: `desktop/src/App.tsx`
- Modify: `desktop/src/components/BootScreen.tsx`
- Test: `desktop/tests/health.test.ts`

- [ ] **Step 1: Write the failing test for bridge-backed boot label flow**

```ts
// desktop/tests/health.test.ts
import { describe, expect, it } from 'vitest'
import { getBootLabel, normalizeDesktopState } from '../src/lib/desktop'

describe('normalizeDesktopState', () => {
  it('turns ipc ready payload into renderer-ready state', () => {
    const state = normalizeDesktopState({ phase: 'ready', detail: 'api healthy' })
    expect(getBootLabel(state)).toBe('服务已就绪')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
cd D:\newProj\desktop
npm test -- --run desktop/tests/health.test.ts
```

Expected:

- `normalizeDesktopState is not exported`

- [ ] **Step 3: Implement preload + IPC + renderer polling**

```ts
// desktop/electron/preload.ts
import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('desktop', {
  getServiceState: () => ipcRenderer.invoke('desktop:get-service-state'),
  getAppInfo: () => ipcRenderer.invoke('desktop:get-app-info'),
  restartBackend: () => ipcRenderer.invoke('desktop:restart-backend'),
})
```

```ts
// desktop/src/lib/desktop.ts
export function normalizeDesktopState(input: { phase: BootState['phase']; detail?: string }): BootState {
  return { phase: input.phase, detail: input.detail }
}

export async function readDesktopServiceState(): Promise<BootState> {
  if (!window.desktop) {
    return { phase: 'booting', detail: 'desktop bridge unavailable' }
  }
  const state = await window.desktop.getServiceState()
  return normalizeDesktopState(state)
}
```

```tsx
// desktop/src/App.tsx
import { useEffect, useMemo, useState } from 'react'
import { BootScreen } from './components/BootScreen'
import { DesktopShellPlaceholder } from './components/DesktopShellPlaceholder'
import { getBootLabel, readDesktopServiceState, type BootState } from './lib/desktop'

export default function App() {
  const [state, setState] = useState<BootState>({ phase: 'booting' })

  useEffect(() => {
    let cancelled = false
    const tick = async () => {
      const next = await readDesktopServiceState()
      if (!cancelled) setState(next)
    }
    void tick()
    const id = window.setInterval(() => void tick(), 1000)
    return () => {
      cancelled = true
      window.clearInterval(id)
    }
  }, [])

  const label = useMemo(() => getBootLabel(state), [state])

  if (state.phase !== 'ready') {
    return <BootScreen label={label} detail={state.detail} />
  }

  return <DesktopShellPlaceholder />
}
```

- [ ] **Step 4: Run tests and verify renderer contract passes**

Run:

```powershell
cd D:\newProj\desktop
npm test -- --run desktop/tests/health.test.ts
npm run typecheck
```

Expected:

- `2 passed`
- `typecheck` 无错误

- [ ] **Step 5: Commit**

```powershell
git add desktop/electron/preload.ts desktop/electron/ipc.ts desktop/electron/main.ts desktop/src/lib/desktop.ts desktop/src/App.tsx desktop/src/components/BootScreen.tsx desktop/tests/health.test.ts
git commit -m "Surface desktop bridge state to the renderer boot flow" -m "The renderer needs a safe way to observe backend readiness without owning process control. This commit exposes a narrow preload bridge and wires the boot screen to real desktop service state." -m "Constraint: Keep Electron security defaults on with contextIsolation enabled
Rejected: Expose raw ipcRenderer to the window object | unnecessary desktop attack surface
Confidence: high
Scope-risk: moderate
Directive: Any new desktop capability must be added as a narrow preload method, never by turning on nodeIntegration
Tested: cd desktop; npm test -- --run desktop/tests/health.test.ts; npm run typecheck
Not-tested: Real IPC timing under packaged production build"
```

### Task 4: Wire Real Python Startup, Health Polling, and Desktop Docs

**Files:**
- Modify: `desktop/electron/backend/paths.ts`
- Modify: `desktop/electron/backend/health.ts`
- Modify: `desktop/electron/backend/processManager.ts`
- Modify: `desktop/electron/main.ts`
- Create: `desktop/README.md`
- Modify: `README.md`

- [ ] **Step 1: Write the failing test for root path resolution**

```ts
// desktop/tests/processManager.test.ts
import { describe, expect, it } from 'vitest'
import { buildPythonLaunchSpec } from '../electron/backend/paths'

describe('buildPythonLaunchSpec', () => {
  it('points to scripts/run_api.py from the repo root', () => {
    const spec = buildPythonLaunchSpec('api', 'D:/newProj')
    expect(spec.args.at(-1)).toBe('scripts/run_api.py')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run:

```powershell
cd D:\newProj\desktop
npm test -- --run desktop/tests/processManager.test.ts
```

Expected:

- `buildPythonLaunchSpec is not exported`

- [ ] **Step 3: Implement repo-root launch specs and health polling integration**

```ts
// desktop/electron/backend/paths.ts
import path from 'node:path'

export function buildPythonLaunchSpec(kind: 'api' | 'worker', repoRoot: string) {
  const script = kind === 'api' ? 'scripts/run_api.py' : 'scripts/run_worker.py'
  return {
    command: 'python',
    args: [path.join(repoRoot, script)],
    cwd: repoRoot,
  }
}
```

```ts
// desktop/electron/backend/health.ts
export async function waitForHealth(url: string, timeoutMs = 15000): Promise<boolean> {
  const started = Date.now()
  while (Date.now() - started < timeoutMs) {
    try {
      const response = await fetch(url)
      if (response.ok) return true
    } catch {}
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  return false
}
```

```md
<!-- desktop/README.md -->
# Desktop Workspace

## Development

```powershell
cd D:\newProj\desktop
npm install
npm run dev
```

Electron 主进程负责拉起：

- `python scripts/run_api.py`
- `python scripts/run_worker.py`

默认通过项目根目录 `.data` 共享数据目录。
```

- [ ] **Step 4: Run focused desktop verification**

Run:

```powershell
cd D:\newProj\desktop
npm test
npm run typecheck
npm run build
```

Expected:

- all Vitest tests pass
- typecheck pass
- Vite renderer build + Electron TS build succeed

- [ ] **Step 5: Run backend regression suite to confirm no Python breakage**

Run:

```powershell
cd D:\newProj
python -m pytest tests/test_runtime_llm.py tests/test_worker.py tests/test_queries.py tests/test_conversation_management.py tests/test_simulations.py -q
```

Expected:

- 全绿

- [ ] **Step 6: Commit**

```powershell
git add desktop/electron/backend/paths.ts desktop/electron/backend/health.ts desktop/electron/backend/processManager.ts desktop/electron/main.ts desktop/README.md README.md
git commit -m "Boot the desktop shell through the real Python backend" -m "The Windows desktop milestone requires Electron to own the existing Python service lifecycle and document how developers run it. This commit wires the shell to the repo's API/worker scripts and documents the desktop workspace." -m "Constraint: M2 must keep using the existing Python runtime entry points before packaged-distribution work starts
Rejected: Package Python into the app immediately | belongs to the later release-preparation milestone
Confidence: medium
Scope-risk: broad
Directive: Do not couple renderer components to localhost URLs; all backend readiness must stay behind the desktop bridge
Tested: cd desktop; npm test; npm run typecheck; npm run build; cd D:\newProj; python -m pytest tests/test_runtime_llm.py tests/test_worker.py tests/test_queries.py tests/test_conversation_management.py tests/test_simulations.py -q
Not-tested: Packaged .exe launch with embedded Python runtime"
```

## Self-Review Checklist

- Spec coverage:
  - Electron 工程骨架：Task 1
  - 主窗口：Task 2
  - 自动启动 Python API / worker：Task 2 + Task 4
  - 健康检查：Task 3 + Task 4
  - 基础 bridge：Task 3
- Placeholder scan:
  - 无 `TODO` / `TBD` / “类似前面任务” 的占位
- Type consistency:
  - `BootState` / `ManagedServiceState` / preload bridge 方法命名在任务间保持一致
