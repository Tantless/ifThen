import { existsSync, readFileSync } from 'node:fs'
import { resolve } from 'node:path'
import { fileURLToPath } from 'node:url'
import { JSDOM } from 'jsdom'
import React, { type ReactElement, type ReactNode } from 'react'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { renderToStaticMarkup } from 'react-dom/server'
import { build } from 'vite'
import { afterEach, describe, expect, it, vi } from 'vitest'

import { FrontAppShell } from '../src/frontui/AppShell'
import { FrontChatList } from '../src/frontui/ChatList'
import { FrontChatWindow } from '../src/frontui/ChatWindow'
import { FrontSidebar } from '../src/frontui/Sidebar'
import { WindowTitleBar, type WindowTitleBarProps } from '../src/frontui/WindowTitleBar'
import {
  closeDesktopWindow,
  getDesktopWindowState,
  minimizeDesktopWindow,
  toggleDesktopWindowMaximize,
} from '../src/lib/windowControls'
import type { FrontChatListItem, FrontChatWindowState } from '../src/frontui/types'
import type { DesktopBridge } from '../src/types/desktop'

const desktopRoot = fileURLToPath(new URL('..', import.meta.url))
const viteConfigFile = resolve(desktopRoot, 'vite.config.ts')
const mountedRoots: Array<{ root: ReturnType<typeof createRoot>; container: HTMLDivElement }> = []
let activeDom: JSDOM | null = null

function collectElements(node: ReactNode): ReactElement[] {
  const items: ReactElement[] = []

  const visit = (value: ReactNode) => {
    if (!React.isValidElement(value)) {
      return
    }

    items.push(value)

    if ('children' in value.props) {
      React.Children.forEach(value.props.children, visit)
    }
  }

  visit(node)
  return items
}

function getReactProps<T extends Record<string, unknown>>(element: Element): T {
  const propsKey = Object.keys(element).find((key) => key.startsWith('__reactProps$'))
  if (!propsKey) {
    throw new Error('expected rendered DOM node to have React props attached')
  }

  return (element as Record<string, unknown>)[propsKey] as T
}

afterEach(() => {
  while (mountedRoots.length > 0) {
    const mounted = mountedRoots.pop()
    if (!mounted) {
      return
    }

    act(() => {
      mounted.root.unmount()
    })
    mounted.container.remove()
  }

  if (activeDom) {
    activeDom.window.close()
    activeDom = null
  }

  Reflect.deleteProperty(globalThis, 'window')
  Reflect.deleteProperty(globalThis, 'document')
  Reflect.deleteProperty(globalThis, 'navigator')
  Reflect.deleteProperty(globalThis, 'HTMLElement')
  Reflect.deleteProperty(globalThis, 'Event')
  Reflect.deleteProperty(globalThis, 'MouseEvent')
  Reflect.deleteProperty(globalThis, 'IS_REACT_ACT_ENVIRONMENT')
  Reflect.deleteProperty(globalThis, 'desktop')
})

describe('frontUI shell wiring', () => {
  it('imports only the frontUI stylesheet entry from the desktop main entrypoint', () => {
    const mainSource = readFileSync(new URL('../src/main.tsx', import.meta.url), 'utf8')

    expect(mainSource).toContain("import './styles/frontui.css'")
    expect(mainSource).not.toContain("import './styles.css'")
  })

  it('defines the frontUI stylesheet entry with upstream imports and root sizing', () => {
    const stylesheetUrl = new URL('../src/styles/frontui.css', import.meta.url)

    expect(existsSync(stylesheetUrl)).toBe(true)

    const stylesheet = readFileSync(stylesheetUrl, 'utf8')

    expect(stylesheet).toContain("@import './frontui/fonts.css';")
    expect(stylesheet).toContain("@import './frontui/tailwind.css';")
    expect(stylesheet).toContain("@import './frontui/theme.css';")
    expect(stylesheet).toMatch(/html\s*,\s*body\s*,\s*#root\s*\{[^}]*min-height\s*:\s*100%/s)
    expect(stylesheet).toMatch(/body\s*\{[^}]*margin\s*:\s*0/s)
    expect(stylesheet).toMatch(/body\s*\{[^}]*font-family\s*:/s)
    expect(stylesheet).toContain('.desktop-shell-root')
    expect(stylesheet).toContain('.desktop-shell-main')
    expect(stylesheet).toContain('.desktop-shell-titlebar')
    expect(stylesheet).toContain('.desktop-shell-drag-region')
    expect(stylesheet).toContain('.desktop-shell-actions')
    expect(stylesheet).toContain('.desktop-titlebar__actions')
  })

  it('registers the Tailwind v4 Vite plugin and required style-pipeline devDependencies', () => {
    const viteConfig = readFileSync(new URL('../vite.config.ts', import.meta.url), 'utf8')
    const packageJson = JSON.parse(readFileSync(new URL('../package.json', import.meta.url), 'utf8')) as {
      devDependencies?: Record<string, string>
    }

    expect(viteConfig).toContain("from '@tailwindcss/vite'")
    expect(viteConfig).toContain('tailwindcss()')
    expect(packageJson.devDependencies).toMatchObject({
      '@tailwindcss/vite': expect.any(String),
      tailwindcss: expect.any(String),
      'tw-animate-css': expect.any(String),
    })
  })

  it('builds the desktop renderer with the frontUI style pipeline enabled', async () => {
    const result = await build({
      configFile: viteConfigFile,
      root: desktopRoot,
      logLevel: 'silent',
      build: {
        write: false,
        emptyOutDir: false,
        minify: false,
      },
    })

    const outputs = (Array.isArray(result) ? result : [result]).flatMap((entry) =>
      'output' in entry ? entry.output : [],
    )

    expect(outputs.some((entry) => entry.type === 'asset' && entry.fileName.endsWith('.css'))).toBe(true)
    expect(outputs.some((entry) => entry.type === 'chunk' && entry.fileName.endsWith('.js'))).toBe(true)
  })
})

describe('frontUI shell markup', () => {
  it('renders a desktop titlebar scaffold with drag region and three window controls', () => {
    const html = renderToStaticMarkup(
      <WindowTitleBar
        appTitle="微信聊天"
        isMaximized={false}
        onMinimize={() => undefined}
        onToggleMaximize={() => undefined}
        onClose={() => undefined}
      />,
    )

    expect(html).toContain('desktop-titlebar')
    expect(html).toContain('w-full')
    expect(html).toContain('desktop-titlebar__drag-region')
    expect(html).toContain('desktop-titlebar__actions')
    expect(html).toContain('desktop-titlebar__icon--minimize')
    expect(html).toContain('desktop-titlebar__icon--maximize')
    expect(html).toContain('desktop-titlebar__icon--close')
    expect(html).toContain('微信聊天')
    expect(html).toContain('aria-label="最小化窗口"')
    expect(html).toContain('aria-label="最大化窗口"')
    expect(html).toContain('aria-label="关闭窗口"')
  })

  it('keeps titlebar props desktop-safe and switches the maximize label in maximized state', () => {
    const events: string[] = []
    const props: WindowTitleBarProps = {
      appTitle: 'If Then',
      isMaximized: true,
      onMinimize: () => events.push('minimize'),
      onToggleMaximize: () => events.push('toggle-maximize'),
      onClose: () => events.push('close'),
    }

    const tree = WindowTitleBar(props)
    const buttons = collectElements(tree).filter((element) => element.type === 'button')
    const rendered = renderToStaticMarkup(tree)

    expect(buttons.map((button) => button.props['aria-label'])).toEqual([
      '最小化窗口',
      '还原窗口',
      '关闭窗口',
    ])
    expect(buttons.every((button) => String(button.props.className).includes('h-10 w-12'))).toBe(true)
    expect(rendered).toContain('desktop-titlebar__icon--minimize')
    expect(rendered).toContain('desktop-titlebar__icon--restore')
    expect(rendered).toContain('desktop-titlebar__icon--close')
    expect((rendered.match(/h-3 w-3/g) ?? []).length).toBeGreaterThanOrEqual(3)
    expect((rendered.match(/viewBox="0 0 16 16"/g) ?? []).length).toBeGreaterThanOrEqual(3)
    expect((rendered.match(/fill="currentColor"/g) ?? []).length).toBeGreaterThanOrEqual(3)
    expect(rendered).not.toContain('rounded-full bg-current')
    expect(rendered).not.toContain('border-[1.5px] border-current')
    expect(rendered).not.toContain('h-[10px] w-[1.2px]')

    buttons[0]?.props.onClick?.()
    buttons[1]?.props.onClick?.()
    buttons[2]?.props.onClick?.()

    expect(events).toEqual(['minimize', 'toggle-maximize', 'close'])
  })

  it('renders the frontUI three-column scaffold with upstream class signatures', () => {
    const items: FrontChatListItem[] = [
      {
        id: 'conversation-7',
        conversationId: 7,
        displayName: '和小李的聊天',
        avatarUrl: 'https://example.test/avatar.png',
        previewText: '我 / 小李 · qq export v5',
        timestampLabel: '42%',
        progress: {
          label: '摘要生成 42%',
          percent: 42,
          tone: 'running',
        },
        unreadCount: 2,
        active: true,
        source: 'real',
      },
    ]

    const state: FrontChatWindowState = {
      mode: 'conversation',
      title: '和小李的聊天',
      messages: [
        {
          id: 'message-1',
          messageId: 1,
          align: 'left',
          speakerName: '小李',
          avatarUrl: 'https://example.test/other.png',
          text: '收到，稍后回你',
          timestampLabel: '10:01',
          timestampRaw: '2026-04-08T10:01:00',
          canRewrite: false,
          source: 'real',
        },
        {
          id: 'message-2',
          messageId: 2,
          align: 'right',
          speakerName: '我',
          avatarUrl: 'https://example.test/self.png',
          text: '那我们先这样吧',
          timestampLabel: '10:02',
          timestampRaw: '2026-04-08T10:02:00',
          canRewrite: true,
          source: 'real',
        },
      ],
    }

    const html = renderToStaticMarkup(
      <FrontAppShell
        sidebar={
          <FrontSidebar
            activeTab="chat"
            onTabChange={() => undefined}
            onOpenSettings={() => undefined}
            onOpenImport={() => undefined}
          />
        }
        list={
          <FrontChatList
            items={items}
            activeChatId={7}
            searchQuery=""
            onSearchChange={() => undefined}
            onSelectChat={() => undefined}
            onOpenImport={() => undefined}
          />
        }
        window={
          <FrontChatWindow
            state={state}
            analysisProgress={{ label: '摘要生成 42%', percent: 42, tone: 'running' }}
            onSendMessage={() => undefined}
          />
        }
      />,
    )

    expect(html).toContain('desktop-shell-root')
    expect(html).toContain('desktop-shell-main')
    expect(html).not.toContain('max-w-[1200px]')
    expect(html).not.toContain('max-h-[800px]')
    expect(html).toContain('bg-[#2e2e2e]')
    expect(html).toContain('w-[280px]')
    expect(html).toContain('w-[60px]')
    expect(html).toContain('min-w-[400px]')
    expect(html).toContain('min-h-0')
    expect(html).toContain('overflow-hidden')
    expect(html).toContain('custom-scrollbar')
    expect(html).toContain('rounded-lg rounded-tr-none')
    expect(html).toContain('发送(S)')
    expect(html).toContain('摘要生成 42%')
    expect(html).toContain('front-progress')
    expect(html).toContain('front-progress__fill')
  })

  it('composes the titleBar slot before the main content body with WindowTitleBar controls intact', () => {
    const dom = new JSDOM(
      renderToStaticMarkup(
        <FrontAppShell
          titleBar={
            <WindowTitleBar
              appTitle="If Then"
              isMaximized={false}
              onMinimize={() => undefined}
              onToggleMaximize={() => undefined}
              onClose={() => undefined}
            />
          }
          sidebar={
            <FrontSidebar
              activeTab="chat"
              onTabChange={() => undefined}
              onOpenSettings={() => undefined}
              onOpenImport={() => undefined}
            />
          }
          list={
            <FrontChatList
              items={[]}
              activeChatId={null}
              searchQuery=""
              onSearchChange={() => undefined}
              onSelectChat={() => undefined}
              onOpenImport={() => undefined}
            />
          }
          window={<FrontChatWindow state={{ mode: 'placeholder' }} onSendMessage={() => undefined} />}
        />,
      ),
    )

    const document = dom.window.document
    const shellMain = document.querySelector('.desktop-shell-main')
    const titleBarWrapper = document.querySelector('.desktop-shell-titlebar')
    const contentBody = shellMain?.children.item(1) ?? null

    expect(titleBarWrapper).not.toBeNull()
    expect(shellMain?.firstElementChild).toBe(titleBarWrapper)
    expect(contentBody).not.toBeNull()
    expect(titleBarWrapper?.compareDocumentPosition(contentBody as Element)).toBe(dom.window.Node.DOCUMENT_POSITION_FOLLOWING)
    expect(titleBarWrapper?.textContent).toContain('If Then')
    expect(document.querySelector('button[aria-label="最小化窗口"]')).not.toBeNull()
    expect(document.querySelector('button[aria-label="最大化窗口"]')).not.toBeNull()
    expect(document.querySelector('button[aria-label="关闭窗口"]')).not.toBeNull()
  })

  it('renders the placeholder chat state without requiring extra placeholder data', () => {
    const html = renderToStaticMarkup(<FrontChatWindow state={{ mode: 'placeholder' }} onSendMessage={() => undefined} />)

    expect(html).toContain('bg-[#f5f5f5]')
    expect(html).toContain('选择一段对话开始聊天')
  })

  it('wires sidebar and list callbacks to desktop-safe props', () => {
    const events: string[] = []

    const sidebarTree = FrontSidebar({
      activeTab: 'chat',
      onTabChange: (tab) => events.push(`tab:${tab}`),
      onOpenSettings: () => events.push('settings'),
      onOpenImport: () => events.push('import'),
    })
    const listTree = FrontChatList({
      items: [
        {
          id: 'conversation-7',
          conversationId: 7,
          displayName: '和小李的聊天',
          avatarUrl: 'https://example.test/avatar.png',
          previewText: '我 / 小李 · qq export v5',
          timestampLabel: '42%',
          progress: null,
          unreadCount: 0,
          active: true,
          source: 'real',
        },
      ],
      activeChatId: 7,
      searchQuery: '',
      onSearchChange: (value) => events.push(`search:${value}`),
      onSelectChat: (conversationId) => events.push(`select:${conversationId}`),
      onOpenImport: () => events.push('list-import'),
    })

    const sidebarButtons = collectElements(sidebarTree).filter((element) => element.type === 'button')
    const listInput = collectElements(listTree).find((element) => element.type === 'input')
    const listButtons = collectElements(listTree).filter((element) => element.type === 'button')

    sidebarButtons[1]?.props.onClick?.()
    sidebarButtons.at(-1)?.props.onClick?.()
    listInput?.props.onChange?.({ target: { value: '阿青' } })
    listButtons[0]?.props.onClick?.()
    listButtons[1]?.props.onClick?.()

    expect(events).toEqual(['tab:chat', 'settings', 'search:阿青', 'list-import', 'select:7'])
  })

  it('keeps the sidebar focused on chat list and settings entry points only', () => {
    const sidebarTree = FrontSidebar({
      activeTab: 'chat',
      onTabChange: () => undefined,
      onOpenSettings: () => undefined,
      onOpenImport: () => undefined,
    })

    const sidebarButtons = collectElements(sidebarTree).filter((element) => element.type === 'button')
    const labels = sidebarButtons.map((button) => String(button.props['aria-label'] ?? ''))

    expect(labels).toEqual(['返回聊天列表', '聊天', '设置'])
  })

  it('clears the composer draft when the runtime conversation key changes', () => {
    activeDom = new JSDOM('<!doctype html><html><body></body></html>')
    const { window } = activeDom
    Object.assign(globalThis, {
      window,
      document: window.document,
      navigator: window.navigator,
      HTMLElement: window.HTMLElement,
      Event: window.Event,
      MouseEvent: window.MouseEvent,
      IS_REACT_ACT_ENVIRONMENT: true,
    })
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      value: () => undefined,
      configurable: true,
    })

    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    mountedRoots.push({ root, container })

    const firstState: FrontChatWindowState = {
      mode: 'conversation',
      title: '同名会话',
      messages: [],
    }

    const secondState: FrontChatWindowState = {
      mode: 'conversation',
      title: '同名会话',
      messages: [],
    }

    act(() => {
      root.render(<FrontChatWindow state={firstState} conversationKey="conversation-1" onSendMessage={vi.fn()} />)
    })

    const textarea = container.querySelector('textarea')

    expect(textarea).not.toBeNull()

    if (!textarea) {
      throw new Error('expected chat composer textarea to render')
    }

    const textareaProps = getReactProps<{
      onChange?: (event: { target: { value: string } }) => void
    }>(textarea)

    act(() => {
      textareaProps.onChange?.({ target: { value: '第一段草稿' } })
    })

    expect(textarea.value).toBe('第一段草稿')

    act(() => {
      textareaProps.onChange?.({ target: { value: '第二段草稿' } })
    })

    act(() => {
      root.render(<FrontChatWindow state={secondState} conversationKey="conversation-2" onSendMessage={vi.fn()} />)
    })

    const rerenderedTextarea = container.querySelector('textarea')
    expect(rerenderedTextarea?.value).toBe('')
  })

  it('supports double-click and right-click entry for self-message rewrite', async () => {
    activeDom = new JSDOM('<!doctype html><html><body></body></html>')
    const { window } = activeDom
    Object.assign(globalThis, {
      window,
      document: window.document,
      navigator: window.navigator,
      HTMLElement: window.HTMLElement,
      Event: window.Event,
      MouseEvent: window.MouseEvent,
      IS_REACT_ACT_ENVIRONMENT: true,
    })
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      value: () => undefined,
      configurable: true,
    })

    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    mountedRoots.push({ root, container })

    const onStartRewrite = vi.fn()

    act(() => {
      root.render(
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
                text: '那我们先这样吧',
                timestampLabel: '10:02',
                timestampRaw: '2026-04-08T10:02:00',
                canRewrite: true,
                source: 'real',
              },
            ],
          }}
          conversationKey="conversation-7"
          onStartRewrite={onStartRewrite}
          onSendMessage={() => undefined}
        />,
      )
    })

    const rewriteTarget = container.querySelector('[data-chat-message-id="message-12"] .cursor-pointer')
    expect(rewriteTarget).not.toBeNull()

    act(() => {
      getReactProps<{
        onDoubleClick?: () => void
        onContextMenu?: (event: { preventDefault: () => void; clientX: number; clientY: number }) => void
      }>(rewriteTarget as Element).onDoubleClick?.()
    })

    expect(onStartRewrite).toHaveBeenCalledWith(12)

    act(() => {
      getReactProps<{
        onDoubleClick?: () => void
        onContextMenu?: (event: { preventDefault: () => void; clientX: number; clientY: number }) => void
      }>(rewriteTarget as Element).onContextMenu?.({
        preventDefault: () => undefined,
        clientX: 120,
        clientY: 80,
      })
    })

    const contextMenuButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('改写') ?? false,
    )
    expect(contextMenuButton).not.toBeUndefined()

    act(() => {
      if (contextMenuButton) {
        getReactProps<{ onClick?: () => void }>(contextMenuButton).onClick?.()
      }
    })

    expect(onStartRewrite).toHaveBeenCalledTimes(2)
  })

  it('renders a completed-simulation status bar and wires its actions', () => {
    activeDom = new JSDOM('<!doctype html><html><body></body></html>')
    const { window } = activeDom
    Object.assign(globalThis, {
      window,
      document: window.document,
      navigator: window.navigator,
      HTMLElement: window.HTMLElement,
      Event: window.Event,
      MouseEvent: window.MouseEvent,
      IS_REACT_ACT_ENVIRONMENT: true,
    })
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      value: () => undefined,
      configurable: true,
    })

    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    mountedRoots.push({ root, container })

    const onResetRewriteView = vi.fn()
    const onContinueRewrite = vi.fn()

    act(() => {
      root.render(
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
                text: '我想先冷静一下，晚点继续聊可以吗？',
                timestampLabel: '10:02',
                timestampRaw: '2026-04-08T10:02:00',
                canRewrite: true,
                source: 'real',
              },
              {
                id: 'message-13',
                messageId: 13,
                align: 'left',
                speakerName: '小李',
                avatarUrl: 'https://example.test/other.png',
                text: '好，那晚点再说。',
                timestampLabel: '10:03',
                timestampRaw: '2026-04-08T10:03:00',
                canRewrite: false,
                source: 'real',
              },
            ],
          }}
          conversationKey="conversation-7"
          rewriteState={{
            state: 'completed',
            targetMessageId: 12,
            draftText: '我想先冷静一下，晚点继续聊可以吗？',
            generatedMessages: [
              {
                id: 'simulation-1',
                messageId: null,
                align: 'left',
                speakerName: '小李',
                avatarUrl: 'https://example.test/other.png',
                text: '好，那你先休息。',
                timestampLabel: '10:03',
                timestampRaw: '2026-04-08T10:03:00',
                canRewrite: false,
                source: 'mock',
              },
            ],
          }}
          onResetRewriteView={onResetRewriteView}
          onContinueRewrite={onContinueRewrite}
          onSendMessage={() => undefined}
        />,
      )
    })

    expect(container.textContent).toContain('正在查看推演结果')
    expect(container.textContent).toContain('原始历史已保留，可随时切回')
    expect(container.textContent).toContain('好，那你先休息。')

    const buttons = Array.from(container.querySelectorAll('button'))
    const resetButton = buttons.find((element) => element.textContent?.includes('返回原始历史') ?? false)
    const continueButton = buttons.find((element) => element.textContent?.includes('继续改写') ?? false)

    expect(resetButton).not.toBeUndefined()
    expect(continueButton).not.toBeUndefined()

    act(() => {
      if (resetButton) {
        getReactProps<{ onClick?: () => void }>(resetButton).onClick?.()
      }
      if (continueButton) {
        getReactProps<{ onClick?: () => void }>(continueButton).onClick?.()
      }
    })

    expect(onResetRewriteView).toHaveBeenCalledTimes(1)
    expect(onContinueRewrite).toHaveBeenCalledTimes(1)
  })

  it('renders the rewrite pending progress as a floating overlay instead of a chat-stream item', () => {
    activeDom = new JSDOM('<!doctype html><html><body></body></html>')
    const { window } = activeDom
    Object.assign(globalThis, {
      window,
      document: window.document,
      navigator: window.navigator,
      HTMLElement: window.HTMLElement,
      Event: window.Event,
      MouseEvent: window.MouseEvent,
      IS_REACT_ACT_ENVIRONMENT: true,
    })
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      value: () => undefined,
      configurable: true,
    })

    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    mountedRoots.push({ root, container })

    act(() => {
      root.render(
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
                text: '我想先冷静一下，晚点继续聊可以吗？',
                timestampLabel: '10:02',
                timestampRaw: '2026-04-08T10:02:00',
                canRewrite: true,
                source: 'real',
              },
              {
                id: 'message-13',
                messageId: 13,
                align: 'left',
                speakerName: '小李',
                avatarUrl: 'https://example.test/other.png',
                text: '好，那晚点再说。',
                timestampLabel: '10:03',
                timestampRaw: '2026-04-08T10:03:00',
                canRewrite: false,
                source: 'real',
                ghosted: true,
              },
            ],
          }}
          conversationKey="conversation-7"
          rewriteState={{
            state: 'pending',
            targetMessageId: 12,
            draftText: '我想先冷静一下，晚点继续聊可以吗？',
            stageLabel: '结合人格中……',
            generatedMessages: [],
          }}
          onSendMessage={() => undefined}
        />,
      )
    })

    const overlay = container.querySelector('[data-testid="rewrite-pending-overlay"]')
    const scrollContainer = container.querySelector('[data-testid="chat-message-scroll"]')

    expect(overlay).not.toBeNull()
    expect(overlay?.textContent).toContain('正在推演')
    expect(overlay?.textContent).toContain('结合人格中')
    expect(overlay?.className).toContain('absolute')
    expect(overlay?.className).toContain('bottom-6')
    expect(scrollContainer?.contains(overlay as Node)).toBe(false)
  })

  it('anchors the viewport when loading older messages and shows a wechat-like loading hint', async () => {
    activeDom = new JSDOM('<!doctype html><html><body></body></html>')
    const { window } = activeDom
    Object.assign(globalThis, {
      window,
      document: window.document,
      navigator: window.navigator,
      HTMLElement: window.HTMLElement,
      Event: window.Event,
      MouseEvent: window.MouseEvent,
      IS_REACT_ACT_ENVIRONMENT: true,
    })
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      value: () => undefined,
      configurable: true,
    })

    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    mountedRoots.push({ root, container })

    const recentMessages = Array.from({ length: 80 }, (_, index) => ({
      id: `message-${index + 21}`,
      messageId: index + 21,
      align: (index + 21) % 2 === 0 ? ('right' as const) : ('left' as const),
      speakerName: (index + 21) % 2 === 0 ? '我' : '阿青',
      avatarUrl: 'https://example.test/avatar.png',
      text: `最近消息 ${index + 21}`,
      timestampLabel: `10:${String(index).padStart(2, '0')}`,
      timestampRaw: `2026-04-08T10:${String(index).padStart(2, '0')}:00`,
      canRewrite: false,
      source: 'real' as const,
    }))
    const olderMessages = Array.from({ length: 20 }, (_, index) => ({
      id: `message-${index + 1}`,
      messageId: index + 1,
      align: (index + 1) % 2 === 0 ? ('right' as const) : ('left' as const),
      speakerName: (index + 1) % 2 === 0 ? '我' : '阿青',
      avatarUrl: 'https://example.test/avatar.png',
      text: `更早消息 ${index + 1}`,
      timestampLabel: `09:${String(index).padStart(2, '0')}`,
      timestampRaw: `2026-04-08T09:${String(index).padStart(2, '0')}:00`,
      canRewrite: false,
      source: 'real' as const,
    }))
    let resolveOlderLoad: (() => void) | null = null

    function Harness() {
      const [messages, setMessages] = React.useState(recentMessages)
      const [pending, setPending] = React.useState(false)

      const handleLoadOlderMessages = async () => {
        setPending(true)
        await new Promise<void>((resolve) => {
          resolveOlderLoad = resolve
        })
        setMessages((current) => [...olderMessages, ...current])
        setPending(false)
      }

      return (
        <FrontChatWindow
          state={{ mode: 'conversation', title: '和阿青的聊天', messages }}
          conversationKey="conversation-7"
          onSendMessage={() => undefined}
          hasOlderMessages={messages.length < recentMessages.length + olderMessages.length}
          olderMessagesPending={pending}
          onLoadOlderMessages={handleLoadOlderMessages}
        />
      )
    }

    act(() => {
      root.render(<Harness />)
    })

    const scrollContainer = container.querySelector('[data-testid="chat-message-scroll"]') as HTMLDivElement | null
    expect(scrollContainer).not.toBeNull()

    if (!scrollContainer) {
      throw new Error('expected chat message scroll container to render')
    }

    Object.defineProperty(scrollContainer, 'clientHeight', {
      value: 600,
      configurable: true,
    })
    Object.defineProperty(scrollContainer, 'scrollHeight', {
      value: 1200,
      configurable: true,
    })
    Object.defineProperty(scrollContainer, 'getBoundingClientRect', {
      value: () => ({
        top: 100,
        bottom: 700,
        left: 0,
        right: 400,
        width: 400,
        height: 600,
        x: 0,
        y: 100,
        toJSON: () => undefined,
      }),
      configurable: true,
    })
    Object.defineProperty(window.HTMLElement.prototype, 'getBoundingClientRect', {
      value: function getBoundingClientRect() {
        if (this === scrollContainer) {
          return {
            top: 100,
            bottom: 700,
            left: 0,
            right: 400,
            width: 400,
            height: 600,
            x: 0,
            y: 100,
            toJSON: () => undefined,
          }
        }

        const messageId = this.getAttribute?.('data-chat-message-id')
        if (!messageId) {
          return {
            top: 0,
            bottom: 0,
            left: 0,
            right: 0,
            width: 0,
            height: 0,
            x: 0,
            y: 0,
            toJSON: () => undefined,
          }
        }

        const messageElements = Array.from(scrollContainer.querySelectorAll('[data-chat-message-id]'))
        const index = messageElements.indexOf(this as Element)
        const top = 116 + index * 48 - scrollContainer.scrollTop

        return {
          top,
          bottom: top + 40,
          left: 0,
          right: 320,
          width: 320,
          height: 40,
          x: 0,
          y: top,
          toJSON: () => undefined,
        }
      },
      configurable: true,
    })
    act(() => {
      scrollContainer.scrollTop = 0
      scrollContainer.dispatchEvent(new window.Event('scroll', { bubbles: true }))
    })

    await act(async () => {
      await Promise.resolve()
    })

    expect(container.textContent).toContain('正在加载聊天记录')
    expect(container.innerHTML).toContain('backdrop-blur-md')
    expect(container.innerHTML).toContain('animate-pulse')

    await act(async () => {
      resolveOlderLoad?.()
      await Promise.resolve()
      await Promise.resolve()
    })

    expect(scrollContainer.scrollTop).toBeGreaterThan(900)
  })

  it('does not auto-trigger another older-message load until the user scrolls away from the top threshold', async () => {
    activeDom = new JSDOM('<!doctype html><html><body></body></html>')
    const { window } = activeDom
    Object.assign(globalThis, {
      window,
      document: window.document,
      navigator: window.navigator,
      HTMLElement: window.HTMLElement,
      Event: window.Event,
      MouseEvent: window.MouseEvent,
      IS_REACT_ACT_ENVIRONMENT: true,
    })
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      value: () => undefined,
      configurable: true,
    })

    const container = document.createElement('div')
    document.body.appendChild(container)
    const root = createRoot(container)
    mountedRoots.push({ root, container })

    const messages = Array.from({ length: 80 }, (_, index) => ({
      id: `message-${index + 1}`,
      messageId: index + 1,
      align: index % 2 === 0 ? ('left' as const) : ('right' as const),
      speakerName: index % 2 === 0 ? '阿青' : '我',
      avatarUrl: 'https://example.test/avatar.png',
      text: `消息 ${index + 1}`,
      timestampLabel: `10:${String(index).padStart(2, '0')}`,
      timestampRaw: `2026-04-08T10:${String(index).padStart(2, '0')}:00`,
      canRewrite: false,
      source: 'real' as const,
    }))

    const onLoadOlderMessages = vi.fn(async () => undefined)

    act(() => {
      root.render(
        <FrontChatWindow
          state={{ mode: 'conversation', title: '和阿青的聊天', messages }}
          conversationKey="conversation-7"
          onSendMessage={() => undefined}
          hasOlderMessages
          olderMessagesPending={false}
          onLoadOlderMessages={onLoadOlderMessages}
        />,
      )
    })

    const scrollContainer = container.querySelector('[data-testid="chat-message-scroll"]') as HTMLDivElement | null
    expect(scrollContainer).not.toBeNull()

    if (!scrollContainer) {
      throw new Error('expected chat message scroll container to render')
    }

    act(() => {
      scrollContainer.scrollTop = 0
      scrollContainer.dispatchEvent(new window.Event('scroll', { bubbles: true }))
    })
    await act(async () => {
      await Promise.resolve()
    })

    expect(onLoadOlderMessages).toHaveBeenCalledTimes(1)

    act(() => {
      scrollContainer.scrollTop = 0
      scrollContainer.dispatchEvent(new window.Event('scroll', { bubbles: true }))
    })
    await act(async () => {
      await Promise.resolve()
    })

    expect(onLoadOlderMessages).toHaveBeenCalledTimes(1)

    act(() => {
      scrollContainer.scrollTop = 120
      scrollContainer.dispatchEvent(new window.Event('scroll', { bubbles: true }))
      scrollContainer.scrollTop = 0
      scrollContainer.dispatchEvent(new window.Event('scroll', { bubbles: true }))
    })
    await act(async () => {
      await Promise.resolve()
    })

    expect(onLoadOlderMessages).toHaveBeenCalledTimes(2)
  })
})

describe('desktop window controls', () => {
  it('returns safe fallbacks when the desktop window bridge is unavailable', async () => {
    await expect(getDesktopWindowState()).resolves.toEqual({ isMaximized: false })
    await expect(minimizeDesktopWindow()).resolves.toBeUndefined()
    await expect(toggleDesktopWindowMaximize()).resolves.toEqual({ isMaximized: false })
    await expect(closeDesktopWindow()).resolves.toBeUndefined()
  })

  it('forwards titlebar window actions to the desktop bridge when available', async () => {
    const calls: string[] = []

    ;(globalThis as typeof globalThis & { desktop?: DesktopBridge }).desktop = {
      getServiceState: async () => ({ phase: 'ready' }),
      pickImportFile: async () => ({ canceled: true, filePaths: [] }),
      getAppInfo: async () => ({ name: 'If Then', version: '0.1.0' }),
      readImportFile: async () => ({ fileName: 'chat.txt', content: '第一行' }),
      window: {
        minimize: async () => void calls.push('minimize'),
        toggleMaximize: async () => {
          calls.push('toggle-maximize')
          return { isMaximized: true }
        },
        close: async () => void calls.push('close'),
        getState: async () => {
          calls.push('get-state')
          return { isMaximized: true }
        },
      },
    }

    await expect(getDesktopWindowState()).resolves.toEqual({ isMaximized: true })
    await minimizeDesktopWindow()
    await expect(toggleDesktopWindowMaximize()).resolves.toEqual({ isMaximized: true })
    await closeDesktopWindow()

    expect(calls).toEqual(['get-state', 'minimize', 'toggle-maximize', 'close'])
  })
})
