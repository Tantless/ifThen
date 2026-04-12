# 微信风格桌面窗口化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前 `desktop` 从“默认 Electron 系统窗口 + 居中网页卡片”推进成“无默认菜单栏、无原生标题栏、自定义标题栏、全窗口铺满”的微信式桌面应用窗口。

**Architecture:** 继续保留现有 Electron 主进程负责后端拉起与窗口创建，React 渲染层负责 frontUI 主界面与标题栏表现。先通过 Electron IPC 暴露窗口控制能力，再在 `frontui` 中落地自定义标题栏和全窗口主壳布局，最后用 App 集成测试锁定无边框窗口化后的行为。

**Tech Stack:** Electron 37, React 19, TypeScript 5, Vite 7, Vitest 3, preload / IPC bridge, frontUI renderer shell

---

## File Structure Map

### Modify
- `desktop/electron/main.ts` — 改为无边框窗口、关闭默认菜单栏、保持现有后端启动链路
- `desktop/electron/ipc.ts` — 新增窗口控制 IPC 通道
- `desktop/electron/preload.cts` — 暴露窗口控制 bridge 给 renderer
- `desktop/src/App.tsx` — 将窗口标题栏与窗口状态接入当前 frontUI 主壳
- `desktop/src/frontui/AppShell.tsx` — 从居中卡片改为全窗口铺满布局
- `desktop/src/styles/frontui.css` — 增加标题栏与全窗口壳所需样式入口
- `desktop/tests/ipc.test.ts` — 增加窗口控制 IPC 测试
- `desktop/tests/desktopBridge.test.ts` — 增加 renderer bridge 侧能力测试
- `desktop/tests/frontUiShell.test.tsx` — 增加标题栏与全窗口布局测试
- `desktop/tests/visualShell.test.tsx` — 增加 App 级窗口化集成测试
- `README.md` — 同步新的开发态观感与启动说明（如有必要）

### Create
- `desktop/src/frontui/WindowTitleBar.tsx` — 微信风格自定义标题栏
- `desktop/src/lib/windowControls.ts` — renderer 对 `desktop.window` bridge 的轻量封装
- `desktop/src/types/desktop.ts` — renderer 侧桌面 bridge 类型声明（含窗口控制）
- `desktop/tests/windowChrome.test.ts` — 主进程窗口配置测试

### Retain
- `desktop/src/components/AnalysisInspector.tsx`
- `desktop/src/components/RewritePanel.tsx`
- `desktop/src/components/BranchView.tsx`

这些组件本阶段继续复用，只调整其在全窗口壳中的挂载位置，不在本计划内做彻底视觉重写。

---

### Task 1: 锁定 Electron 无边框窗口与菜单栏移除行为

**Files:**
- Modify: `desktop/electron/main.ts`
- Create: `desktop/tests/windowChrome.test.ts`

- [ ] **Step 1: 先写主进程窗口配置失败测试**

```ts
import { beforeEach, describe, expect, it, vi } from 'vitest'

const { BrowserWindow, setApplicationMenu } = vi.hoisted(() => ({
  BrowserWindow: vi.fn(() => ({
    loadURL: vi.fn(),
    loadFile: vi.fn(),
    show: vi.fn(),
    on: vi.fn(),
    isMaximized: vi.fn(() => false),
    minimize: vi.fn(),
    maximize: vi.fn(),
    unmaximize: vi.fn(),
    close: vi.fn(),
  })),
  setApplicationMenu: vi.fn(),
}))

vi.mock('electron', () => ({
  app: {
    whenReady: () => Promise.resolve(),
    on: vi.fn(),
    quit: vi.fn(),
  },
  BrowserWindow,
  Menu: { setApplicationMenu },
}))

describe('window chrome configuration', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('creates a frameless desktop window and removes the default menu', async () => {
    const { createWindow } = await import('../electron/main')

    await createWindow()

    expect(BrowserWindow).toHaveBeenCalledWith(
      expect.objectContaining({
        frame: false,
        titleBarStyle: 'hidden',
        show: false,
      }),
    )
    expect(setApplicationMenu).toHaveBeenCalledWith(null)
  })
})
```

- [ ] **Step 2: 运行测试确认当前失败**

Run:

```powershell
cd D:\newProj\desktop
npm test -- windowChrome
```

Expected:
- FAIL，因为当前 `main.ts` 还没有 `frame: false`
- FAIL，因为当前没有移除默认菜单栏

- [ ] **Step 3: 对 `main.ts` 做最小实现，使窗口改成无边框**

更新 `desktop/electron/main.ts` 的核心结构：

```ts
import { app, BrowserWindow, Menu } from 'electron'

export async function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#f5f5f5',
    show: false,
    webPreferences: {
      preload: fileURLToPath(new URL('./preload.cjs', import.meta.url)),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  Menu.setApplicationMenu(null)

  const rendererUrl = process.env.IF_THEN_DESKTOP_RENDERER_URL
  if (rendererUrl) {
    await win.loadURL(rendererUrl)
  } else {
    await win.loadFile(backendPaths.rendererHtml)
  }

  win.show()
  return win
}
```

同时把文件里的 `createWindow` 从私有函数调整为可测试导出：

```ts
export async function createWindow() {
  // ...
}
```

- [ ] **Step 4: 运行目标测试确认转绿**

Run:

```powershell
cd D:\newProj\desktop
npm test -- windowChrome
```

Expected:
- PASS，确认无边框窗口与菜单栏移除已被锁定

- [ ] **Step 5: Commit**

```bash
git add desktop/electron/main.ts desktop/tests/windowChrome.test.ts
git commit -m "Make the desktop shell frameless and remove the default menu"
```

---

### Task 2: 补窗口控制 IPC 与 preload bridge

**Files:**
- Modify: `desktop/electron/ipc.ts`
- Modify: `desktop/electron/preload.cts`
- Modify: `desktop/tests/ipc.test.ts`
- Modify: `desktop/tests/desktopBridge.test.ts`
- Create: `desktop/src/types/desktop.ts`

- [ ] **Step 1: 先写失败测试，锁定窗口控制通道**

在 `desktop/tests/ipc.test.ts` 增加：

```ts
it('registers window control handlers', async () => {
  const focusedWindow = {
    minimize: vi.fn(),
    maximize: vi.fn(),
    unmaximize: vi.fn(),
    close: vi.fn(),
    isMaximized: vi.fn(() => false),
  }

  electron.BrowserWindow.getFocusedWindow.mockReturnValue(focusedWindow)

  registerDesktopIpc({ getState: () => ({ phase: 'ready' }) } as any)

  expect(handlers.get('desktop:window-minimize')).toBeTypeOf('function')
  expect(handlers.get('desktop:window-toggle-maximize')).toBeTypeOf('function')
  expect(handlers.get('desktop:window-close')).toBeTypeOf('function')
  expect(handlers.get('desktop:window-get-state')).toBeTypeOf('function')
})
```

在 `desktop/tests/desktopBridge.test.ts` 增加：

```ts
describe('desktop window bridge', () => {
  it('declares minimize, toggleMaximize, close, and getState capabilities', () => {
    type DesktopBridgeShape = typeof globalThis extends { desktop: infer T } ? T : never
    expectTypeOf<DesktopBridgeShape>().toMatchTypeOf<{
      window: {
        minimize: () => Promise<void>
        toggleMaximize: () => Promise<{ isMaximized: boolean }>
        close: () => Promise<void>
        getState: () => Promise<{ isMaximized: boolean }>
      }
    }>()
  })
})
```

- [ ] **Step 2: 运行目标测试确认失败**

Run:

```powershell
cd D:\newProj\desktop
npm test -- ipc desktopBridge
```

Expected:
- FAIL，因为当前还没有窗口 IPC / preload 暴露

- [ ] **Step 3: 在主进程注册窗口控制通道**

在 `desktop/electron/ipc.ts` 追加：

```ts
import { app, BrowserWindow, dialog, ipcMain } from 'electron'

function getFocusedWindowOrThrow() {
  const win = BrowserWindow.getFocusedWindow()
  if (!win) {
    throw new Error('No focused desktop window')
  }
  return win
}

ipcMain.handle('desktop:window-minimize', () => {
  getFocusedWindowOrThrow().minimize()
})

ipcMain.handle('desktop:window-toggle-maximize', () => {
  const win = getFocusedWindowOrThrow()
  if (win.isMaximized()) {
    win.unmaximize()
  } else {
    win.maximize()
  }
  return { isMaximized: win.isMaximized() }
})

ipcMain.handle('desktop:window-close', () => {
  getFocusedWindowOrThrow().close()
})

ipcMain.handle('desktop:window-get-state', () => {
  const win = getFocusedWindowOrThrow()
  return { isMaximized: win.isMaximized() }
})
```

- [ ] **Step 4: 在 preload 暴露窗口控制 API**

更新 `desktop/electron/preload.cts`：

```ts
contextBridge.exposeInMainWorld('desktop', {
  getServiceState: () => ipcRenderer.invoke('desktop:get-service-state'),
  pickImportFile: () => ipcRenderer.invoke('desktop:pick-import-file'),
  getAppInfo: () => ipcRenderer.invoke('desktop:get-app-info'),
  readImportFile: () => ipcRenderer.invoke('desktop:read-import-file'),
  window: {
    minimize: () => ipcRenderer.invoke('desktop:window-minimize'),
    toggleMaximize: () => ipcRenderer.invoke('desktop:window-toggle-maximize'),
    close: () => ipcRenderer.invoke('desktop:window-close'),
    getState: () => ipcRenderer.invoke('desktop:window-get-state'),
  },
})
```

新增 renderer 类型文件 `desktop/src/types/desktop.ts`：

```ts
export type DesktopWindowState = {
  isMaximized: boolean
}

export type DesktopBridge = {
  getServiceState: () => Promise<{ phase: string; detail?: string }>
  pickImportFile: () => Promise<{ canceled: boolean; filePaths: string[] }>
  getAppInfo: () => Promise<{ name: string; version: string }>
  readImportFile: () => Promise<{ fileName: string; content: string }>
  window: {
    minimize: () => Promise<void>
    toggleMaximize: () => Promise<DesktopWindowState>
    close: () => Promise<void>
    getState: () => Promise<DesktopWindowState>
  }
}
```

- [ ] **Step 5: 运行测试确认通过**

Run:

```powershell
cd D:\newProj\desktop
npm test -- ipc desktopBridge
npm run typecheck
```

Expected:
- PASS，renderer 与主进程之间的窗口控制桥接成立

- [ ] **Step 6: Commit**

```bash
git add desktop/electron/ipc.ts desktop/electron/preload.cts desktop/src/types/desktop.ts desktop/tests/ipc.test.ts desktop/tests/desktopBridge.test.ts
git commit -m "Expose desktop window controls through the Electron bridge"
```

---

### Task 3: 落地微信风格标题栏组件

**Files:**
- Create: `desktop/src/frontui/WindowTitleBar.tsx`
- Create: `desktop/src/lib/windowControls.ts`
- Modify: `desktop/tests/frontUiShell.test.tsx`

- [ ] **Step 1: 先写失败测试，锁定标题栏渲染与回调契约**

在 `desktop/tests/frontUiShell.test.tsx` 增加：

```tsx
import { WindowTitleBar } from '../src/frontui/WindowTitleBar'

it('renders a custom window title bar with minimize, maximize, and close affordances', () => {
  const html = renderToStaticMarkup(
    <WindowTitleBar
      appTitle="如果那时"
      isMaximized={false}
      onMinimize={() => undefined}
      onToggleMaximize={() => undefined}
      onClose={() => undefined}
    />,
  )

  expect(html).toContain('desktop-titlebar')
  expect(html).toContain('aria-label="最小化窗口"')
  expect(html).toContain('aria-label="最大化窗口"')
  expect(html).toContain('aria-label="关闭窗口"')
})
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiShell
```

Expected:
- FAIL，因为 `WindowTitleBar.tsx` 还不存在

- [ ] **Step 3: 添加标题栏组件与 renderer 侧 windowControls 封装**

新增 `desktop/src/lib/windowControls.ts`：

```ts
import type { DesktopBridge, DesktopWindowState } from '../types/desktop'

function getDesktopBridge(): DesktopBridge | undefined {
  return (globalThis as typeof globalThis & { desktop?: DesktopBridge }).desktop
}

export async function getDesktopWindowState(): Promise<DesktopWindowState> {
  const bridge = getDesktopBridge()
  return bridge?.window.getState ? bridge.window.getState() : { isMaximized: false }
}

export async function minimizeDesktopWindow(): Promise<void> {
  await getDesktopBridge()?.window.minimize?.()
}

export async function toggleDesktopWindowMaximize(): Promise<DesktopWindowState> {
  const bridge = getDesktopBridge()
  return bridge?.window.toggleMaximize ? bridge.window.toggleMaximize() : { isMaximized: false }
}

export async function closeDesktopWindow(): Promise<void> {
  await getDesktopBridge()?.window.close?.()
}
```

新增 `desktop/src/frontui/WindowTitleBar.tsx`：

```tsx
type WindowTitleBarProps = {
  appTitle: string
  isMaximized: boolean
  onMinimize: () => void
  onToggleMaximize: () => void
  onClose: () => void
}

export function WindowTitleBar({
  appTitle,
  isMaximized,
  onMinimize,
  onToggleMaximize,
  onClose,
}: WindowTitleBarProps) {
  return (
    <header className="desktop-titlebar">
      <div className="desktop-titlebar__drag-region">
        <span className="desktop-titlebar__title">{appTitle}</span>
      </div>
      <div className="desktop-titlebar__actions">
        <button type="button" aria-label="最小化窗口" onClick={onMinimize}>—</button>
        <button type="button" aria-label={isMaximized ? '还原窗口' : '最大化窗口'} onClick={onToggleMaximize}>
          {isMaximized ? '❐' : '□'}
        </button>
        <button type="button" aria-label="关闭窗口" onClick={onClose}>✕</button>
      </div>
    </header>
  )
}
```

- [ ] **Step 4: 运行测试确认标题栏基础通过**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiShell
```

Expected:
- PASS，标题栏结构已具备

- [ ] **Step 5: Commit**

```bash
git add desktop/src/frontui/WindowTitleBar.tsx desktop/src/lib/windowControls.ts desktop/tests/frontUiShell.test.tsx
git commit -m "Add a custom desktop title bar for the frameless shell"
```

---

### Task 4: 把 `FrontAppShell` 改成全窗口铺满布局

**Files:**
- Modify: `desktop/src/frontui/AppShell.tsx`
- Modify: `desktop/src/styles/frontui.css`
- Modify: `desktop/tests/frontUiShell.test.tsx`

- [ ] **Step 1: 先写失败测试，锁定全窗口布局替代居中卡片**

在 `desktop/tests/frontUiShell.test.tsx` 更新断言：

```tsx
expect(html).toContain('desktop-shell-root')
expect(html).toContain('desktop-shell-main')
expect(html).not.toContain('max-w-[1200px]')
expect(html).not.toContain('max-h-[800px]')
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiShell
```

Expected:
- FAIL，因为当前 `FrontAppShell` 仍是居中卡片

- [ ] **Step 3: 最小改造 `FrontAppShell` 为全窗口壳**

更新 `desktop/src/frontui/AppShell.tsx`：

```tsx
import type { ReactNode } from 'react'

type FrontAppShellProps = {
  titleBar: ReactNode
  sidebar: ReactNode
  list: ReactNode
  window: ReactNode
  aside?: ReactNode
}

export function FrontAppShell({ titleBar, sidebar, list, window, aside }: FrontAppShellProps) {
  return (
    <div className="desktop-shell-root">
      {titleBar}
      <div className="desktop-shell-main">
        {sidebar}
        {list}
        {window}
        {aside}
      </div>
    </div>
  )
}
```

在 `desktop/src/styles/frontui.css` 增加：

```css
.desktop-shell-root {
  width: 100vw;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  background: #f5f5f5;
}

.desktop-shell-main {
  flex: 1;
  min-height: 0;
  display: flex;
  overflow: hidden;
}

.desktop-titlebar {
  height: 40px;
  display: flex;
  align-items: stretch;
  justify-content: space-between;
  background: #ededed;
}

.desktop-titlebar__drag-region {
  flex: 1;
  display: flex;
  align-items: center;
  padding: 0 12px;
  -webkit-app-region: drag;
}

.desktop-titlebar__actions {
  display: flex;
  -webkit-app-region: no-drag;
}
```

- [ ] **Step 4: 运行测试确认全窗口布局通过**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiShell
npm run build
```

Expected:
- PASS，主壳不再是居中卡片
- build 通过，样式链路正常

- [ ] **Step 5: Commit**

```bash
git add desktop/src/frontui/AppShell.tsx desktop/src/styles/frontui.css desktop/tests/frontUiShell.test.tsx
git commit -m "Stretch the frontUI shell across the full desktop window"
```

---

### Task 5: 在 `App.tsx` 接入标题栏和窗口状态

**Files:**
- Modify: `desktop/src/App.tsx`
- Modify: `desktop/tests/visualShell.test.tsx`

- [ ] **Step 1: 先写失败集成测试，锁定 App 级标题栏行为**

在 `desktop/tests/visualShell.test.tsx` 增加：

```tsx
it('renders the custom title bar in the ready desktop shell', async () => {
  // 与现有 ready 态 mock 同样的数据水位
  // root.render(<App />)
  // flushAsyncWork()
  expect(container.querySelector('.desktop-titlebar')).not.toBeNull()
  expect(container.querySelector('button[aria-label="最小化窗口"]')).not.toBeNull()
  expect(container.querySelector('button[aria-label="关闭窗口"]')).not.toBeNull()
})
```

- [ ] **Step 2: 运行测试确认失败**

Run:

```powershell
cd D:\newProj\desktop
npm test -- visualShell
```

Expected:
- FAIL，因为 `App.tsx` 还没把标题栏接到 `FrontAppShell`

- [ ] **Step 3: 在 `App.tsx` 接入标题栏与窗口状态**

在 `desktop/src/App.tsx` 中新增：

```tsx
import { WindowTitleBar } from './frontui/WindowTitleBar'
import {
  closeDesktopWindow,
  getDesktopWindowState,
  minimizeDesktopWindow,
  toggleDesktopWindowMaximize,
} from './lib/windowControls'
```

新增状态与初始化：

```tsx
const [isDesktopWindowMaximized, setIsDesktopWindowMaximized] = useState(false)

useEffect(() => {
  if (state.phase !== 'ready') {
    return
  }

  void getDesktopWindowState().then((next) => {
    setIsDesktopWindowMaximized(next.isMaximized)
  })
}, [state.phase])
```

把标题栏接入 `FrontAppShell`：

```tsx
<FrontAppShell
  titleBar={
    <WindowTitleBar
      appTitle="如果那时"
      isMaximized={isDesktopWindowMaximized}
      onMinimize={() => {
        void minimizeDesktopWindow()
      }}
      onToggleMaximize={() => {
        void toggleDesktopWindowMaximize().then((next) => setIsDesktopWindowMaximized(next.isMaximized))
      }}
      onClose={() => {
        void closeDesktopWindow()
      }}
    />
  }
  sidebar={...}
  list={...}
  window={...}
  aside={...}
/>
```

- [ ] **Step 4: 运行集成测试与类型检查**

Run:

```powershell
cd D:\newProj\desktop
npm test -- visualShell
npm run typecheck
```

Expected:
- PASS，App 已接入标题栏与窗口状态

- [ ] **Step 5: Commit**

```bash
git add desktop/src/App.tsx desktop/tests/visualShell.test.tsx
git commit -m "Wire the custom title bar into the desktop app shell"
```

---

### Task 6: 做桌面窗口化的最终验证与文档同步

**Files:**
- Modify: `README.md`
- Modify: `docs/project-status.md`

- [ ] **Step 1: 更新文档，明确当前已进入无边框窗口阶段**

在 `README.md` 的桌面部分补充：

```md
- 当前桌面端已使用自定义标题栏与全窗口 frontUI 主壳
- 开发态若看到系统菜单栏或默认标题栏，视为回归
```

在 `docs/project-status.md` 增加：

```md
| 微信式窗口壳 | Electron frameless window + custom title bar | Real | 已完成菜单栏移除、无边框窗口、自定义标题栏 |
```

- [ ] **Step 2: 跑最终验证**

Run:

```powershell
cd D:\newProj\desktop
npm test
npm run typecheck
npm run build
```

Expected:
- 全部 PASS

- [ ] **Step 3: 手工 GUI 验证**

Run:

```powershell
cd D:\newProj\desktop
npm run dev
```

另一个终端：

```powershell
cd D:\newProj\desktop
npm run build:electron
$env:IF_THEN_DESKTOP_RENDERER_URL = "http://localhost:5173"
npx electron .
```

手工检查：
- 没有默认 `File / Edit` 菜单栏
- 没有原生标题栏
- 标题栏可拖动
- 最小化 / 最大化 / 关闭可用
- 主聊天界面全窗口铺满
- 当前 frontUI 三栏与分析/改写/分支路径仍可使用

- [ ] **Step 4: Commit**

```bash
git add README.md docs/project-status.md
git commit -m "Document the frameless wechat-style desktop shell"
```

---

## Self-Review

### Spec coverage
- 菜单栏移除：Task 1
- 无边框窗口：Task 1
- 窗口控制 IPC：Task 2
- 自定义标题栏：Task 3
- 全窗口铺满：Task 4
- App 接线：Task 5
- 最终验证：Task 6

无明显漏项。

### Placeholder scan
- 未使用 `TODO / TBD / similar to above`
- 每个任务都给了文件、测试、命令、最小代码方向

### Type consistency
- IPC 通道命名统一为 `desktop:window-*`
- preload / renderer 统一使用 `desktop.window.*`
- 标题栏状态统一为 `isMaximized`

---

Plan complete and saved to `docs/superpowers/plans/2026-04-08-wechat-desktop-window.md`. Two execution options:

**1. Subagent-Driven (recommended)** - 我按任务逐个派发子代理执行、每步回看，迭代更稳  
**2. Inline Execution** - 我直接在当前会话里按计划连续实现

**你选哪种？**
