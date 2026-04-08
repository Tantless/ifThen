# Desktop Frontend Product Shell Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把当前 Electron renderer 从 boot placeholder 升级为真实桌面产品壳，跑通“配置模型 → 导入聊天记录 → 查看分析状态 → 浏览历史聊天 → 改写并推演 → 查看分析信息”的主链路。

**Architecture:** 继续沿用现有 `desktop/` React + TypeScript 工作区，在 renderer 内按 `bridge / services / adapters / shell components` 分层。桌面专属能力通过 preload bridge 暴露，业务数据继续走本地 Python HTTP API，组件只消费 service/adapters 暴露的视图模型，不直接耦合原始后端响应。

**Tech Stack:** Electron, React, TypeScript, Vite, Vitest, Python FastAPI backend

---

## 执行状态（2026-04-08 同步）

- 状态：**已完成并已并入 `main`**
- 结果：桌面端主链路已跑通，覆盖欢迎引导、模型配置、导入聊天、会话列表、历史消息浏览、改写推演、分支视图与分析侧栏。
- 当前验证参考：`cd desktop && npm test` 为 `9 files / 46 tests passed`，`npm run typecheck` / `npm run build` 通过。
- 说明：下方 `- [ ]` 复选框保留为原始执行脚本，不再表示当前待办；当前总体进度以 `docs/2026-04-08-milestone-progress-summary.md` 为准。

## File Map

### Existing files to modify
- `desktop/electron/preload.ts`
- `desktop/electron/ipc.ts`
- `desktop/src/App.tsx`
- `desktop/src/lib/desktop.ts`
- `desktop/src/types/desktop.d.ts`
- `desktop/src/styles.css`

### New files to create
- `desktop/src/types/api.ts`
- `desktop/src/lib/apiClient.ts`
- `desktop/src/lib/bootstrap.ts`
- `desktop/src/lib/adapters.ts`
- `desktop/src/lib/chatState.ts`
- `desktop/src/lib/services/settingsService.ts`
- `desktop/src/lib/services/conversationService.ts`
- `desktop/src/lib/services/jobService.ts`
- `desktop/src/lib/services/simulationService.ts`
- `desktop/src/components/AppShell.tsx`
- `desktop/src/components/SidebarNav.tsx`
- `desktop/src/components/ConversationListPane.tsx`
- `desktop/src/components/ConversationListItem.tsx`
- `desktop/src/components/ChatPane.tsx`
- `desktop/src/components/ChatHeader.tsx`
- `desktop/src/components/MessageTimeline.tsx`
- `desktop/src/components/MessageBubble.tsx`
- `desktop/src/components/ConversationEmptyState.tsx`
- `desktop/src/components/WelcomeModal.tsx`
- `desktop/src/components/SettingsDrawer.tsx`
- `desktop/src/components/ImportDialog.tsx`
- `desktop/src/components/AnalysisStatusBadge.tsx`
- `desktop/src/components/RewritePanel.tsx`
- `desktop/src/components/BranchView.tsx`
- `desktop/src/components/AnalysisInspector.tsx`
- `desktop/tests/desktopBridge.test.ts`
- `desktop/tests/apiClient.test.ts`
- `desktop/tests/adapters.test.ts`
- `desktop/tests/chatState.test.ts`

---

### Task 1: Expand the Desktop Bridge and API Service Foundation

**Files:**
- Modify: `desktop/electron/preload.ts`
- Modify: `desktop/electron/ipc.ts`
- Modify: `desktop/src/lib/desktop.ts`
- Modify: `desktop/src/types/desktop.d.ts`
- Create: `desktop/src/types/api.ts`
- Create: `desktop/src/lib/apiClient.ts`
- Create: `desktop/src/lib/services/settingsService.ts`
- Create: `desktop/src/lib/services/conversationService.ts`
- Create: `desktop/src/lib/services/jobService.ts`
- Create: `desktop/src/lib/services/simulationService.ts`
- Test: `desktop/tests/desktopBridge.test.ts`
- Test: `desktop/tests/apiClient.test.ts`

- [ ] **Step 1: Write the failing tests**

```ts
// desktop/tests/desktopBridge.test.ts
import { describe, expect, it } from 'vitest'
import { normalizeDesktopFileSelection, shouldUseDesktopBridge } from '../src/lib/desktop'

describe('normalizeDesktopFileSelection', () => {
  it('turns a canceled selection into null', () => {
    expect(normalizeDesktopFileSelection({ canceled: true, filePaths: [] })).toBeNull()
  })
})

describe('shouldUseDesktopBridge', () => {
  it('requires the bridge for file picking only', () => {
    expect(shouldUseDesktopBridge('pick-import-file')).toBe(true)
    expect(shouldUseDesktopBridge('read-conversations')).toBe(false)
  })
})
```

```ts
// desktop/tests/apiClient.test.ts
import { describe, expect, it, vi } from 'vitest'
import { createApiClient } from '../src/lib/apiClient'

describe('createApiClient', () => {
  it('prefixes paths with the local api origin', async () => {
    const fetchMock = vi.fn(async () => ({ ok: true, status: 200, json: async () => [] }))
    await createApiClient(fetchMock as typeof fetch).get('/conversations')
    expect(fetchMock).toHaveBeenCalledWith(
      'http://127.0.0.1:8000/conversations',
      expect.objectContaining({ method: 'GET' }),
    )
  })
})
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `cd D:\newProj\desktop && npm test -- --run desktop/tests/desktopBridge.test.ts desktop/tests/apiClient.test.ts`  
Expected: missing exports / missing files.

- [ ] **Step 3: Implement the minimum bridge and client**

```ts
// desktop/electron/preload.ts
contextBridge.exposeInMainWorld('desktop', {
  getServiceState: () => ipcRenderer.invoke('desktop:get-service-state'),
  pickImportFile: () => ipcRenderer.invoke('desktop:pick-import-file'),
  getAppInfo: () => ipcRenderer.invoke('desktop:get-app-info'),
})
```

```ts
// desktop/src/lib/apiClient.ts
const DEFAULT_API_ORIGIN = 'http://127.0.0.1:8000'
export function createApiClient(fetchImpl: typeof fetch = fetch) {
  async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const response = await fetchImpl(`${DEFAULT_API_ORIGIN}${path}`, init)
    if (!response.ok) throw new Error(`API request failed: ${response.status}`)
    if (response.status === 204) return undefined as T
    return (await response.json()) as T
  }
  return {
    get: <T>(path: string) => request<T>(path, { method: 'GET' }),
    put: <T>(path: string, body: unknown) =>
      request<T>(path, { method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }),
    post: <T>(path: string, body: BodyInit | null, headers?: HeadersInit) =>
      request<T>(path, { method: 'POST', body, headers }),
    delete: (path: string) => request<void>(path, { method: 'DELETE' }),
  }
}
```

- [ ] **Step 4: Implement the IPC handlers and service wrappers**

Code to add:
- `desktop/electron/ipc.ts`: `dialog.showOpenDialog({ properties: ['openFile'], filters: [{ name: 'QQ chat export', extensions: ['txt'] }] })`
- `desktop/electron/ipc.ts`: `app.getName()` / `app.getVersion()` handler
- `desktop/src/lib/desktop.ts`: `normalizeDesktopFileSelection()` and `openImportFileDialog()`
- `desktop/src/types/api.ts`: `ConversationRead`, `JobRead`, `MessageRead`, `TopicRead`, `PersonaProfileRead`, `SnapshotRead`, `SettingRead`, `SettingWrite`, `ImportResponse`, `SimulationCreate`, `SimulationRead`
- `desktop/src/lib/services/*.ts`: wrap `/settings`, `/conversations`, `/jobs`, `/simulations`

- [ ] **Step 5: Run focused verification**

Run:
- `cd D:\newProj\desktop && npm test -- --run desktop/tests/desktopBridge.test.ts desktop/tests/apiClient.test.ts`
- `cd D:\newProj\desktop && npm run typecheck`

Expected: both pass.

- [ ] **Step 6: Commit**

```powershell
git add desktop/electron/preload.ts desktop/electron/ipc.ts desktop/src/lib/desktop.ts desktop/src/types/desktop.d.ts desktop/src/types/api.ts desktop/src/lib/apiClient.ts desktop/src/lib/services/settingsService.ts desktop/src/lib/services/conversationService.ts desktop/src/lib/services/jobService.ts desktop/src/lib/services/simulationService.ts desktop/tests/desktopBridge.test.ts desktop/tests/apiClient.test.ts
git commit -m "Create the desktop renderer service and bridge foundation"
```

---

### Task 2: Replace the Placeholder with a Real App Shell

**Files:**
- Modify: `desktop/src/App.tsx`
- Modify: `desktop/src/styles.css`
- Create: `desktop/src/lib/bootstrap.ts`
- Create: `desktop/src/components/AppShell.tsx`
- Create: `desktop/src/components/SidebarNav.tsx`
- Create: `desktop/src/components/ConversationEmptyState.tsx`
- Test: `desktop/tests/desktopBridge.test.ts`

- [ ] **Step 1: Write the failing bootstrap test**

```ts
// desktop/tests/desktopBridge.test.ts
import { describe, expect, it } from 'vitest'
import { decideAppShellState } from '../src/lib/bootstrap'

describe('decideAppShellState', () => {
  it('opens welcome flow when settings or conversations are missing', () => {
    expect(decideAppShellState({ bootPhase: 'ready', settings: [], conversations: [] })).toMatchObject({
      ready: true,
      showWelcome: true,
    })
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\newProj\desktop && npm test -- --run desktop/tests/desktopBridge.test.ts`  
Expected: missing bootstrap helper.

- [ ] **Step 3: Implement bootstrap helper and shell skeleton**

Code to add:
- `desktop/src/lib/bootstrap.ts`: `hasModelSettings()` + `decideAppShellState()`
- `desktop/src/components/AppShell.tsx`: 3-column grid shell
- `desktop/src/components/SidebarNav.tsx`: left dark nav with “会话 / 分析 / 设置”
- `desktop/src/components/ConversationEmptyState.tsx`: no conversation selected placeholder
- `desktop/src/App.tsx`: boot ready 后并行拉 `/settings` 与 `/conversations`，不再渲染 `DesktopShellPlaceholder`

Minimal code target:

```tsx
if (!appShellState.ready) {
  return <BootScreen label={getBootLabel(bootState)} detail={bootState.detail} />
}

return (
  <AppShell
    sidebar={<SidebarNav />}
    listPane={<div>会话列表加载中…</div>}
    chatPane={<ConversationEmptyState />}
  />
)
```

- [ ] **Step 4: Add shell base styles**

Add to `desktop/src/styles.css`:

```css
.desktop-shell { display: grid; grid-template-columns: 64px 320px 1fr; min-height: 100vh; }
.desktop-shell__list { border-right: 1px solid #d6d6d6; background: #ecebeb; }
.desktop-shell__chat { min-width: 0; background: #f7f7f7; }
```

- [ ] **Step 5: Run focused verification**

Run:
- `cd D:\newProj\desktop && npm test -- --run desktop/tests/desktopBridge.test.ts`
- `cd D:\newProj\desktop && npm run typecheck`

- [ ] **Step 6: Commit**

```powershell
git add desktop/src/App.tsx desktop/src/styles.css desktop/src/lib/bootstrap.ts desktop/src/components/AppShell.tsx desktop/src/components/SidebarNav.tsx desktop/src/components/ConversationEmptyState.tsx desktop/tests/desktopBridge.test.ts
git commit -m "Replace the desktop placeholder with a real app shell"
```

---

### Task 3: Implement Welcome Flow, Settings Drawer, Import Dialog, and Job Polling

**Files:**
- Modify: `desktop/src/App.tsx`
- Create: `desktop/src/components/WelcomeModal.tsx`
- Create: `desktop/src/components/SettingsDrawer.tsx`
- Create: `desktop/src/components/ImportDialog.tsx`
- Create: `desktop/src/components/AnalysisStatusBadge.tsx`
- Create: `desktop/src/lib/adapters.ts`
- Test: `desktop/tests/adapters.test.ts`

- [ ] **Step 1: Write the failing adapter tests**

```ts
// desktop/tests/adapters.test.ts
import { describe, expect, it } from 'vitest'
import { buildSettingsFormState, buildConversationListItem } from '../src/lib/adapters'

describe('buildSettingsFormState', () => {
  it('maps flat llm settings into one form state', () => {
    expect(buildSettingsFormState([
      { setting_key: 'llm.base_url', setting_value: 'https://api.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'sk-test', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4-mini', is_secret: false },
    ])).toMatchObject({ baseUrl: 'https://api.test/v1', apiKey: 'sk-test', chatModel: 'gpt-5.4-mini' })
  })

  it('shows running jobs as analysing', () => {
    expect(buildConversationListItem({
      conversation: { id: 1, title: 'Alice', other_display_name: 'Alice', status: 'queued' },
      latestJob: { status: 'running', progress_percent: 42, current_stage: 'topics' },
    })).toMatchObject({ statusLabel: '分析中 42%' })
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\newProj\desktop && npm test -- --run desktop/tests/adapters.test.ts`

- [ ] **Step 3: Implement adapters and modal components**

Code to add:
- `desktop/src/lib/adapters.ts`: `buildSettingsFormState()` + `buildConversationListItem()`
- `desktop/src/components/WelcomeModal.tsx`: configure/import/close actions
- `desktop/src/components/SettingsDrawer.tsx`: `baseUrl/apiKey/chatModel` 表单
- `desktop/src/components/ImportDialog.tsx`: 调 bridge 选文件 + `self_display_name`
- `desktop/src/components/AnalysisStatusBadge.tsx`: `queued/running/completed/failed` 标签

- [ ] **Step 4: Wire import and job polling**

`desktop/src/App.tsx` 需要：
- 控制 `showWelcome / showSettings / showImportDialog`
- 导入成功后立即插入新会话、选中新会话
- 若返回 `job.id`，轮询 `/jobs/{id}` 直到 `completed | failed`

Minimal job polling shape:

```ts
async function pollJob(jobId: number) {
  const next = await readJob(jobId)
  if (next.status === 'queued' || next.status === 'running') {
    window.setTimeout(() => void pollJob(jobId), 1000)
    return
  }
  await refreshConversations()
}
```

- [ ] **Step 5: Run focused verification**

Run:
- `cd D:\newProj\desktop && npm test -- --run desktop/tests/adapters.test.ts`
- `cd D:\newProj\desktop && npm run typecheck`

- [ ] **Step 6: Commit**

```powershell
git add desktop/src/App.tsx desktop/src/components/WelcomeModal.tsx desktop/src/components/SettingsDrawer.tsx desktop/src/components/ImportDialog.tsx desktop/src/components/AnalysisStatusBadge.tsx desktop/src/lib/adapters.ts desktop/tests/adapters.test.ts
git commit -m "Add the desktop welcome, settings, and import flows"
```

---

### Task 4: Implement Conversation List and History Chat Browsing

**Files:**
- Modify: `desktop/src/App.tsx`
- Modify: `desktop/src/styles.css`
- Create: `desktop/src/components/ConversationListPane.tsx`
- Create: `desktop/src/components/ConversationListItem.tsx`
- Create: `desktop/src/components/ChatPane.tsx`
- Create: `desktop/src/components/ChatHeader.tsx`
- Create: `desktop/src/components/MessageTimeline.tsx`
- Create: `desktop/src/components/MessageBubble.tsx`
- Modify: `desktop/src/lib/adapters.ts`
- Test: `desktop/tests/adapters.test.ts`

- [ ] **Step 1: Write the failing message adapter test**

```ts
// desktop/tests/adapters.test.ts
import { describe, expect, it } from 'vitest'
import { buildMessageBubbleModel } from '../src/lib/adapters'

describe('buildMessageBubbleModel', () => {
  it('marks self text messages as rewrite candidates', () => {
    expect(buildMessageBubbleModel({
      id: 12,
      sequence_no: 5,
      speaker_role: 'self',
      speaker_name: 'Me',
      timestamp: '2026-04-07T10:00:00',
      content_text: '那我们先这样吧',
      message_type: 'text',
    })).toMatchObject({ align: 'right', canRewrite: true })
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\newProj\desktop && npm test -- --run desktop/tests/adapters.test.ts`

- [ ] **Step 3: Implement conversation and message view models**

Add to `desktop/src/lib/adapters.ts`:

```ts
export function buildMessageBubbleModel(message: MessageRead) {
  const isSelf = message.speaker_role === 'self'
  return {
    id: message.id,
    align: isSelf ? 'right' : 'left',
    speakerName: message.speaker_name,
    text: message.content_text,
    timestamp: message.timestamp,
    canRewrite: isSelf && message.message_type === 'text',
  }
}
```

- [ ] **Step 4: Implement list pane and history chat components**

Code to add:
- `ConversationListPane.tsx`: search + import button + list
- `ConversationListItem.tsx`: active state + status label
- `ChatHeader.tsx`: 当前联系人 + 分析状态 + inspector 入口
- `MessageTimeline.tsx`: map bubble models
- `MessageBubble.tsx`: left/right bubble + hover rewrite action
- `ChatPane.tsx`: empty / loading / history states

`desktop/src/App.tsx` 需要：
- `selectedConversationId`
- `conversationSearch`
- `messages`
- 选中会话后 `listMessages(conversationId)`

- [ ] **Step 5: Run focused verification**

Run:
- `cd D:\newProj\desktop && npm test -- --run desktop/tests/adapters.test.ts`
- `cd D:\newProj\desktop && npm run typecheck`

- [ ] **Step 6: Commit**

```powershell
git add desktop/src/App.tsx desktop/src/styles.css desktop/src/components/ConversationListPane.tsx desktop/src/components/ConversationListItem.tsx desktop/src/components/ChatPane.tsx desktop/src/components/ChatHeader.tsx desktop/src/components/MessageTimeline.tsx desktop/src/components/MessageBubble.tsx desktop/src/lib/adapters.ts desktop/tests/adapters.test.ts
git commit -m "Add conversation browsing to the desktop shell"
```

---

### Task 5: Implement Rewrite Simulation, Branch View, and Analysis Inspector

**Files:**
- Modify: `desktop/src/App.tsx`
- Create: `desktop/src/lib/chatState.ts`
- Create: `desktop/src/components/RewritePanel.tsx`
- Create: `desktop/src/components/BranchView.tsx`
- Create: `desktop/src/components/AnalysisInspector.tsx`
- Test: `desktop/tests/chatState.test.ts`

- [ ] **Step 1: Write the failing branch-state tests**

```ts
// desktop/tests/chatState.test.ts
import { describe, expect, it } from 'vitest'
import { enterBranchView, exitBranchView } from '../src/lib/chatState'

describe('chatState', () => {
  it('switches from history to branch', () => {
    expect(
      enterBranchView({ mode: 'history' }, { targetMessageId: 12, replacementContent: '换个说法' }),
    ).toMatchObject({ mode: 'branch', targetMessageId: 12 })
  })

  it('returns from branch to history', () => {
    expect(exitBranchView({ mode: 'branch', targetMessageId: 12, replacementContent: '换个说法' })).toMatchObject({
      mode: 'history',
    })
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\newProj\desktop && npm test -- --run desktop/tests/chatState.test.ts`

- [ ] **Step 3: Implement chat mode state and rewrite panel**

Add:
- `desktop/src/lib/chatState.ts`: `enterBranchView()` / `exitBranchView()`
- `desktop/src/components/RewritePanel.tsx`: 原消息、替换文本、模式选择、提交按钮
- `desktop/src/lib/services/simulationService.ts`: `createSimulation(payload)`

- [ ] **Step 4: Implement branch view and analysis inspector**

Add:
- `desktop/src/components/BranchView.tsx`: 返回历史、改写内容、首轮回复、短链 turns
- `desktop/src/components/AnalysisInspector.tsx`: topics / persona / snapshot
- `desktop/src/App.tsx`: history / branch 模式切换，右上角 inspector 开关，加载 `topics/profile/snapshot`

- [ ] **Step 5: Run full desktop verification**

Run:
- `cd D:\newProj\desktop && npm test`
- `cd D:\newProj\desktop && npm run typecheck`
- `cd D:\newProj\desktop && npm run build`

Expected: all green.

- [ ] **Step 6: Commit**

```powershell
git add desktop/src/App.tsx desktop/src/lib/chatState.ts desktop/src/components/RewritePanel.tsx desktop/src/components/BranchView.tsx desktop/src/components/AnalysisInspector.tsx desktop/src/lib/services/simulationService.ts desktop/tests/chatState.test.ts
git commit -m "Add branch simulation and analysis inspector to the desktop shell"
```

---

## Self-Review Checklist

- Spec coverage:
  - app shell / 三栏布局：Task 2
  - 首启欢迎引导 / 设置 / 导入：Task 3
  - 会话列表 / 历史聊天浏览：Task 4
  - 改写推演 / branch view / inspector：Task 5
  - bridge / services / adapters 基础层：Task 1
- Placeholder scan:
  - 无 `TODO` / `TBD` / “类似前面任务” 占位
- Type consistency:
  - `ConversationRead` / `JobRead` / `SimulationRead` 等名称与后端 `schemas.py` 对齐
  - `history` / `branch` 模式命名在全计划保持一致
