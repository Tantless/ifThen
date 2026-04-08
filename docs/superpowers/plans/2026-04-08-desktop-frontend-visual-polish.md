# Desktop Frontend Visual Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不改变桌面端核心流程的前提下，把现有 `desktop/` renderer 打磨成更像 Windows 本地聊天客户端的产品界面，并统一欢迎弹窗、设置抽屉、导入弹窗、rewrite/branch/inspector 的视觉语言。

**Architecture:** 继续沿用现有 React + TypeScript + 单文件 `styles.css` 方案，不引入新的 UI 体系。实现时按“全局视觉骨架 -> 主界面核心区 -> 弹层与抽屉 -> 分析增强层”的顺序推进，每个任务都通过小范围结构调整 + 样式收敛完成，避免重做数据流或 bridge。测试仍以现有 Vitest、类型检查、构建验证为主，必要时补最小 render/class contract 测试锁定关键 UI 结构。

**Tech Stack:** Electron, React, TypeScript, Vite, Vitest, CSS

---

## 执行状态（2026-04-08 同步）

- 状态：**已完成并已并入 `main`**
- 结果：桌面端三栏结构、欢迎弹窗、设置抽屉、导入弹窗与 analysis 增强层的视觉语言已统一到当前产品基线。
- 当前验证参考：`cd desktop && npm test` 为 `9 files / 46 tests passed`，`npm run typecheck` / `npm run build` 通过。
- 说明：下方 `- [ ]` 复选框保留为原始执行脚本，不再表示当前待办；当前总体进度以 `docs/2026-04-08-milestone-progress-summary.md` 为准。

## File Map

### Existing files to modify
- `desktop/src/styles.css`
- `desktop/src/components/AppShell.tsx`
- `desktop/src/components/SidebarNav.tsx`
- `desktop/src/components/ConversationListPane.tsx`
- `desktop/src/components/ConversationListItem.tsx`
- `desktop/src/components/ChatPane.tsx`
- `desktop/src/components/ChatHeader.tsx`
- `desktop/src/components/MessageTimeline.tsx`
- `desktop/src/components/MessageBubble.tsx`
- `desktop/src/components/WelcomeModal.tsx`
- `desktop/src/components/ImportDialog.tsx`
- `desktop/src/components/SettingsDrawer.tsx`
- `desktop/src/components/RewritePanel.tsx`
- `desktop/src/components/BranchView.tsx`
- `desktop/src/components/AnalysisInspector.tsx`
- `desktop/tests/chatState.test.ts`

### New files to create
- `desktop/tests/visualShell.test.tsx`
- `desktop/tests/modalChrome.test.tsx`

### Files explicitly out of scope
- `desktop/electron/**`
- `desktop/src/lib/services/**`
- `desktop/src/lib/apiClient.ts`
- backend Python source and tests (deprecated warning cleanup will be a separate plan)

---

### Task 1: Establish the desktop-window chrome and global visual tokens

**Files:**
- Modify: `desktop/src/styles.css`
- Modify: `desktop/src/components/AppShell.tsx`
- Modify: `desktop/src/components/SidebarNav.tsx`
- Test: `desktop/tests/visualShell.test.tsx`

- [ ] **Step 1: Write the failing shell render test**

```tsx
// desktop/tests/visualShell.test.tsx
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { AppShell } from '../src/components/AppShell'
import { SidebarNav } from '../src/components/SidebarNav'

describe('desktop shell chrome', () => {
  it('renders dedicated window, nav, list, and chat surface wrappers', () => {
    const html = renderToStaticMarkup(
      <AppShell
        sidebar={<SidebarNav />}
        listPane={<div>list</div>}
        chatPane={<div>chat</div>}
      />,
    )

    expect(html).toContain('desktop-window')
    expect(html).toContain('desktop-window__sidebar')
    expect(html).toContain('desktop-window__list')
    expect(html).toContain('desktop-window__chat')
  })

  it('keeps sidebar brand and settings affordance for desktop-app framing', () => {
    const html = renderToStaticMarkup(<SidebarNav />)
    expect(html).toContain('sidebar-nav__brand')
    expect(html).toContain('sidebar-nav__footer')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test -- --run desktop/tests/visualShell.test.tsx`
Expected: FAIL because `AppShell`/`SidebarNav` do not yet expose the required wrapper class names.

- [ ] **Step 3: Add the minimal shell structure changes**

```tsx
// desktop/src/components/AppShell.tsx
import type { ReactNode } from 'react'

type AppShellProps = {
  sidebar: ReactNode
  listPane: ReactNode
  chatPane: ReactNode
}

export function AppShell({ sidebar, listPane, chatPane }: AppShellProps) {
  return (
    <main className="desktop-window">
      <aside className="desktop-window__sidebar">{sidebar}</aside>
      <section className="desktop-window__list">{listPane}</section>
      <section className="desktop-window__chat">{chatPane}</section>
    </main>
  )
}
```

```tsx
// desktop/src/components/SidebarNav.tsx (representative target shape)
export function SidebarNav() {
  return (
    <nav className="sidebar-nav">
      <div className="sidebar-nav__brand">
        <div className="sidebar-nav__brand-mark">如果</div>
      </div>
      <div className="sidebar-nav__items">...</div>
      <div className="sidebar-nav__footer">...</div>
    </nav>
  )
}
```

- [ ] **Step 4: Introduce the global desktop-window styling tokens**

```css
/* desktop/src/styles.css */
:root {
  color: #1f2329;
  background: #d9d8d7;
  font-family: "Segoe UI", system-ui, -apple-system, BlinkMacSystemFont, sans-serif;
}

body {
  margin: 0;
  min-width: 320px;
  min-height: 100vh;
  background: linear-gradient(180deg, #d7d6d5 0%, #cbcac9 100%);
}

.desktop-window {
  display: grid;
  grid-template-columns: 72px 308px minmax(0, 1fr);
  min-height: 100vh;
  background: #f5f5f5;
}

.desktop-window__sidebar {
  background: #2e2e2e;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
}

.desktop-window__list {
  background: #e7e6e6;
  border-right: 1px solid #d6d6d6;
}

.desktop-window__chat {
  background: #f5f5f5;
}

.sidebar-nav__footer {
  display: flex;
  flex-direction: column;
  gap: 12px;
  align-items: center;
}
```

- [ ] **Step 5: Run focused verification**

Run:
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test -- --run desktop/tests/visualShell.test.tsx`
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm run typecheck`

Expected: both pass.

- [ ] **Step 6: Commit**

```powershell
git add desktop/src/styles.css desktop/src/components/AppShell.tsx desktop/src/components/SidebarNav.tsx desktop/tests/visualShell.test.tsx
git commit -m "Make the desktop shell read like a native chat client"
```

---

### Task 2: Rework the conversation list and chat pane into a chat-client presentation

**Files:**
- Modify: `desktop/src/styles.css`
- Modify: `desktop/src/components/ConversationListPane.tsx`
- Modify: `desktop/src/components/ConversationListItem.tsx`
- Modify: `desktop/src/components/ChatPane.tsx`
- Modify: `desktop/src/components/ChatHeader.tsx`
- Modify: `desktop/src/components/MessageTimeline.tsx`
- Modify: `desktop/src/components/MessageBubble.tsx`
- Test: `desktop/tests/visualShell.test.tsx`
- Test: `desktop/tests/chatState.test.ts`

- [ ] **Step 1: Extend the failing render test for list/chat structure**

```tsx
// append to desktop/tests/visualShell.test.tsx
import { ConversationListPane } from '../src/components/ConversationListPane'
import { ChatPane } from '../src/components/ChatPane'

it('renders a desktop-style conversation toolbar and search shell', () => {
  const html = renderToStaticMarkup(
    <ConversationListPane
      items={[]}
      selectedConversationId={null}
      searchValue=""
      emptyMessage="empty"
      onSearchChange={() => undefined}
      onImportConversation={() => undefined}
      onOpenSettings={() => undefined}
      onSelectConversation={() => undefined}
    />,
  )

  expect(html).toContain('conversation-list-pane__toolbar')
  expect(html).toContain('conversation-list-pane__search-shell')
})

it('renders a split chat surface wrapper when detail panel is present', () => {
  const html = renderToStaticMarkup(
    <ChatPane
      title="小李"
      subtitle="来源：qq_text"
      status="completed"
      progressPercent={100}
      messages={[]}
      detailPanel={<aside>inspector</aside>}
    />,
  )

  expect(html).toContain('chat-pane__surface')
  expect(html).toContain('chat-pane__body--split')
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test -- --run desktop/tests/visualShell.test.tsx desktop/tests/chatState.test.ts`
Expected: FAIL because the new list/chat wrapper classes do not exist yet.

- [ ] **Step 3: Update list and chat component markup minimally**

```tsx
// desktop/src/components/ConversationListPane.tsx (target additions only)
<header className="conversation-list-pane__toolbar">
  <div className="conversation-list-pane__title-group">...</div>
  <div className="conversation-list-pane__toolbar-actions">...</div>
</header>

<label className="conversation-list-pane__search-shell">
  <span className="conversation-list-pane__search-icon">⌕</span>
  <input ... />
</label>
```

```tsx
// desktop/src/components/ChatPane.tsx (target additions only)
return (
  <section className="chat-pane">
    <div className="chat-pane__surface">
      <ChatHeader ... />
      <div className={`chat-pane__body${detailPanel ? ' chat-pane__body--split' : ''}`}>
        ...
      </div>
    </div>
  </section>
)
```

```tsx
// desktop/src/components/MessageBubble.tsx (target shape)
<article className={`message-bubble message-bubble--${message.align}`}>
  <div className="message-bubble__avatar-slot" />
  <div className="message-bubble__stack">
    <div className="message-bubble__meta">...</div>
    <div className="message-bubble__card">...</div>
  </div>
</article>
```

- [ ] **Step 4: Apply the list/chat visual pass in CSS**

```css
/* desktop/src/styles.css */
.conversation-list-pane {
  display: flex;
  flex-direction: column;
  height: 100%;
  padding: 0;
  color: #111111;
}

.conversation-list-pane__toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  height: 60px;
  padding: 10px 14px 8px;
  border-bottom: 1px solid #e3e3e3;
  background: #f7f7f7;
}

.conversation-list-pane__search-shell {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 10px 12px 0;
  padding: 0 10px;
  height: 34px;
  border-radius: 8px;
  background: #ededed;
  color: #888;
}

.conversation-list-item {
  border: 0;
  border-radius: 0;
  padding: 12px 14px;
  background: transparent;
  box-shadow: none;
}

.conversation-list-item--active {
  background: #d7d7d7;
}

.chat-pane__surface {
  display: flex;
  min-height: 100%;
  flex-direction: column;
  background: #f5f5f5;
}

.chat-header {
  min-height: 60px;
  padding: 14px 24px;
  border-bottom: 1px solid #e5e5e5;
  background: #f5f5f5;
}

.message-bubble__card {
  max-width: min(68%, 640px);
  border-radius: 8px;
  box-shadow: none;
}

.message-bubble--right .message-bubble__card {
  background: #95ec69;
}

.message-bubble--left .message-bubble__card {
  background: #ffffff;
}
```

- [ ] **Step 5: Run focused verification**

Run:
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test -- --run desktop/tests/visualShell.test.tsx desktop/tests/chatState.test.ts`
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm run typecheck`

Expected: both pass.

- [ ] **Step 6: Commit**

```powershell
git add desktop/src/styles.css desktop/src/components/ConversationListPane.tsx desktop/src/components/ConversationListItem.tsx desktop/src/components/ChatPane.tsx desktop/src/components/ChatHeader.tsx desktop/src/components/MessageTimeline.tsx desktop/src/components/MessageBubble.tsx desktop/tests/visualShell.test.tsx desktop/tests/chatState.test.ts
git commit -m "Make the conversation and chat panes feel like a desktop messenger"
```

---

### Task 3: Unify welcome, import, and settings surfaces under one desktop modal language

**Files:**
- Modify: `desktop/src/styles.css`
- Modify: `desktop/src/components/WelcomeModal.tsx`
- Modify: `desktop/src/components/ImportDialog.tsx`
- Modify: `desktop/src/components/SettingsDrawer.tsx`
- Test: `desktop/tests/modalChrome.test.tsx`

- [ ] **Step 1: Write the failing modal chrome test**

```tsx
// desktop/tests/modalChrome.test.tsx
import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { WelcomeModal } from '../src/components/WelcomeModal'
import { ImportDialog } from '../src/components/ImportDialog'
import { SettingsDrawer } from '../src/components/SettingsDrawer'

describe('desktop modal chrome', () => {
  it('renders welcome and import surfaces with shared desktop modal wrappers', () => {
    const welcome = renderToStaticMarkup(
      <WelcomeModal open onConfigureModel={() => undefined} onImportConversation={() => undefined} onClose={() => undefined} />,
    )
    const importDialog = renderToStaticMarkup(
      <ImportDialog open onClose={() => undefined} onSubmit={() => undefined} />,
    )

    expect(welcome).toContain('desktop-modal__panel')
    expect(importDialog).toContain('desktop-modal__panel')
  })

  it('renders settings inside a dedicated desktop drawer shell', () => {
    const html = renderToStaticMarkup(
      <SettingsDrawer
        open
        initialState={{ baseUrl: '', apiKey: '', chatModel: '' }}
        onClose={() => undefined}
        onSave={() => undefined}
      />,
    )

    expect(html).toContain('desktop-drawer')
    expect(html).toContain('desktop-drawer__header')
  })
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test -- --run desktop/tests/modalChrome.test.tsx`
Expected: FAIL because shared modal/drawer class names do not exist yet.

- [ ] **Step 3: Add the shared modal/drawer wrappers**

```tsx
// desktop/src/components/WelcomeModal.tsx (target shape)
<div className="desktop-modal" role="dialog" aria-modal="true">
  <section className="desktop-modal__panel desktop-modal__panel--welcome">...</section>
</div>
```

```tsx
// desktop/src/components/ImportDialog.tsx (target shape)
<div className="desktop-modal" role="dialog" aria-modal="true">
  <section className="desktop-modal__panel desktop-modal__panel--import">...</section>
</div>
```

```tsx
// desktop/src/components/SettingsDrawer.tsx (target shape)
<aside className="desktop-drawer" aria-label="模型设置">
  <header className="desktop-drawer__header">...</header>
  <form className="desktop-drawer__form">...</form>
</aside>
```

- [ ] **Step 4: Apply the unified modal/drawer styling**

```css
/* desktop/src/styles.css */
.desktop-modal {
  position: fixed;
  inset: 0;
  display: grid;
  place-items: center;
  padding: 24px;
  background: rgba(33, 33, 33, 0.28);
  backdrop-filter: blur(4px);
}

.desktop-modal__panel {
  width: min(520px, 100%);
  border-radius: 12px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  background: #ffffff;
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.12);
  padding: 24px;
  color: #111111;
}

.desktop-drawer {
  position: fixed;
  top: 0;
  right: 0;
  bottom: 0;
  width: min(420px, 100%);
  padding: 24px 22px;
  background: #ffffff;
  border-left: 1px solid #e5e5e5;
  box-shadow: -12px 0 32px rgba(0, 0, 0, 0.08);
}

.desktop-drawer__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.desktop-drawer__form {
  display: grid;
  gap: 16px;
  margin-top: 24px;
}
```

- [ ] **Step 5: Run focused verification**

Run:
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test -- --run desktop/tests/modalChrome.test.tsx`
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm run typecheck`

Expected: both pass.

- [ ] **Step 6: Commit**

```powershell
git add desktop/src/styles.css desktop/src/components/WelcomeModal.tsx desktop/src/components/ImportDialog.tsx desktop/src/components/SettingsDrawer.tsx desktop/tests/modalChrome.test.tsx
git commit -m "Unify desktop dialogs and settings drawer chrome"
```

---

### Task 4: Rebalance rewrite, branch, and inspector as secondary analysis surfaces

**Files:**
- Modify: `desktop/src/styles.css`
- Modify: `desktop/src/components/RewritePanel.tsx`
- Modify: `desktop/src/components/BranchView.tsx`
- Modify: `desktop/src/components/AnalysisInspector.tsx`
- Modify: `desktop/tests/chatState.test.ts`

- [ ] **Step 1: Extend the failing Task 5 render tests for secondary-surface chrome**

```tsx
// append to desktop/tests/chatState.test.ts
it('renders rewrite panel with desktop tool-surface classes and timestamp row', () => {
  const html = renderToStaticMarkup(
    React.createElement(RewritePanel, {
      originalMessage: '今天先到这里吧',
      originalTimestamp: '2026-04-08T09:00:00Z',
      replacementContent: '我们晚点继续聊可以吗？',
      mode: 'short_thread',
      turnCount: 3,
      pending: false,
      onReplacementContentChange: () => undefined,
      onModeChange: () => undefined,
      onTurnCountChange: () => undefined,
      onSubmit: () => undefined,
      onCancel: () => undefined,
    }),
  )

  expect(html).toContain('rewrite-panel__context')
  expect(html).toContain('发送时间')
})

it('renders inspector tabs as compact secondary tools instead of full-width sections', () => {
  const html = renderToStaticMarkup(
    React.createElement(AnalysisInspector, {
      open: true,
      currentTab: 'topics',
      loadingByTab: { topics: false, profile: false, snapshot: false },
      errorByTab: { topics: null, profile: null, snapshot: null },
      topics: [],
      profile: [],
      snapshot: null,
      onTabChange: () => undefined,
      onClose: () => undefined,
    }),
  )

  expect(html).toContain('analysis-inspector__tabs')
  expect(html).toContain('analysis-inspector__tab')
})
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test -- --run desktop/tests/chatState.test.ts`
Expected: FAIL because the new secondary-surface classes/props do not yet exist.

- [ ] **Step 3: Tighten the analysis-surface component markup**

```tsx
// desktop/src/components/RewritePanel.tsx (target additions only)
<div className="rewrite-panel__context">
  <div>
    <span className="rewrite-panel__label">原消息</span>
    <p className="rewrite-panel__quote">{originalMessage}</p>
  </div>
  <div>
    <span className="rewrite-panel__label">发送时间</span>
    <p className="rewrite-panel__timestamp">{formattedTimestamp}</p>
  </div>
</div>
```

```tsx
// desktop/src/components/BranchView.tsx (target additions only)
<div className="branch-view__summary-grid">...</div>
<section className="branch-view__turns branch-view__turns--secondary">...</section>
```

```tsx
// desktop/src/components/AnalysisInspector.tsx (target shape only)
<div className="analysis-inspector__tabs">
  <button className={...}>Topics</button>
  <button className={...}>Persona</button>
  <button className={...}>Snapshot</button>
</div>
<section className="analysis-inspector__panel">...</section>
```

- [ ] **Step 4: Apply the analysis-surface polish in CSS**

```css
/* desktop/src/styles.css */
.rewrite-panel {
  gap: 14px;
  padding: 20px 24px;
  border-bottom: 1px solid #e9e9e9;
  background: #ffffff;
}

.rewrite-panel__context {
  display: grid;
  gap: 12px;
  grid-template-columns: 1.5fr 1fr;
}

.branch-view {
  gap: 18px;
  padding: 20px 24px 28px;
  background: #f5f5f5;
}

.branch-view__summary-grid {
  display: grid;
  gap: 14px;
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.analysis-inspector {
  width: 300px;
  padding: 18px 16px 22px;
  border-left: 1px solid #e5e5e5;
  background: #fcfcfc;
}

.analysis-inspector__panel {
  padding: 14px;
  border-radius: 10px;
  background: #ffffff;
  border: 1px solid #ededed;
}
```

- [ ] **Step 5: Run focused verification**

Run:
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test -- --run desktop/tests/chatState.test.ts`
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm run typecheck`

Expected: both pass.

- [ ] **Step 6: Commit**

```powershell
git add desktop/src/styles.css desktop/src/components/RewritePanel.tsx desktop/src/components/BranchView.tsx desktop/src/components/AnalysisInspector.tsx desktop/tests/chatState.test.ts
git commit -m "Keep analysis tooling secondary to the chat surface"
```

---

### Task 5: Run the full desktop verification pass and document the visual-polish completion state

**Files:**
- Modify: `docs/superpowers/specs/2026-04-08-desktop-frontend-visual-polish-design.md` (only if a wording clarification is needed after implementation)
- Verify: `desktop/tests/visualShell.test.tsx`
- Verify: `desktop/tests/modalChrome.test.tsx`
- Verify: `desktop/tests/chatState.test.ts`

- [ ] **Step 1: Run the focused desktop polish suite**

Run:
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test -- --run desktop/tests/visualShell.test.tsx desktop/tests/modalChrome.test.tsx desktop/tests/chatState.test.ts`

Expected: PASS for all visual-polish and Task 5 regression tests.

- [ ] **Step 2: Run the full verification suite**

Run:
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm test`
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm run typecheck`
- `cd D:\newProj\.worktrees\electron-shell-bootstrap\desktop && npm run build`

Expected: all pass.

- [ ] **Step 3: Confirm the worktree only contains intended visual-polish changes**

Run:
- `git -C D:\newProj\.worktrees\electron-shell-bootstrap status --short`

Expected: only the files listed in this plan are modified or newly added.

- [ ] **Step 4: Commit the final integration checkpoint**

```powershell
git add desktop/src/styles.css desktop/src/components/AppShell.tsx desktop/src/components/SidebarNav.tsx desktop/src/components/ConversationListPane.tsx desktop/src/components/ConversationListItem.tsx desktop/src/components/ChatPane.tsx desktop/src/components/ChatHeader.tsx desktop/src/components/MessageTimeline.tsx desktop/src/components/MessageBubble.tsx desktop/src/components/WelcomeModal.tsx desktop/src/components/ImportDialog.tsx desktop/src/components/SettingsDrawer.tsx desktop/src/components/RewritePanel.tsx desktop/src/components/BranchView.tsx desktop/src/components/AnalysisInspector.tsx desktop/tests/visualShell.test.tsx desktop/tests/modalChrome.test.tsx desktop/tests/chatState.test.ts
git commit -m "Finish the desktop visual-polish pass" 
```

- [ ] **Step 5: Note the immediate next task after this plan**

After the visual polish is merged, create the next plan for backend deprecation-warning cleanup instead of mixing it into this branch.

---

## Self-Review Checklist

- Spec coverage:
  - 桌面窗口感：Task 1
  - 会话列表 / 聊天主区聊天客户端化：Task 2
  - Welcome / Import / Settings 统一弹层语言：Task 3
  - Rewrite / Branch / Inspector 作为增强层：Task 4
  - 完整验证与收口：Task 5
- Placeholder scan:
  - 无 `TODO` / `TBD` / “类似前一任务” 占位
- Type consistency:
  - 新测试文件统一使用 `tsx`
  - 不引入新 service 类型或后端契约变更
  - 视觉类名围绕 `desktop-window`, `desktop-modal`, `desktop-drawer`, `chat-pane__surface`, `analysis-inspector__panel` 等稳定命名
