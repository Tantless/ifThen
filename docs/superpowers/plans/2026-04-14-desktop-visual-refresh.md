# Desktop Visual Refresh Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Re-skin the Electron desktop frontend to match `DESIGN.md` without changing product behavior.

**Architecture:** Keep the existing component tree and service flow intact, but move the visual language to a shared warm-neutral desktop token set. Update the frontUI Tailwind classes and legacy modal/drawer CSS in parallel so the shell, dialogs, and overlays feel like one coherent Windows WeChat-inspired client.

**Tech Stack:** React 19, TypeScript, Tailwind CSS 4, shared CSS in `desktop/src/styles/frontui.css` and `desktop/src/styles.css`, Vitest

---

### Task 1: Establish Shared Design Tokens

**Files:**
- Modify: `desktop/src/styles/frontui.css`
- Modify: `desktop/src/styles/frontui/theme.css`
- Modify: `plan/TODO.md`

- [ ] Add the active task note to `plan/TODO.md` and capture current progress / risks.
- [ ] Define warm-neutral desktop tokens for backgrounds, borders, text, accent green, danger red, shadows, and motion timing in the front-end theme layer.
- [ ] Apply the new root font stack and body/window surfaces so every downstream component inherits the same baseline.

### Task 2: Refresh The Three-Column Shell

**Files:**
- Modify: `desktop/src/frontui/AppShell.tsx`
- Modify: `desktop/src/frontui/WindowTitleBar.tsx`
- Modify: `desktop/src/frontui/Sidebar.tsx`
- Modify: `desktop/src/frontui/ChatList.tsx`

- [ ] Rework the shell background, inner window surface, and dividers to match the restrained desktop palette from `DESIGN.md`.
- [ ] Make the titlebar feel more native and compact by reducing visual noise and relying on borders instead of strong fills.
- [ ] Update sidebar and chat list controls to use quieter hover/active states, compact search affordances, and a calmer context menu.

### Task 3: Refresh The Chat Window Without Touching Behavior

**Files:**
- Modify: `desktop/src/frontui/ChatWindow.tsx`
- Modify: `desktop/src/frontui/AppShell.tsx`

- [ ] Tighten header spacing and button hierarchy so the conversation content stays visually primary.
- [ ] Re-style composer controls, progress strips, history hints, rewrite overlays, and message bubbles to fit the new desktop system.
- [ ] Preserve all existing message roles, rewrite-state markers, and data attributes so logic and tests keep working.

### Task 4: Unify Modals, Drawer, And Overlay Surfaces

**Files:**
- Modify: `desktop/src/styles.css`
- Modify: `desktop/src/components/ChatHistoryDialog.tsx`
- Modify: `desktop/src/components/AnalysisInspector.tsx`
- Modify: `desktop/src/components/ImportDialog.tsx`
- Modify: `desktop/src/components/SettingsDrawer.tsx`
- Modify: `desktop/src/components/SelfAvatarDialog.tsx`
- Modify: `desktop/src/components/WelcomeModal.tsx`
- Modify: `desktop/src/components/AvatarPicker.tsx`
- Modify: `desktop/src/components/BootScreen.tsx`

- [ ] Replace the older blue-tinted modal / drawer treatments with `DESIGN.md` warm neutrals, compact buttons, thin borders, and restrained shadows.
- [ ] Re-style the chat history dialog and analysis inspector so tabs, search, calendars, cards, and action buttons all use the same desktop vocabulary.
- [ ] Keep markup stable wherever possible so this remains a visual refactor rather than a structural rewrite.

### Task 5: Update Visual Assertions And Verify

**Files:**
- Modify: `desktop/tests/frontUiShell.test.tsx`
- Modify: `desktop/tests/visualShell.test.tsx`

- [ ] Update any tests that assert old class tokens or old visual copy so they validate the new styling contract instead of stale colors.
- [ ] Run `npm test` in `desktop/` and fix any style-sensitive failures.
- [ ] Run `npm run typecheck` in `desktop/` and confirm the refactor stayed type-safe.

