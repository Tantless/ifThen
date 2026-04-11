# Windows Native Titlebar Modernization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Upgrade the Electron desktop shell to a Windows-friendly modern titlebar with small window corner radius, Win11-first native appearance enhancements, and Win10-safe fallback, while keeping the existing app body and custom titlebar structure largely unchanged.

**Architecture:** Keep the current frameless Electron window and React titlebar component, but introduce a focused window-appearance helper on the Electron side plus small shell/titlebar styling updates on the renderer side. Drive the work with tests first: one lane for BrowserWindow appearance options and one lane for renderer/titlebar markup + CSS behavior.

**Tech Stack:** Electron 37, React 19, TypeScript, Vitest, Vite, CSS

---

## File Structure / Responsibility Map

- Create: `desktop/electron/backend/windowAppearance.ts`
  - Single responsibility: compute Windows-aware BrowserWindow appearance options and shell tokens without mixing in boot logic.
- Create: `desktop/tests/windowAppearance.test.ts`
  - Unit tests for Win10 / Win11 window appearance resolution.
- Modify: `desktop/electron/main.ts`
  - Consume appearance helper when constructing `BrowserWindow`.
- Modify: `desktop/tests/windowChrome.test.ts`
  - Assert modernized window options are forwarded into BrowserWindow creation.
- Modify: `desktop/src/frontui/WindowTitleBar.tsx`
  - Keep structure/drag regions, modernize titlebar classes only.
- Modify: `desktop/src/frontui/AppShell.tsx`
  - Add shell-level class hooks needed for rounded outer frame and titlebar clipping.
- Modify: `desktop/src/styles/frontui.css`
  - Add shell/titlebar modern Windows styling and safe fallback behavior.
- Modify: `desktop/tests/frontUiShell.test.tsx`
  - Assert the new shell/titlebar class signatures render as expected.

---

### Task 1: Lock in Electron window appearance behavior with tests

**Files:**
- Create: `desktop/tests/windowAppearance.test.ts`
- Modify: `desktop/tests/windowChrome.test.ts`
- Read for context: `desktop/electron/main.ts`, `desktop/tests/windowChrome.test.ts`

- [ ] **Step 1: Write the failing appearance helper tests**

Create `desktop/tests/windowAppearance.test.ts` with:

```ts
import { describe, expect, it } from 'vitest'

import { getWindowsAppearanceOptions } from '../electron/backend/windowAppearance'

describe('getWindowsAppearanceOptions', () => {
  it('returns Win11-first enhancements for Windows 11 builds', () => {
    const result = getWindowsAppearanceOptions({
      platform: 'win32',
      release: '10.0.22631',
    })

    expect(result).toMatchObject({
      backgroundColor: '#00000000',
      roundedCorners: true,
      titleBarStyle: 'hidden',
      frame: false,
    })
  })

  it('returns a conservative fallback for Windows 10 builds', () => {
    const result = getWindowsAppearanceOptions({
      platform: 'win32',
      release: '10.0.19045',
    })

    expect(result).toMatchObject({
      frame: false,
      titleBarStyle: 'hidden',
      roundedCorners: false,
    })
    expect(result.backgroundColor).toBe('#f3f3f3')
  })

  it('keeps non-Windows platforms on the existing safe defaults', () => {
    const result = getWindowsAppearanceOptions({
      platform: 'darwin',
      release: '23.0.0',
    })

    expect(result).toMatchObject({
      frame: false,
      titleBarStyle: 'hidden',
      backgroundColor: '#f5f5f5',
    })
  })
})
```

- [ ] **Step 2: Run the new test and verify it fails**

Run:

```bash
cd desktop
npm test -- --runInBand desktop/tests/windowAppearance.test.ts
```

Expected: FAIL with module-not-found for `../electron/backend/windowAppearance` or missing export `getWindowsAppearanceOptions`.

- [ ] **Step 3: Extend the BrowserWindow contract test before implementation**

Update `desktop/tests/windowChrome.test.ts` expectation block to prepare for the new modern shell options:

```ts
expect(BrowserWindow).toHaveBeenCalledWith(
  expect.objectContaining({
    frame: false,
    titleBarStyle: 'hidden',
    show: false,
    roundedCorners: expect.any(Boolean),
    backgroundColor: expect.any(String),
    webPreferences: expect.objectContaining({
      preload: expect.stringMatching(/preload\.cjs$/),
      contextIsolation: true,
      nodeIntegration: false,
    }),
  }),
)
```

- [ ] **Step 4: Run the window chrome test and verify it still fails for the missing appearance helper path**

Run:

```bash
cd desktop
npm test -- --runInBand desktop/tests/windowChrome.test.ts
```

Expected: FAIL after `main.ts` is updated later, or currently PASS on old defaults; if it passes now, continue because the stricter assertion is groundwork for the next task.

- [ ] **Step 5: Commit the test-first scaffolding**

```bash
git add desktop/tests/windowAppearance.test.ts desktop/tests/windowChrome.test.ts
git commit -m "Define the Windows titlebar appearance contract before shell changes

Constraint: Must preserve frameless custom titlebar architecture
Rejected: Ad hoc appearance flags directly in main.ts | harder to test and reason about per Windows version
Confidence: high
Scope-risk: narrow
Directive: Keep BrowserWindow appearance logic isolated from backend boot orchestration
Tested: Added focused Vitest coverage for window appearance resolution
Not-tested: Runtime Electron behavior on a real Windows host"
```

---

### Task 2: Implement Windows-aware BrowserWindow appearance resolution

**Files:**
- Create: `desktop/electron/backend/windowAppearance.ts`
- Modify: `desktop/electron/main.ts`
- Test: `desktop/tests/windowAppearance.test.ts`, `desktop/tests/windowChrome.test.ts`

- [ ] **Step 1: Implement the appearance helper with explicit Win10 / Win11 branching**

Create `desktop/electron/backend/windowAppearance.ts`:

```ts
import type { BrowserWindowConstructorOptions } from 'electron'

type WindowsAppearanceInput = {
  platform: NodeJS.Platform
  release: string
}

function isWindows11(release: string): boolean {
  const build = Number.parseInt(release.split('.').at(-1) ?? '', 10)
  return Number.isFinite(build) && build >= 22000
}

export function getWindowsAppearanceOptions(
  input: WindowsAppearanceInput,
): Pick<BrowserWindowConstructorOptions, 'frame' | 'titleBarStyle' | 'backgroundColor' | 'roundedCorners'> {
  if (input.platform !== 'win32') {
    return {
      frame: false,
      titleBarStyle: 'hidden',
      backgroundColor: '#f5f5f5',
      roundedCorners: false,
    }
  }

  if (isWindows11(input.release)) {
    return {
      frame: false,
      titleBarStyle: 'hidden',
      backgroundColor: '#00000000',
      roundedCorners: true,
    }
  }

  return {
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#f3f3f3',
    roundedCorners: false,
  }
}
```

- [ ] **Step 2: Wire the helper into Electron window creation**

Update the top of `desktop/electron/main.ts`:

```ts
import os from 'node:os'
import { getWindowsAppearanceOptions } from './backend/windowAppearance.js'
```

Then replace the hard-coded appearance fields inside `createWindow()`:

```ts
const appearance = getWindowsAppearanceOptions({
  platform: process.platform,
  release: os.release(),
})

const win = new BrowserWindow({
  width: 1440,
  height: 900,
  minWidth: 1100,
  minHeight: 700,
  ...appearance,
  show: false,
  webPreferences: {
    preload: fileURLToPath(new URL('./preload.cjs', import.meta.url)),
    contextIsolation: true,
    nodeIntegration: false,
  },
})
```

- [ ] **Step 3: Run the focused Electron tests**

Run:

```bash
cd desktop
npm test -- --runInBand desktop/tests/windowAppearance.test.ts desktop/tests/windowChrome.test.ts
```

Expected:

```text
2 files passed
```

- [ ] **Step 4: Typecheck the Electron-side change**

Run:

```bash
cd desktop
npm run typecheck
```

Expected: PASS with no TypeScript errors.

- [ ] **Step 5: Commit the window appearance implementation**

```bash
git add desktop/electron/backend/windowAppearance.ts desktop/electron/main.ts desktop/tests/windowAppearance.test.ts desktop/tests/windowChrome.test.ts
git commit -m "Prepare the Electron shell for Windows-native titlebar styling

Constraint: Win11 should get stronger appearance enhancements while Win10 stays on a safe fallback
Rejected: One shared appearance preset for all Windows versions | loses the requested Win11-first behavior
Confidence: medium
Scope-risk: moderate
Directive: Do not move shell appearance branching into renderer code; window creation owns platform-specific chrome decisions
Tested: Focused window appearance Vitest suite; desktop typecheck
Not-tested: Real Windows 10 and Windows 11 runtime rendering"
```

---

### Task 3: Modernize the shell/titlebar renderer without changing app body structure

**Files:**
- Modify: `desktop/src/frontui/AppShell.tsx`
- Modify: `desktop/src/frontui/WindowTitleBar.tsx`
- Modify: `desktop/src/styles/frontui.css`
- Test: `desktop/tests/frontUiShell.test.tsx`

- [ ] **Step 1: Write the failing renderer-shell assertions**

Update `desktop/tests/frontUiShell.test.tsx` titlebar/shell expectations:

```ts
expect(html).toContain('desktop-titlebar')
expect(html).toContain('desktop-titlebar--windows-modern')
expect(html).toContain('desktop-titlebar__drag-region')
expect(html).toContain('desktop-titlebar__controls')
```

And extend the app shell markup expectation with:

```ts
expect(rendered).toContain('desktop-shell-root')
expect(rendered).toContain('desktop-shell-root--windows-modern')
expect(rendered).toContain('desktop-shell-main')
expect(rendered).toContain('desktop-shell-main--windowed')
```

If the existing test block has no rendered shell string yet, use this render:

```tsx
const rendered = renderToStaticMarkup(
  <FrontAppShell
    titleBar={<div>title</div>}
    sidebar={<aside>sidebar</aside>}
    list={<section>list</section>}
    window={<main>window</main>}
  />,
)
```

- [ ] **Step 2: Run the shell test and verify it fails**

Run:

```bash
cd desktop
npm test -- --runInBand desktop/tests/frontUiShell.test.tsx
```

Expected: FAIL because the new class signatures are not present yet.

- [ ] **Step 3: Add shell-level class hooks in AppShell**

Update `desktop/src/frontui/AppShell.tsx`:

```tsx
export function FrontAppShell({ titleBar, sidebar, list, window, aside }: FrontAppShellProps) {
  return (
    <div className="desktop-shell-root desktop-shell-root--windows-modern h-screen w-screen overflow-hidden bg-[#f5f5f5]">
      <div className="desktop-shell-main desktop-shell-main--windowed flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden bg-white">
        {titleBar ? <div className="desktop-shell-titlebar">{titleBar}</div> : null}
        <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
          {sidebar}
          {list}
          {window}
          {aside}
        </div>
      </div>
    </div>
  )
}
```

- [ ] **Step 4: Modernize the titlebar class contract without changing behavior**

Update the `header` class in `desktop/src/frontui/WindowTitleBar.tsx`:

```tsx
<header
  className="desktop-titlebar desktop-titlebar--windows-modern flex h-10 w-full items-stretch justify-between text-[#1f1f1f] select-none"
  style={dragRegionStyle}
>
```

Update the control buttons to use shared Windows-modern class hooks:

```tsx
className="desktop-titlebar__button desktop-titlebar__button--windows desktop-titlebar__button--minimize flex h-10 w-12 items-center justify-center text-sm text-[#4c4c4c] transition-colors"
```

```tsx
className="desktop-titlebar__button desktop-titlebar__button--windows desktop-titlebar__button--maximize flex h-10 w-12 items-center justify-center text-sm text-[#4c4c4c] transition-colors"
```

```tsx
className="desktop-titlebar__button desktop-titlebar__button--windows desktop-titlebar__button--close flex h-10 w-12 items-center justify-center text-sm text-[#4c4c4c] transition-colors"
```

- [ ] **Step 5: Add the CSS for rounded outer shell and modern Windows titlebar styling**

Append this focused block to `desktop/src/styles/frontui.css`:

```css
.desktop-shell-root--windows-modern {
  background:
    radial-gradient(circle at top, rgba(255, 255, 255, 0.72), rgba(255, 255, 255, 0.08) 38%, transparent 64%),
    #eef1f5;
}

.desktop-shell-main--windowed {
  border-radius: 12px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  background: rgba(255, 255, 255, 0.88);
  box-shadow:
    0 18px 48px rgba(18, 24, 33, 0.14),
    0 2px 8px rgba(18, 24, 33, 0.08);
  overflow: hidden;
}

.desktop-titlebar--windows-modern {
  background: linear-gradient(to bottom, rgba(250, 251, 252, 0.82), rgba(244, 246, 248, 0.72));
  border-bottom: 1px solid rgba(26, 32, 44, 0.08);
  backdrop-filter: blur(18px) saturate(1.15);
}

.desktop-titlebar__button--windows:hover {
  background: rgba(17, 24, 39, 0.06);
}

.desktop-titlebar__button--windows:active {
  background: rgba(17, 24, 39, 0.1);
}

.desktop-titlebar__button--close:hover {
  background: #e81123;
  color: #fff;
}
```

- [ ] **Step 6: Run the shell renderer test and confirm it passes**

Run:

```bash
cd desktop
npm test -- --runInBand desktop/tests/frontUiShell.test.tsx
```

Expected:

```text
1 file passed
```

- [ ] **Step 7: Commit the renderer-shell modernization**

```bash
git add desktop/src/frontui/AppShell.tsx desktop/src/frontui/WindowTitleBar.tsx desktop/src/styles/frontui.css desktop/tests/frontUiShell.test.tsx
git commit -m "Modernize the custom titlebar without disturbing the app body

Constraint: Visual changes must stay scoped to the outer shell and titlebar
Rejected: Full-page component restyling | outside the approved scope
Confidence: medium
Scope-risk: narrow
Directive: Keep new shell classes additive so the body layout can stay stable while the window chrome evolves
Tested: frontUiShell Vitest coverage
Not-tested: Pixel-level visual QA on Windows hardware"
```

---

### Task 4: Full verification and manual Windows QA checklist

**Files:**
- Verify only: existing changed files from Tasks 1-3

- [ ] **Step 1: Run the full desktop test suite**

Run:

```bash
cd desktop
npm test
```

Expected: PASS across the desktop test suite.

- [ ] **Step 2: Run desktop build validation**

Run:

```bash
cd desktop
npm run build
```

Expected: Vite renderer build and Electron TypeScript build both pass.

- [ ] **Step 3: Perform focused manual validation on Windows**

Use this checklist:

```text
[ ] Window opens without black corners or white edge seams
[ ] Titlebar drag region still drags the window
[ ] Minimize button works
[ ] Maximize / restore works
[ ] Close works
[ ] Win11 shows a stronger modern titlebar feel than Win10
[ ] Win10 fallback still looks natural and stable
[ ] Main three-column layout remains unchanged
```

- [ ] **Step 4: Commit the verified finish**

```bash
git add desktop/electron/main.ts desktop/electron/backend/windowAppearance.ts desktop/src/frontui/AppShell.tsx desktop/src/frontui/WindowTitleBar.tsx desktop/src/styles/frontui.css desktop/tests/windowAppearance.test.ts desktop/tests/windowChrome.test.ts desktop/tests/frontUiShell.test.tsx
git commit -m "Ship a Windows-friendly titlebar refresh with safe platform fallbacks

Constraint: Must preserve the current custom titlebar interaction model while improving native feel
Rejected: Native titlebar replacement | conflicts with the chosen keep-structure approach
Confidence: medium
Scope-risk: moderate
Directive: Re-test both Windows 10 and Windows 11 before expanding the visual language beyond the shell
Tested: desktop Vitest suite; desktop production build; manual shell QA checklist
Not-tested: Dark mode / non-Windows platform polish"
```

---

## Spec Coverage Check

- Win10 + Win11 都友好 → Tasks 1-2 introduce explicit version-aware window appearance branching.
- 保留当前自定义标题栏结构 → Task 3 keeps `WindowTitleBar` structure and drag regions, changing classes/styles only.
- 只改窗口外轮廓 + 标题栏 → Task 3 scopes renderer edits to `AppShell`, `WindowTitleBar`, and shell CSS.
- Win11 更强、Win10 降级 → Task 2 implements the platform split directly.
- 验证拖拽 / 窗口控制 / 主体布局不破坏 → Task 4 manual QA checklist covers these conditions.

## Self-Review Notes

- No `TODO` / `TBD` placeholders remain.
- All planned files have exact paths.
- Function names introduced in tests (`getWindowsAppearanceOptions`) match the implementation task.
- Commit steps use the repository’s Lore protocol instead of generic commit messages.

