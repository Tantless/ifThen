# frontUI Visual Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the current desktop chat shell with the `D:\frontUI\src` visual structure while preserving existing desktop business flows and documenting which areas remain mock-backed during the transition.

**Architecture:** Keep the existing `desktop/src/App.tsx` state machine, service calls, Electron bridge usage, and modal flows as the orchestration layer. Introduce a frontUI-flavored presentation layer (`Sidebar`, `ChatList`, `ChatWindow`) plus a dedicated adapter module that maps real backend payloads into the UI view models expected by those components. Allow temporary mock-only affordances inside the new shell, but track every such gap in a migration status document instead of showing labels in the UI.

**Tech Stack:** React 19, TypeScript, Vite, Electron renderer, Vitest, server-side React markup tests, Tailwind CSS v4, lucide-react, date-fns

---

## File Structure Map

### Modify
- `desktop/package.json` — add the minimum frontUI runtime/style dependencies and scripts that still work with the existing Electron flow.
- `desktop/vite.config.ts` — wire up Tailwind v4 through Vite if needed by the imported frontUI styles.
- `desktop/src/main.tsx` — swap the global stylesheet entry from the current handcrafted shell CSS to the frontUI style bundle.
- `desktop/src/App.tsx` — keep the current boot/data orchestration, but render the new frontUI shell container instead of the old desktop shell composition.
- `desktop/src/lib/adapters.ts` — either trim or supersede the existing adapter layer so frontUI view models become the canonical presentation model.
- `desktop/tests/visualShell.test.tsx` — replace old shell-specific assertions with frontUI shell structure checks.

### Create
- `desktop/src/frontui/AppShell.tsx` — top-level frontUI three-column layout container for the desktop renderer.
- `desktop/src/frontui/Sidebar.tsx` — left navigation rail adapted from `D:\frontUI\src\app\components\Sidebar.tsx`.
- `desktop/src/frontui/ChatList.tsx` — center list pane adapted from `D:\frontUI\src\app\components\ChatList.tsx`.
- `desktop/src/frontui/ChatWindow.tsx` — right message pane adapted from `D:\frontUI\src\app\components\ChatWindow.tsx`.
- `desktop/src/frontui/types.ts` — UI-facing types for chat list items, message items, and shell tabs.
- `desktop/src/frontui/mockState.ts` — explicit temporary mock data for frontUI-only controls that do not yet map to real backend capability.
- `desktop/src/lib/frontUiAdapters.ts` — transforms from `ConversationRead`, `MessageRead`, `JobRead`, and app state into frontUI view models.
- `desktop/tests/frontUiAdapters.test.ts` — adapter-level regression tests.
- `desktop/tests/frontUiShell.test.tsx` — renderer shell markup and mock/real integration tests.
- `docs/project-status.md` — canonical current-state doc, including the frontUI real/mock/pending summary.

### Delete / Retire After Cutover
- `desktop/src/components/AppShell.tsx`
- `desktop/src/components/SidebarNav.tsx`
- `desktop/src/components/ConversationListPane.tsx`
- `desktop/src/components/ChatPane.tsx`
- old shell-only CSS blocks inside `desktop/src/styles.css`

Only delete retired files after the new shell is wired and tests have been updated to the new structure.

---

### Task 1: Establish frontUI dependency and stylesheet pipeline

**Files:**
- Modify: `desktop/package.json`
- Modify: `desktop/vite.config.ts`
- Modify: `desktop/src/main.tsx`
- Create: `desktop/src/styles/frontui.css`
- Test: `desktop/tests/frontUiShell.test.tsx`

- [ ] **Step 1: Write the failing shell-style entry test**

```tsx
import { readFileSync } from 'node:fs'
import { describe, expect, it } from 'vitest'

describe('frontUI style entry', () => {
  it('loads the frontUI stylesheet bundle from main.tsx', () => {
    const main = readFileSync(new URL('../src/main.tsx', import.meta.url), 'utf8')
    const styles = readFileSync(new URL('../src/styles/frontui.css', import.meta.url), 'utf8')

    expect(main).toContain("./styles/frontui.css")
    expect(styles).toContain("@import './frontui/fonts.css'")
    expect(styles).toContain("@import './frontui/tailwind.css'")
    expect(styles).toContain("@import './frontui/theme.css'")
  })
})
```

- [ ] **Step 2: Run the test to confirm it fails before the pipeline exists**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiShell
```

Expected: FAIL because `src/styles/frontui.css` does not exist and `main.tsx` still imports `./styles.css`.

- [ ] **Step 3: Add the minimal style/dependency pipeline**

Update `desktop/package.json` dependencies to include only the frontUI shell requirements:

```json
{
  "dependencies": {
    "date-fns": "^4.1.0",
    "lucide-react": "^0.511.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "devDependencies": {
    "@tailwindcss/vite": "^4.1.4",
    "tailwindcss": "^4.1.4",
    "tw-animate-css": "^1.3.0"
  }
}
```

Create `desktop/src/styles/frontui.css`:

```css
@import './frontui/fonts.css';
@import './frontui/tailwind.css';
@import './frontui/theme.css';

html,
body,
#root {
  width: 100%;
  min-height: 100%;
}

body {
  margin: 0;
  font-family: "Segoe UI", system-ui, sans-serif;
}
```

Update `desktop/src/main.tsx`:

```tsx
import ReactDOM from 'react-dom/client'
import App from './App'
import './styles/frontui.css'

ReactDOM.createRoot(document.getElementById('root')!).render(<App />)
```

Update `desktop/vite.config.ts`:

```ts
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
})
```

- [ ] **Step 4: Run targeted test and typecheck**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiShell
npm run typecheck
```

Expected: the new stylesheet test passes; typecheck remains green after adding the new import path.

- [ ] **Step 5: Commit**

```bash
git add desktop/package.json desktop/vite.config.ts desktop/src/main.tsx desktop/src/styles/frontui.css desktop/tests/frontUiShell.test.tsx package-lock.json
git commit -m "Adopt frontUI stylesheet pipeline for the desktop renderer"
```

### Task 2: Introduce frontUI view models and adapter coverage

**Files:**
- Create: `desktop/src/frontui/types.ts`
- Create: `desktop/src/lib/frontUiAdapters.ts`
- Create: `desktop/src/frontui/mockState.ts`
- Test: `desktop/tests/frontUiAdapters.test.ts`

- [ ] **Step 1: Write failing adapter tests for real-data mapping and mock fallback**

```ts
import { describe, expect, it } from 'vitest'

import { buildFrontChatItem, buildFrontChatWindowState } from '../src/lib/frontUiAdapters'

describe('buildFrontChatItem', () => {
  it('maps real conversations into frontUI list rows', () => {
    expect(
      buildFrontChatItem({
        conversation: {
          id: 7,
          title: '和小李的聊天',
          chat_type: 'private',
          self_display_name: '我',
          other_display_name: '小李',
          source_format: 'qq_export_v5',
          status: 'imported',
        },
        latestJob: null,
        isActive: true,
      }),
    ).toMatchObject({
      id: 'conversation-7',
      displayName: '和小李的聊天',
      previewText: expect.any(String),
      active: true,
    })
  })
})

describe('buildFrontChatWindowState', () => {
  it('falls back to the frontUI placeholder state when no conversation is selected', () => {
    expect(buildFrontChatWindowState({ selectedConversation: null, messages: [] }).mode).toBe('placeholder')
  })
})
```

- [ ] **Step 2: Run the test to verify the adapter surface is absent**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiAdapters
```

Expected: FAIL because `frontUiAdapters.ts` and `frontui/types.ts` do not exist yet.

- [ ] **Step 3: Add the new view-model and adapter layer**

Create `desktop/src/frontui/types.ts`:

```ts
export type FrontSidebarTab = 'chat' | 'contacts' | 'files'

export type FrontChatListItem = {
  id: string
  conversationId: number | null
  displayName: string
  avatarUrl: string
  previewText: string
  timestampLabel: string
  unreadCount: number
  active: boolean
  source: 'real' | 'mock'
}

export type FrontChatMessage = {
  id: string
  align: 'left' | 'right'
  speakerName: string
  avatarUrl: string
  text: string
  timestampLabel: string
  canRewrite: boolean
  source: 'real' | 'mock'
}

export type FrontChatWindowState =
  | { mode: 'placeholder' }
  | { mode: 'conversation'; title: string; messages: FrontChatMessage[] }
```

Create `desktop/src/frontui/mockState.ts`:

```ts
import type { FrontChatListItem, FrontChatMessage } from './types'

export const FRONTUI_PLACEHOLDER_AVATAR = 'https://images.unsplash.com/photo-1617978440019-a4855b590db2?...'

export const MOCK_CONTACTS_TAB_ITEMS: FrontChatListItem[] = [
  {
    id: 'mock-contact-1',
    conversationId: null,
    displayName: '通讯录功能开发中',
    avatarUrl: FRONTUI_PLACEHOLDER_AVATAR,
    previewText: '此入口保留 frontUI 视觉位',
    timestampLabel: '',
    unreadCount: 0,
    active: false,
    source: 'mock',
  },
]
```

Create `desktop/src/lib/frontUiAdapters.ts` with pure mapping helpers that derive `displayName`, `previewText`, timestamp labels, self/other avatars, and placeholder state without importing React.

- [ ] **Step 4: Run adapter tests and full desktop tests**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiAdapters
npm test
```

Expected: the adapter tests pass and existing non-shell tests still pass.

- [ ] **Step 5: Commit**

```bash
git add desktop/src/frontui/types.ts desktop/src/frontui/mockState.ts desktop/src/lib/frontUiAdapters.ts desktop/tests/frontUiAdapters.test.ts
git commit -m "Add frontUI view models and adapter coverage"
```

### Task 3: Port frontUI shell components with renderer-safe tests

**Files:**
- Create: `desktop/src/frontui/AppShell.tsx`
- Create: `desktop/src/frontui/Sidebar.tsx`
- Create: `desktop/src/frontui/ChatList.tsx`
- Create: `desktop/src/frontui/ChatWindow.tsx`
- Test: `desktop/tests/frontUiShell.test.tsx`

- [ ] **Step 1: Write failing markup tests for the frontUI shell structure**

```tsx
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { FrontAppShell } from '../src/frontui/AppShell'
import { FrontSidebar } from '../src/frontui/Sidebar'
import { FrontChatList } from '../src/frontui/ChatList'
import { FrontChatWindow } from '../src/frontui/ChatWindow'

describe('frontUI shell markup', () => {
  it('renders the frontUI three-column window scaffold', () => {
    const html = renderToStaticMarkup(
      <FrontAppShell
        sidebar={<FrontSidebar activeTab="chat" onTabChange={() => undefined} onOpenSettings={() => undefined} />}
        list={<FrontChatList items={[]} activeChatId={null} searchQuery="" onSearchChange={() => undefined} onSelectChat={() => undefined} />}
        window={<FrontChatWindow state={{ mode: 'placeholder' }} onSendMessage={() => undefined} />}
      />, 
    )

    expect(html).toContain('bg-[#2e2e2e]')
    expect(html).toContain('w-[280px]')
    expect(html).toContain('min-w-[400px]')
  })
})
```

- [ ] **Step 2: Run the test to confirm the frontUI components are missing**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiShell
```

Expected: FAIL because the `desktop/src/frontui/*.tsx` files are not present.

- [ ] **Step 3: Port the frontUI components with desktop-safe props**

Use the existing `D:\frontUI\src\app\components\Sidebar.tsx`, `ChatList.tsx`, and `ChatWindow.tsx` as the source of truth, but adapt props away from mockData ownership.

`desktop/src/frontui/AppShell.tsx`:

```tsx
import type { ReactNode } from 'react'

export function FrontAppShell({ sidebar, list, window }: { sidebar: ReactNode; list: ReactNode; window: ReactNode }) {
  return (
    <div className="h-screen w-screen bg-[#f5f5f5] flex items-center justify-center overflow-hidden">
      <div className="w-full h-full max-w-[1200px] max-h-[800px] min-w-[800px] min-h-[600px] bg-white flex shadow-2xl rounded-none md:rounded-md overflow-hidden">
        {sidebar}
        {list}
        {window}
      </div>
    </div>
  )
}
```

`desktop/src/frontui/Sidebar.tsx` should keep the icon layout from frontUI, but expose callbacks like `onTabChange`, `onOpenSettings`, and `onOpenImport` instead of owning mock state.

`desktop/src/frontui/ChatList.tsx` should render `FrontChatListItem[]` and keep the frontUI search/header visuals.

`desktop/src/frontui/ChatWindow.tsx` should preserve the frontUI visual message layout while taking a `FrontChatWindowState` object and a controlled `onSendMessage(text)` callback.

- [ ] **Step 4: Run shell tests and inspect generated HTML**

Run:

```powershell
cd D:\newProj\desktop
npm test -- frontUiShell
```

Expected: PASS, and the rendered markup contains the exact frontUI shell class signatures used in the tests.

- [ ] **Step 5: Commit**

```bash
git add desktop/src/frontui/AppShell.tsx desktop/src/frontui/Sidebar.tsx desktop/src/frontui/ChatList.tsx desktop/src/frontui/ChatWindow.tsx desktop/tests/frontUiShell.test.tsx
git commit -m "Port the frontUI chat shell into the desktop renderer"
```

### Task 4: Rewire App.tsx to the frontUI shell while preserving real desktop flows

**Files:**
- Modify: `desktop/src/App.tsx`
- Modify: `desktop/src/lib/adapters.ts`
- Modify or delete after cutover: `desktop/src/components/AppShell.tsx`
- Modify or delete after cutover: `desktop/src/components/SidebarNav.tsx`
- Modify or delete after cutover: `desktop/src/components/ConversationListPane.tsx`
- Modify or delete after cutover: `desktop/src/components/ChatPane.tsx`
- Test: `desktop/tests/visualShell.test.tsx`
- Test: `desktop/tests/desktopBridge.test.ts`

- [ ] **Step 1: Write failing integration tests for the new app shell behavior**

```tsx
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import App from '../src/App'

describe('App frontUI integration', () => {
  it('keeps the boot screen outside the frontUI shell until services are ready', () => {
    const html = renderToStaticMarkup(<App />)
    expect(html).toContain('桌面应用正在初始化')
  })
})
```

Add a second assertion in `desktop/tests/visualShell.test.tsx` that checks the ready-state shell includes the frontUI window wrapper instead of `desktop-window__sidebar`.

- [ ] **Step 2: Run the tests to capture the current mismatch**

Run:

```powershell
cd D:\newProj\desktop
npm test -- visualShell
```

Expected: FAIL because `App.tsx` still renders the legacy `AppShell` / `SidebarNav` / `ConversationListPane` / `ChatPane` composition.

- [ ] **Step 3: Replace the renderer composition with frontUI containers**

In `desktop/src/App.tsx`, keep the existing boot polling, settings hydration, import logic, and rewrite/simulation state. Replace only the ready-state render path.

Target shape:

```tsx
return state.phase !== 'ready' ? (
  <BootScreen label={label} detail={state.detail} />
) : (
  <>
    <FrontAppShell
      sidebar={
        <FrontSidebar
          activeTab={activeTab}
          onTabChange={setActiveTab}
          onOpenSettings={() => setShowSettings(true)}
          onOpenImport={() => setShowImportDialog(true)}
        />
      }
      list={
        <FrontChatList
          items={frontListItems}
          activeChatId={selectedConversationId}
          searchQuery={conversationSearch}
          onSearchChange={setConversationSearch}
          onSelectChat={handleSelectConversation}
        />
      }
      window={
        <FrontChatWindow
          state={frontChatWindowState}
          onSendMessage={handleMockSendUntilRealComposerExists}
          rightPanel={rewriteOrBranchPanel}
        />
      }
    />

    <WelcomeModal ... />
    <SettingsDrawer ... />
    <ImportDialog ... />
  </>
)
```

Rules for this task:

- Keep `BootScreen`, `WelcomeModal`, `SettingsDrawer`, and `ImportDialog` mounted from the current desktop implementation.
- Use the new adapter layer for all frontUI props.
- Preserve existing list/message fetch behavior.
- If message sending is not yet backed by a real API, keep the frontUI input area visible but use a temporary no-op/mock handler that only updates local state for the active renderer session.

- [ ] **Step 4: Run full tests and a production build**

Run:

```powershell
cd D:\newProj\desktop
npm test
npm run typecheck
npm run build
```

Expected: PASS. The desktop renderer should build with the new frontUI shell while the Electron main/preload build still succeeds.

- [ ] **Step 5: Commit**

```bash
git add desktop/src/App.tsx desktop/src/lib/adapters.ts desktop/src/components/AppShell.tsx desktop/src/components/SidebarNav.tsx desktop/src/components/ConversationListPane.tsx desktop/src/components/ChatPane.tsx desktop/tests/visualShell.test.tsx desktop/tests/desktopBridge.test.ts
git commit -m "Swap the desktop shell to the frontUI chat layout"
```

### Task 5: Record the real-vs-mock migration status and verify the desktop app manually

**Files:**
- Create: `docs/project-status.md`
- Modify: `README.md`
- Test: manual Electron run

- [ ] **Step 1: Write the migration status document with an explicit capability table**

Create or update `docs/project-status.md` with a table like:

```md
| Area | Front-end Entry | Data Source | Current State | Next Step |
| --- | --- | --- | --- | --- |
| 会话列表 | 主界面中栏 | `/conversations` + latest jobs | Real | polish unread/timestamp/avatar mapping |
| 消息浏览 | 主界面右栏 | `/messages` | Real | map richer message types |
| 发送消息输入框 | 主界面右栏底部 | local mock only | Mock | replace with explicit unsupported-state UX or real reply drafting flow |
| 联系人标签页 | 左侧 contacts 图标 | mockState | Mock | define real product behavior |
| 文件标签页 | 左侧 files 图标 | mockState | Mock | define real product behavior |
| 设置 | 侧边栏设置入口 | `/settings` | Real | restyle to frontUI system |
| 导入聊天记录 | 侧边栏/列表入口 | desktop bridge + `/imports/qq-text` | Real | unify entry placement in shell |
| 分析 / 推演 / 分支 | 临时保留入口 | existing desktop logic | Mixed | embed into new shell panels |
```

- [ ] **Step 2: Update the README quickstart status note**

Add one paragraph under the desktop section:

```md
桌面前端当前已切换到 frontUI 主聊天壳。主聊天浏览链路优先接入真实后端；部分非核心标签页与输入操作仍可能使用临时 mock，详见 `docs/project-status.md`。
```

- [ ] **Step 3: Run manual Electron verification**

Run:

```powershell
cd D:\newProj\desktop
npm run dev
```

In a second terminal:

```powershell
cd D:\newProj\desktop
npm run build:electron
$env:IF_THEN_DESKTOP_RENDERER_URL = "http://127.0.0.1:5173"
npx electron .
```

Expected manual checks:

- boot screen still appears before readiness
- ready state opens the frontUI three-column shell
- real conversations appear in the middle list
- selecting a conversation loads real message history into the frontUI chat window
- settings and import flows are still reachable

- [ ] **Step 4: Re-run the full regression set after the manual check**

Run:

```powershell
cd D:\newProj\desktop
npm test
npm run typecheck
npm run build
```

Expected: PASS after the manual verification confirms the GUI is wired correctly.

- [ ] **Step 5: Commit**

```bash
git add docs/project-status.md README.md
git commit -m "Document frontUI migration status and desktop verification"
```

---

## Self-Review

### Spec coverage
- frontUI 作为视觉母版：Task 1 + Task 3 + Task 4 cover the shell migration.
- 保留 desktop 现有真实功能：Task 4 explicitly preserves boot, settings, import, and current orchestration.
- 允许 mock 过渡：Task 2 defines `mockState`, Task 5 documents every mock area.
- 用文档而非前端标识记录状态：Task 5 writes the status summary into `docs/project-status.md`.
- 先拿下主聊天界面视觉一致性：Task 3 + Task 4 prioritize the frontUI three-column shell.

### Placeholder scan
- No `TODO` / `TBD` placeholders remain.
- Every task names exact files and commands.
- Code-bearing steps include concrete code snippets or explicit target shapes.

### Type consistency
- `FrontChatListItem`, `FrontChatMessage`, and `FrontChatWindowState` are defined in Task 2 before Task 3/4 consume them.
- The frontUI renderer shell names (`FrontAppShell`, `FrontSidebar`, `FrontChatList`, `FrontChatWindow`) stay consistent across tasks.
- The migration status summary now lives in `docs/project-status.md`.
