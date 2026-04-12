# V2 Low-Effort UI Polish Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the five low-effort V2 desktop polish items: four-corner chat bubbles, a special rewrite-target material, WeChat-style timestamps, import-mode dropdown UI, and auto-scroll to the latest message after import.

**Architecture:** Keep the work inside the existing desktop frontUI flow. Use test-first changes in three focused lanes: shared chat message formatting/rendering, import dialog mode selection, and first-load message scroll behavior. Do not change backend contracts or expand into the high-effort chat-history modal work.

**Tech Stack:** React 19, TypeScript, Vitest, Vite, FastAPI backend contract (unchanged)

---

## File Structure / Responsibility Map

- Modify: `desktop/src/frontui/types.ts`
  - Extend the `bubbleTone` union with a dedicated rewrite-target tone.
- Modify: `desktop/src/lib/frontUiAdapters.ts`
  - Centralize chat timestamp formatting and reuse it for real/simulated messages.
- Modify: `desktop/src/frontui/ChatWindow.tsx`
  - Render four-corner bubbles, map the new rewrite-target material, and tighten initial bottom-scroll behavior.
- Modify: `desktop/src/App.tsx`
  - Tag the active rewrite target with its own bubble tone and reuse the shared timestamp formatter for local mock messages.
- Modify: `desktop/src/components/ImportDialog.tsx`
  - Replace the checkbox with a select-backed import mode UI while preserving the boolean submit payload.
- Modify: `desktop/tests/frontUiAdapters.test.ts`
  - Lock timestamp formatting and simulated-message formatting changes with failing tests first.
- Modify: `desktop/tests/frontUiShell.test.tsx`
  - Lock chat bubble rendering changes and import-dialog control changes with failing tests first.
- Modify: `desktop/tests/visualShell.test.tsx`
  - Lock app-level import payload and post-import scroll behavior with failing tests first.

---

### Task 1: Lock and implement chat bubble / timestamp behavior

**Files:**
- Modify: `desktop/tests/frontUiAdapters.test.ts`
- Modify: `desktop/tests/frontUiShell.test.tsx`
- Modify: `desktop/src/frontui/types.ts`
- Modify: `desktop/src/lib/frontUiAdapters.ts`
- Modify: `desktop/src/frontui/ChatWindow.tsx`
- Modify: `desktop/src/App.tsx`

- [ ] **Step 1: Write the failing timestamp-formatting tests**

Append these tests to `desktop/tests/frontUiAdapters.test.ts`:

```ts
describe('chat timestamp formatting', () => {
  it('formats same-day timestamps as HH:mm', () => {
    const result = buildFrontChatMessage({
      message: {
        id: 31,
        sequence_no: 1,
        speaker_name: '我',
        speaker_role: 'self',
        timestamp: '2026-04-12T13:17:00+08:00',
        content_text: '今天消息',
        message_type: 'text',
        resource_items: null,
      },
      selfAvatarUrl: 'self-avatar',
      now: '2026-04-12T18:00:00+08:00',
    })

    expect(result.timestampLabel).toBe('13:17')
  })

  it('formats yesterday / the day before / same-year / cross-year timestamps like WeChat', () => {
    const now = '2026-04-12T18:00:00+08:00'

    expect(
      buildFrontChatMessage({
        message: {
          id: 32,
          sequence_no: 2,
          speaker_name: '阿青',
          speaker_role: 'other',
          timestamp: '2026-04-11T13:17:00+08:00',
          content_text: '昨天消息',
          message_type: 'text',
          resource_items: null,
        },
        otherAvatarUrl: 'other-avatar',
        now,
      }).timestampLabel,
    ).toBe('昨天 13:17')

    expect(
      buildFrontChatMessage({
        message: {
          id: 33,
          sequence_no: 3,
          speaker_name: '阿青',
          speaker_role: 'other',
          timestamp: '2026-04-10T13:17:00+08:00',
          content_text: '前天消息',
          message_type: 'text',
          resource_items: null,
        },
        otherAvatarUrl: 'other-avatar',
        now,
      }).timestampLabel,
    ).toBe('前天 13:17')

    expect(
      buildFrontChatMessage({
        message: {
          id: 34,
          sequence_no: 4,
          speaker_name: '阿青',
          speaker_role: 'other',
          timestamp: '2026-03-01T13:17:00+08:00',
          content_text: '本年消息',
          message_type: 'text',
          resource_items: null,
        },
        otherAvatarUrl: 'other-avatar',
        now,
      }).timestampLabel,
    ).toBe('3月1日 13:17')

    expect(
      buildFrontChatMessage({
        message: {
          id: 35,
          sequence_no: 5,
          speaker_name: '阿青',
          speaker_role: 'other',
          timestamp: '2025-03-01T13:17:00+08:00',
          content_text: '往年消息',
          message_type: 'text',
          resource_items: null,
        },
        otherAvatarUrl: 'other-avatar',
        now,
      }).timestampLabel,
    ).toBe('2025年3月1日 13:17')
  })
})
```

- [ ] **Step 2: Run the adapter test and verify it fails**

Run:

```bash
cd desktop
npm test -- desktop/tests/frontUiAdapters.test.ts
```

Expected: FAIL because `buildFrontChatMessage` does not accept `now`, and timestamp labels are still plain `HH:mm`.

- [ ] **Step 3: Write the failing chat-bubble rendering tests**

Update `desktop/tests/frontUiShell.test.tsx`:

1. Change the three-column scaffold assertion from:

```ts
expect(html).toContain('rounded-lg rounded-tr-none')
```

to:

```ts
expect(html).toContain('rounded-[18px]')
expect(html).not.toContain('rounded-tr-none')
expect(html).not.toContain('rounded-tl-none')
```

2. Add a rewrite-target rendering assertion:

```ts
it('renders the active rewrite target with a dedicated material distinct from simulation bubbles', () => {
  const html = renderToStaticMarkup(
    <FrontChatWindow
      state={{
        mode: 'conversation',
        title: '和小李的聊天',
        messages: [
          {
            id: 'message-12',
            messageId: 12,
            align: 'right',
            speakerName: '我',
            avatarUrl: 'https://example.test/self.png',
            text: '改写后的消息',
            timestampLabel: '13:17',
            timestampRaw: '2026-04-12T13:17:00+08:00',
            canRewrite: true,
            source: 'real',
            bubbleTone: 'rewrite-target',
          },
        ],
      }}
      onSendMessage={() => undefined}
    />,
  )

  expect(html).toContain('data-chat-bubble-tone="rewrite-target"')
  expect(html).toContain('rewrite-target')
})
```

- [ ] **Step 4: Run the shell test and verify it fails**

Run:

```bash
cd desktop
npm test -- desktop/tests/frontUiShell.test.tsx
```

Expected: FAIL because the renderer still emits `rounded-*-none` and there is no `rewrite-target` tone support.

- [ ] **Step 5: Implement the minimal shared timestamp formatter and rewrite-target tone**

Make these focused changes:

1. In `desktop/src/frontui/types.ts`, extend the union:

```ts
bubbleTone?: 'default' | 'simulation-self' | 'simulation-other' | 'rewrite-target'
```

2. In `desktop/src/lib/frontUiAdapters.ts`, add a shared formatter and optional `now` input:

```ts
function startOfDay(value: Date): number {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime()
}

export function formatChatTimestampLabel(timestamp: string, nowInput?: string | Date): string {
  const trimmed = trimText(timestamp)
  if (!trimmed) {
    return ''
  }

  const target = new Date(trimmed)
  if (Number.isNaN(target.getTime())) {
    return trimmed
  }

  const now = nowInput ? new Date(nowInput) : new Date()
  const dayDiff = Math.round((startOfDay(now) - startOfDay(target)) / 86_400_000)
  const hhmm = `${String(target.getHours()).padStart(2, '0')}:${String(target.getMinutes()).padStart(2, '0')}`

  if (dayDiff === 0) return hhmm
  if (dayDiff === 1) return `昨天 ${hhmm}`
  if (dayDiff === 2) return `前天 ${hhmm}`
  if (target.getFullYear() === now.getFullYear()) return `${target.getMonth() + 1}月${target.getDate()}日 ${hhmm}`
  return `${target.getFullYear()}年${target.getMonth() + 1}月${target.getDate()}日 ${hhmm}`
}
```

Then update `buildFrontChatMessage` and `buildFrontChatMessagesFromSimulation` signatures to use `formatChatTimestampLabel(...)` instead of the old `resolveTimestampLabel(...)`.

3. In `desktop/src/App.tsx`, import `formatChatTimestampLabel` and use it for the local mock message:

```ts
timestampLabel: formatChatTimestampLabel(now.toISOString(), now),
```

4. In `desktop/src/App.tsx`, when rewriting the target message, set:

```ts
bubbleTone: 'rewrite-target',
```

5. In `desktop/src/frontui/ChatWindow.tsx`, map tones to full-round bubbles:

```ts
const bubbleClass =
  bubbleTone === 'rewrite-target'
    ? 'rounded-[18px] rewrite-target bg-[linear-gradient(135deg,#dff6ff_0%,#eef4ff_48%,#fdfcff_100%)] text-black ring-1 ring-[#8fd3ff]/80 shadow-[0_10px_28px_rgba(92,173,255,0.22)]'
    : bubbleTone === 'simulation-self'
      ? 'rounded-[18px] bg-[#d9ecff] text-black'
      : bubbleTone === 'simulation-other'
        ? 'rounded-[18px] bg-[#f8dce6] text-black'
        : isSelf
          ? 'rounded-[18px] bg-[#95ec69] text-black'
          : 'rounded-[18px] bg-white text-black'
```

Keep the arrow element, but remove any dependency on `rounded-tl-none` / `rounded-tr-none`.

- [ ] **Step 6: Run the focused tests and make sure they pass**

Run:

```bash
cd desktop
npm test -- desktop/tests/frontUiAdapters.test.ts desktop/tests/frontUiShell.test.tsx
```

Expected:

```text
2 files passed
```

---

### Task 2: Replace the import checkbox with a select-backed import mode

**Files:**
- Modify: `desktop/tests/frontUiShell.test.tsx`
- Modify: `desktop/tests/visualShell.test.tsx`
- Modify: `desktop/src/components/ImportDialog.tsx`

- [ ] **Step 1: Write the failing import-dialog control test**

Add this test to `desktop/tests/frontUiShell.test.tsx`:

```ts
it('renders import mode as a select with import-only as the default option', () => {
  const html = renderToStaticMarkup(
    <ImportDialog
      open
      onClose={() => undefined}
      onSubmit={() => undefined}
    />,
  )

  expect(html).toContain('导入模式')
  expect(html).toContain('<select')
  expect(html).toContain('只导入')
  expect(html).toContain('导入并分析')
  expect(html).not.toContain('type="checkbox"')
})
```

Remember to import `ImportDialog` at the top of the test file if it is not already present.

- [ ] **Step 2: Write the failing app-level payload test**

Strengthen the existing import integration test in `desktop/tests/visualShell.test.tsx` by asserting the select default and toggled submit payload:

```ts
const importModeSelect = container.querySelector('select') as HTMLSelectElement | null
expect(importModeSelect?.value).toBe('import_only')

await act(async () => {
  if (importModeSelect) {
    importModeSelect.value = 'import_and_analyze'
    getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(importModeSelect).onChange?.({
      target: { value: 'import_and_analyze' },
    })
  }
})
```

And update the payload expectation for that test case:

```ts
expect(mockedImportConversation).toHaveBeenCalledWith(
  expect.objectContaining({
    autoAnalyze: true,
  }),
)
```

- [ ] **Step 3: Run the two tests and verify they fail**

Run:

```bash
cd desktop
npm test -- desktop/tests/frontUiShell.test.tsx desktop/tests/visualShell.test.tsx
```

Expected: FAIL because the dialog still renders a checkbox and the select does not exist.

- [ ] **Step 4: Implement the select-backed import mode with boolean submit mapping**

Update `desktop/src/components/ImportDialog.tsx`:

1. Replace:

```ts
const [autoAnalyze, setAutoAnalyze] = useState(false)
```

with:

```ts
const [importMode, setImportMode] = useState<'import_only' | 'import_and_analyze'>('import_only')
```

2. Reset `importMode` to `'import_only'` inside the `open` effect.

3. Replace the checkbox field with:

```tsx
<label className="desktop-modal__field">
  <span className="desktop-modal__label">导入模式</span>
  <select
    className="desktop-modal__input"
    value={importMode}
    onChange={(event) => setImportMode(event.target.value as 'import_only' | 'import_and_analyze')}
  >
    <option value="import_only">只导入</option>
    <option value="import_and_analyze">导入并分析</option>
  </select>
</label>
```

4. Submit the preserved boolean contract:

```ts
autoAnalyze: importMode === 'import_and_analyze',
```

5. Keep the helper text, but drive it from `importMode` instead of the checkbox state.

- [ ] **Step 5: Run the focused tests and make sure they pass**

Run:

```bash
cd desktop
npm test -- desktop/tests/frontUiShell.test.tsx desktop/tests/visualShell.test.tsx
```

Expected:

```text
2 files passed
```

---

### Task 3: Fix initial post-import scrolling to the latest message and verify the whole batch

**Files:**
- Modify: `desktop/tests/visualShell.test.tsx`
- Modify: `desktop/src/frontui/ChatWindow.tsx`
- Verify: `desktop/src/App.tsx`, `desktop/src/lib/frontUiAdapters.ts`, `desktop/src/components/ImportDialog.tsx`

- [ ] **Step 1: Write the failing post-import scroll test**

Extend `desktop/tests/visualShell.test.tsx` with a focused assertion around the existing “导入新会话后会在消息尚未落库时重试加载” case:

```ts
const scrollIntoViewSpy = vi.fn()
Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
  value: scrollIntoViewSpy,
  configurable: true,
})
```

After the second `mockedListMessages` resolution and the visible message assertion, add:

```ts
expect(scrollIntoViewSpy).toHaveBeenCalled()
expect(scrollIntoViewSpy).toHaveBeenLastCalledWith({ behavior: 'auto' })
```

If the existing test already stubs `scrollIntoView`, update that stub into a spy and assert on it instead of creating a duplicate stub.

- [ ] **Step 2: Run the visual-shell test and verify it fails**

Run:

```bash
cd desktop
npm test -- desktop/tests/visualShell.test.tsx
```

Expected: FAIL because the first successful import render does not guarantee an `auto` scroll-to-bottom call for the newly loaded latest batch.

- [ ] **Step 3: Implement the minimal initial-load scroll fix**

Update the `useLayoutEffect` in `desktop/src/frontui/ChatWindow.tsx` so it distinguishes three cases:

```ts
const initialConversationLoad =
  !conversationChanged &&
  previous.count === 0 &&
  renderedMessages.length > 0

const shouldScrollToBottom =
  conversationChanged || appendedNewMessage || initialConversationLoad

if (olderMessageAnchorRef.current && scrollContainerRef.current) {
  // keep the existing anchor-preservation branch unchanged
} else if (shouldScrollToBottom) {
  messagesEndRef.current?.scrollIntoView({ behavior: conversationChanged || initialConversationLoad ? 'auto' : 'smooth' })
}
```

Keep the prepend-old-messages anchor branch first so loading older history still preserves the viewport.

- [ ] **Step 4: Run the focused visual-shell test and confirm it passes**

Run:

```bash
cd desktop
npm test -- desktop/tests/visualShell.test.tsx
```

Expected:

```text
1 file passed
```

- [ ] **Step 5: Run the full verification suite**

Run:

```bash
python -m pytest -q
cd desktop
npm test
npm run typecheck
```

Expected:

```text
83 passed
13 files passed / 99 tests passed
typecheck passes
```

- [ ] **Step 6: Commit the completed V2 low-effort polish batch**

```bash
git add \
  docs/superpowers/plans/2026-04-12-v2-low-effort-ui-polish.md \
  desktop/src/frontui/types.ts \
  desktop/src/lib/frontUiAdapters.ts \
  desktop/src/frontui/ChatWindow.tsx \
  desktop/src/App.tsx \
  desktop/src/components/ImportDialog.tsx \
  desktop/tests/frontUiAdapters.test.ts \
  desktop/tests/frontUiShell.test.tsx \
  desktop/tests/visualShell.test.tsx

git commit -m "Polish the V2 desktop chat flow so low-effort regressions stop breaking immersion

Constraint: Keep the fixes inside the current frontUI desktop flow without broad refactors or backend contract changes
Rejected: Fold the high-effort chat-history modal into the same batch | too broad for this polish pass
Confidence: medium
Scope-risk: moderate
Directive: Reuse the shared chat timestamp formatter and the dedicated rewrite-target tone instead of reintroducing ad hoc view logic
Tested: python -m pytest -q; cd desktop && npm test; cd desktop && npm run typecheck
Not-tested: Manual GUI review inside a live Electron session"
```

---

## Spec Coverage Check

- 四圆角消息气泡 → Task 1 updates both the renderer tests and the bubble class mapping.
- 改写目标消息特殊材质 → Task 1 adds a dedicated `rewrite-target` tone from `App.tsx` through `ChatWindow.tsx`.
- 微信式时间展示 → Task 1 introduces and tests a shared formatter used by real, simulated, and local mock messages.
- 导入模式下拉框 → Task 2 changes the dialog UI while preserving the existing `autoAnalyze` boolean contract.
- 导入后默认到底部 → Task 3 locks the first successful latest-batch render to an `auto` bottom scroll without touching older-message anchoring.

## Self-Review Notes

- No `TODO` / `TBD` placeholders remain.
- All tasks list exact files and commands.
- Type names and property names stay consistent with the existing frontUI code (`bubbleTone`, `timestampLabel`, `autoAnalyze`).
- The plan keeps the high-effort chat-history modal explicitly out of scope.
