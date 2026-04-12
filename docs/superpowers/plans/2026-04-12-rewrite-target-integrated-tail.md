# Rewrite Target Integrated Tail Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the rewritten-message pure triangle tail with a visually integrated tail piece that shares the same material as the bubble body.

**Architecture:** Keep ordinary and simulation bubbles on the current border-triangle tail implementation, but special-case `rewrite-target` so it renders a dedicated tail element with the same gradient, edge tone, and shadow as the main bubble. Drive the change with a failing renderer test first, then implement the minimal markup/class update in `ChatWindow.tsx`.

**Tech Stack:** React 19, TypeScript, Vitest, Tailwind utility classes

---

## File Structure / Responsibility Map

- Modify: `desktop/tests/frontUiShell.test.tsx`
  - Lock the new rewrite-target tail contract in a focused renderer test.
- Modify: `desktop/src/frontui/ChatWindow.tsx`
  - Render an integrated tail element for `rewrite-target` while leaving other bubble tails untouched.

---

### Task 1: Convert rewrite-target into a one-piece-looking bubble

**Files:**
- Modify: `desktop/tests/frontUiShell.test.tsx`
- Modify: `desktop/src/frontui/ChatWindow.tsx`

- [ ] **Step 1: Write the failing renderer assertion**

Change the existing rewrite-target test so it requires a dedicated integrated-tail marker instead of the old triangle-only signature:

```ts
expect(html).toContain('data-chat-tail-style="integrated"')
expect(html).not.toContain('border-l-[#d4e9ff]')
```

- [ ] **Step 2: Run the targeted shell test and verify it fails**

Run:

```bash
cd desktop
npm test -- desktop/tests/frontUiShell.test.tsx
```

Expected: FAIL because the rewrite-target branch still renders the border-triangle tail.

- [ ] **Step 3: Implement the minimal integrated tail**

In `desktop/src/frontui/ChatWindow.tsx`:

- branch `rewrite-target` away from the shared `bubbleArrowClass`
- render a dedicated `div` tail element with:
  - `data-chat-tail-style="integrated"`
  - the same rewrite gradient as the body
  - a matching blue border/shadow
  - a rounded, slightly rotated patch shape positioned behind the right-lower edge of the bubble

- [ ] **Step 4: Run the targeted shell test and verify it passes**

Run:

```bash
cd desktop
npm test -- desktop/tests/frontUiShell.test.tsx
```

Expected: PASS.

- [ ] **Step 5: Run desktop regression verification**

Run:

```bash
cd desktop
npm test
npm run typecheck
```

Expected:

```text
13 files passed / 104 tests passed
typecheck passes
```
