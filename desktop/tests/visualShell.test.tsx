import React from 'react'
import { JSDOM } from 'jsdom'
import { act } from 'react'
import { createRoot } from 'react-dom/client'
import { renderToStaticMarkup } from 'react-dom/server'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import App from '../src/App'
import {
  deleteConversation,
  importConversation,
  listMessageDays,
  listConversations,
  listMessages,
  listTopics,
  readProfile,
  readSnapshot,
  startAnalysis,
} from '../src/lib/services/conversationService'
import { listConversationJobs, readJob } from '../src/lib/services/jobService'
import { createSimulation, listConversationSimulationJobs, readSimulation } from '../src/lib/services/simulationService'
import { readSettings, writeSetting } from '../src/lib/services/settingsService'
import type { ConversationRead, JobRead, MessageRead, SettingRead } from '../src/types/api'
import { AVATAR_PRESETS } from '../src/lib/avatarPresets'

vi.mock('../src/lib/services/conversationService', () => ({
  listConversations: vi.fn(),
  listMessages: vi.fn(),
  listMessageDays: vi.fn(),
  listTopics: vi.fn(),
  readProfile: vi.fn(),
  readSnapshot: vi.fn(),
  importConversation: vi.fn(),
  deleteConversation: vi.fn(),
  startAnalysis: vi.fn(),
}))

vi.mock('../src/lib/services/jobService', () => ({
  listConversationJobs: vi.fn(),
  readJob: vi.fn(),
}))

vi.mock('../src/lib/services/settingsService', () => ({
  readSettings: vi.fn(),
  writeSetting: vi.fn(),
}))

vi.mock('../src/lib/services/simulationService', () => ({
  createSimulation: vi.fn(),
  listConversationSimulationJobs: vi.fn(),
  readSimulation: vi.fn(),
}))

const mockedReadSettings = vi.mocked(readSettings)
const mockedWriteSetting = vi.mocked(writeSetting)
const mockedListConversations = vi.mocked(listConversations)
const mockedListMessages = vi.mocked(listMessages)
const mockedListMessageDays = vi.mocked(listMessageDays)
const mockedListTopics = vi.mocked(listTopics)
const mockedReadProfile = vi.mocked(readProfile)
const mockedReadSnapshot = vi.mocked(readSnapshot)
const mockedImportConversation = vi.mocked(importConversation)
const mockedDeleteConversation = vi.mocked(deleteConversation)
const mockedStartAnalysis = vi.mocked(startAnalysis)
const mockedListConversationJobs = vi.mocked(listConversationJobs)
const mockedReadJob = vi.mocked(readJob)
const mockedCreateSimulation = vi.mocked(createSimulation)
const mockedListConversationSimulationJobs = vi.mocked(listConversationSimulationJobs)
const mockedReadSimulation = vi.mocked(readSimulation)

const mountedRoots: Array<{ root: ReturnType<typeof createRoot>; container: HTMLDivElement }> = []
let activeDom: JSDOM | null = null

function getReactProps<T extends Record<string, unknown>>(element: Element): T {
  const propsKey = Object.keys(element).find((key) => key.startsWith('__reactProps$'))
  if (!propsKey) {
    throw new Error('expected rendered DOM node to have React props attached')
  }

  return (element as Record<string, unknown>)[propsKey] as T
}

function createDeferred<T>() {
  let resolve!: (value: T | PromiseLike<T>) => void
  let reject!: (reason?: unknown) => void
  const promise = new Promise<T>((innerResolve, innerReject) => {
    resolve = innerResolve
    reject = innerReject
  })

  return { promise, resolve, reject }
}

function installReadyDesktopBridge(options?: {
  initialIsMaximized?: boolean
  toggledIsMaximized?: boolean
  selectedImportPath?: string
  importFileName?: string
  importFileContent?: string
}) {
  const windowBridge = {
    getState: vi.fn(async () => ({ isMaximized: options?.initialIsMaximized ?? false })),
    minimize: vi.fn(async () => undefined),
    toggleMaximize: vi.fn(async () => ({ isMaximized: options?.toggledIsMaximized ?? true })),
    close: vi.fn(async () => undefined),
  }

  ;(globalThis as typeof globalThis & {
    desktop?: {
      getServiceState: () => Promise<{ phase: 'ready'; detail?: string }>
      pickImportFile: () => Promise<{ canceled: boolean; filePaths: string[] }>
      readImportFile: () => Promise<{ fileName: string; content: string }>
      getAppInfo: () => Promise<{ name: string; version: string }>
      window: typeof windowBridge
    }
  }).desktop = {
    getServiceState: async () => ({ phase: 'ready' }),
    pickImportFile: async () => ({
      canceled: !options?.selectedImportPath,
      filePaths: options?.selectedImportPath ? [options.selectedImportPath] : [],
    }),
    readImportFile: async () => ({
      fileName: options?.importFileName ?? 'chat.txt',
      content: options?.importFileContent ?? '聊天记录',
    }),
    getAppInfo: async () => ({ name: 'if-then-desktop', version: '0.1.0' }),
    window: windowBridge,
  }

  return windowBridge
}

function setupDom() {
  activeDom = new JSDOM('<!doctype html><html><body></body></html>')
  const { window } = activeDom

  Object.assign(globalThis, {
    window,
    document: window.document,
    HTMLElement: window.HTMLElement,
    Event: window.Event,
    MouseEvent: window.MouseEvent,
    IS_REACT_ACT_ENVIRONMENT: true,
  })
  Object.defineProperty(globalThis, 'navigator', {
    value: window.navigator,
    configurable: true,
  })

  Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
    value: () => undefined,
    configurable: true,
  })
  Object.defineProperty(window.HTMLElement.prototype, 'attachEvent', {
    value: () => undefined,
    configurable: true,
  })
  Object.defineProperty(window.HTMLElement.prototype, 'detachEvent', {
    value: () => undefined,
    configurable: true,
  })

  const container = document.createElement('div')
  document.body.appendChild(container)
  const root = createRoot(container)
  mountedRoots.push({ root, container })
  return { root, container }
}

async function flushAsyncWork(rounds = 6) {
  for (let index = 0; index < rounds; index += 1) {
    await act(async () => {
      if (vi.isFakeTimers()) {
        vi.advanceTimersByTime(0)
        await Promise.resolve()
        return
      }

      await new Promise((resolve) => setTimeout(resolve, 0))
    })
  }
}

async function advanceTimersAndFlush(ms: number, rounds = 6) {
  await act(async () => {
    vi.advanceTimersByTime(ms)
  })
  await flushAsyncWork(rounds)
}

beforeEach(() => {
  vi.clearAllMocks()
  installReadyDesktopBridge()
  mockedReadSettings.mockResolvedValue([])
  mockedWriteSetting.mockResolvedValue({
    setting_key: 'llm.base_url',
    setting_value: 'https://example.test/v1',
    is_secret: false,
  })
  mockedListConversations.mockResolvedValue([])
  mockedListMessages.mockResolvedValue([])
  mockedListMessageDays.mockResolvedValue([])
  mockedListTopics.mockResolvedValue([])
  mockedReadProfile.mockResolvedValue([])
  mockedReadSnapshot.mockResolvedValue({
    id: 1,
    as_of_message_id: 1,
    as_of_time: '2026-04-08T10:00:00',
    relationship_temperature: 'warm',
    tension_level: 'low',
    openness_level: 'medium',
    initiative_balance: 'balanced',
    defensiveness_level: 'low',
    unresolved_conflict_flags: [],
    relationship_phase: 'stable',
    snapshot_summary: '稳定',
  })
  mockedImportConversation.mockRejectedValue(new Error('not used in visual shell tests'))
  mockedDeleteConversation.mockRejectedValue(new Error('not used in visual shell tests'))
  mockedStartAnalysis.mockRejectedValue(new Error('not used in visual shell tests'))
  mockedListConversationJobs.mockResolvedValue([])
  mockedReadJob.mockResolvedValue({
    id: 1,
    status: 'completed',
    current_stage: 'completed',
    progress_percent: 100,
    current_stage_percent: 100,
    current_stage_total_units: 1,
    current_stage_completed_units: 1,
    overall_total_units: 1,
    overall_completed_units: 1,
    status_message: null,
  })
  mockedListConversationSimulationJobs.mockResolvedValue([])
  mockedCreateSimulation.mockResolvedValue({
    id: 88,
    conversation_id: 7,
    target_message_id: 12,
    mode: 'single_reply',
    turn_count: 1,
    replacement_content: '那我们先这样吧',
    status: 'queued',
    current_stage: 'queued',
    progress_percent: 0,
    current_stage_percent: 0,
    current_stage_total_units: 0,
    current_stage_completed_units: 0,
    overall_total_units: 0,
    overall_completed_units: 0,
    status_message: '等待 worker 处理',
    result_simulation_id: null,
    error_message: null,
  })
  mockedReadSimulation.mockResolvedValue({
    id: 88,
    mode: 'single_reply',
    replacement_content: '那我们先这样吧',
    first_reply_text: '好，我明白了。',
    impact_summary: '关系稳定，没有明显升级冲突。',
    simulated_turns: [],
  })
})

afterEach(() => {
  vi.useRealTimers()

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

  delete (globalThis as typeof globalThis & { desktop?: unknown }).desktop
  Reflect.deleteProperty(globalThis, 'window')
  Reflect.deleteProperty(globalThis, 'document')
  Reflect.deleteProperty(globalThis, 'navigator')
  Reflect.deleteProperty(globalThis, 'HTMLElement')
  Reflect.deleteProperty(globalThis, 'Event')
  Reflect.deleteProperty(globalThis, 'MouseEvent')
  Reflect.deleteProperty(globalThis, 'IS_REACT_ACT_ENVIRONMENT')
})

describe('App frontUI integration', () => {
  it('在服务未 ready 前保持 boot screen，不提前渲染 frontUI 主壳', () => {
    const html = renderToStaticMarkup(<App />)

    expect(html).toContain('桌面应用正在初始化')
    expect(html).not.toContain('w-[60px]')
    expect(html).not.toContain('desktop-window__sidebar')
  })

  it('在 ready 态渲染 frontUI 三栏主壳并消费真实会话与消息数据', async () => {
    const settings: SettingRead[] = [
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
      { setting_key: 'profile.self_avatar_url', setting_value: AVATAR_PRESETS[0].url, is_secret: false },
      { setting_key: 'conversation.7.other_avatar_url', setting_value: AVATAR_PRESETS[3].url, is_secret: false },
    ]
    const conversations: ConversationRead[] = [
      {
        id: 7,
        title: '和小李的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '小李',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
    ]
    const messages: MessageRead[] = [
      {
        id: 11,
        sequence_no: 1,
        speaker_name: '小李',
        speaker_role: 'other',
        timestamp: '2026-04-08T10:01:00',
        content_text: '收到，稍后回你',
        message_type: 'text',
        resource_items: null,
      },
      {
        id: 12,
        sequence_no: 2,
        speaker_name: '我',
        speaker_role: 'self',
        timestamp: '2026-04-08T10:02:00',
        content_text: '那我们先这样吧',
        message_type: 'text',
        resource_items: null,
      },
    ]
    const completedJob: JobRead = {
      id: 19,
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      current_stage_percent: 100,
      current_stage_total_units: 1,
      current_stage_completed_units: 1,
      overall_total_units: 1,
      overall_completed_units: 1,
      status_message: null,
    }

    mockedReadSettings.mockResolvedValue(settings)
    mockedListConversations.mockResolvedValue(conversations)
    mockedListMessages.mockResolvedValue([...messages].reverse())
    mockedListConversationJobs.mockResolvedValue([completedJob])
    mockedReadJob.mockResolvedValue(completedJob)

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    expect(container.textContent).toContain('和小李的聊天')
    expect(container.textContent).toContain('收到，稍后回你')
    expect(container.textContent).toContain('那我们先这样吧')
    expect(container.textContent).toContain('发送(S)')
    expect(container.querySelector('.desktop-modal__panel--welcome')).toBeNull()
    expect(mockedListMessages).toHaveBeenCalledWith(7, { order: 'desc', limit: 80 })
    expect(mockedListConversationJobs).toHaveBeenCalledWith(7, 1)
    expect((container.querySelector('img[alt="当前用户头像"]') as HTMLImageElement | null)?.src).toBe(AVATAR_PRESETS[0].url)
    expect((container.querySelector('img[alt="和小李的聊天"]') as HTMLImageElement | null)?.src).toBe(AVATAR_PRESETS[3].url)

    const settingsButton = container.querySelector('button[aria-label="设置"]')
    expect(settingsButton).not.toBeNull()

    await act(async () => {
      if (settingsButton) {
        getReactProps<{ onClick?: () => void }>(settingsButton).onClick?.()
      }
    })
    await flushAsyncWork(2)

    expect(container.querySelector('.desktop-drawer')).not.toBeNull()
    expect(container.textContent).toContain('模型配置')
    expect(container.textContent).not.toContain('我的头像')

    const selfAvatarButton = container.querySelector('button[aria-label="打开头像设置"]')
    expect(selfAvatarButton).not.toBeNull()

    await act(async () => {
      if (selfAvatarButton) {
        getReactProps<{ onClick?: () => void }>(selfAvatarButton).onClick?.()
      }
    })
    await flushAsyncWork(2)

    expect(container.querySelector('.desktop-modal__panel')).not.toBeNull()
    expect(container.textContent).toContain('更换头像')
    expect(container.textContent).toContain('我的头像')
  })

  it('右键删除会话后会调用后端并从前端列表与消息区移除', async () => {
    const settings: SettingRead[] = [
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
    ]
    const conversations: ConversationRead[] = [
      {
        id: 7,
        title: '和小李的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '小李',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
      {
        id: 8,
        title: '和阿青的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '阿青',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
    ]
    const messagesByConversation = new Map<number, MessageRead[]>([
      [
        7,
        [
          {
            id: 11,
            sequence_no: 1,
            speaker_name: '小李',
            speaker_role: 'other',
            timestamp: '2026-04-08T10:01:00',
            content_text: '这是小李的消息',
            message_type: 'text',
            resource_items: null,
          },
        ],
      ],
      [
        8,
        [
          {
            id: 21,
            sequence_no: 1,
            speaker_name: '阿青',
            speaker_role: 'other',
            timestamp: '2026-04-08T11:01:00',
            content_text: '这是阿青的消息',
            message_type: 'text',
            resource_items: null,
          },
        ],
      ],
    ])

    mockedReadSettings.mockResolvedValue(settings)
    mockedListConversations.mockResolvedValue(conversations)
    mockedListMessages.mockImplementation(async (conversationId) => [...(messagesByConversation.get(conversationId) ?? [])].reverse())
    mockedListConversationJobs.mockResolvedValue([])
    mockedDeleteConversation.mockResolvedValue(undefined)

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    expect(container.textContent).toContain('和小李的聊天')
    expect(container.textContent).toContain('和阿青的聊天')
    expect(container.textContent).toContain('这是小李的消息')

    const xiaoliButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('和小李的聊天') ?? false,
    )
    expect(xiaoliButton).not.toBeUndefined()

    await act(async () => {
      if (xiaoliButton) {
        getReactProps<{
          onContextMenu?: (event: { preventDefault: () => void; clientX: number; clientY: number }) => void
        }>(xiaoliButton).onContextMenu?.({
          preventDefault: () => undefined,
          clientX: 120,
          clientY: 160,
        })
      }
    })
    await flushAsyncWork(2)

    const deleteButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('删除会话') ?? false,
    )
    expect(deleteButton).not.toBeUndefined()

    await act(async () => {
      if (deleteButton) {
        await getReactProps<{ onClick?: () => Promise<void> | void }>(deleteButton).onClick?.()
      }
    })
    await flushAsyncWork(6)

    expect(mockedDeleteConversation).toHaveBeenCalledWith(7)
    expect(container.textContent).not.toContain('和小李的聊天')
    expect(container.textContent).toContain('和阿青的聊天')
    expect(container.textContent).not.toContain('这是小李的消息')
    expect(container.textContent).toContain('这是阿青的消息')
  })

  it('聊天窗口首次只加载最近 80 条，并在滚动到顶部时继续加载更早 50 条消息', async () => {
    const recentMessages = Array.from({ length: 80 }, (_, index) => {
      const sequence = index + 21
      return {
        id: sequence,
        sequence_no: sequence,
        speaker_name: sequence % 2 === 0 ? '我' : '阿青',
        speaker_role: sequence % 2 === 0 ? 'self' : 'other',
        timestamp: `2026-04-08T10:${String(index).padStart(2, '0')}:00`,
        content_text: `最近消息 ${sequence}`,
        message_type: 'text',
        resource_items: null,
      } satisfies MessageRead
    }).reverse()
    const olderMessages = Array.from({ length: 20 }, (_, index) => {
      const sequence = 20 - index
      return {
        id: sequence,
        sequence_no: sequence,
        speaker_name: sequence % 2 === 0 ? '我' : '阿青',
        speaker_role: sequence % 2 === 0 ? 'self' : 'other',
        timestamp: `2026-04-08T09:${String(40 + index).padStart(2, '0')}:00`,
        content_text: `更早消息 ${sequence}`,
        message_type: 'text',
        resource_items: null,
      } satisfies MessageRead
    })

    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([
      {
        id: 7,
        title: '和阿青的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '阿青',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
    ])
    mockedListMessages.mockResolvedValueOnce(recentMessages).mockResolvedValueOnce(olderMessages)
    mockedListConversationJobs.mockResolvedValue([
      {
        id: 19,
        status: 'completed',
        current_stage: 'completed',
        progress_percent: 100,
        current_stage_percent: 100,
        current_stage_total_units: 1,
        current_stage_completed_units: 1,
        overall_total_units: 1,
        overall_completed_units: 1,
        status_message: null,
      },
    ])

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    expect(container.textContent).toContain('最近消息 100')
    expect(container.textContent).not.toContain('更早消息 1')
    expect(mockedListMessages).toHaveBeenNthCalledWith(1, 7, { order: 'desc', limit: 80 })

    const scrollContainer = container.querySelector('[data-testid="chat-message-scroll"]') as HTMLDivElement | null
    expect(scrollContainer).not.toBeNull()

    if (!scrollContainer) {
      throw new Error('expected chat message scroll container to render')
    }

    Object.defineProperty(scrollContainer, 'scrollHeight', {
      value: 1200,
      configurable: true,
    })
    Object.defineProperty(scrollContainer, 'clientHeight', {
      value: 600,
      configurable: true,
    })

    await act(async () => {
      scrollContainer.scrollTop = 0
      scrollContainer.dispatchEvent(new window.Event('scroll', { bubbles: true }))
    })
    await flushAsyncWork(8)

    expect(mockedListMessages).toHaveBeenNthCalledWith(2, 7, { before: 21, order: 'desc', limit: 50 })
    expect(container.textContent).toContain('更早消息 1')
  })

  it('在 ready 态把 WindowTitleBar 接入主壳，并用 bridge window state 驱动最大化按钮文案', async () => {
    const windowBridge = installReadyDesktopBridge({ initialIsMaximized: false, toggledIsMaximized: true })
    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    expect(container.querySelector('.desktop-titlebar')).not.toBeNull()
    expect(container.querySelector('button[aria-label="最小化窗口"]')).not.toBeNull()
    expect(container.querySelector('button[aria-label="关闭窗口"]')).not.toBeNull()
    expect(windowBridge.getState).toHaveBeenCalledTimes(1)

    const maximizeButton = container.querySelector('button[aria-label="最大化窗口"]')
    expect(maximizeButton).not.toBeNull()

    if (!maximizeButton) {
      throw new Error('expected maximize button to render')
    }

    await act(async () => {
      getReactProps<{ onClick?: () => void }>(maximizeButton).onClick?.()
    })
    await flushAsyncWork(4)

    expect(windowBridge.toggleMaximize).toHaveBeenCalledTimes(1)
    expect(container.querySelector('button[aria-label="还原窗口"]')).not.toBeNull()
  })

  it('只接受最新窗口状态请求结果，避免初始 getState 旧结果覆盖后续 toggleMaximize', async () => {
    const initialWindowState = createDeferred<{ isMaximized: boolean }>()
    const windowBridge = {
      getState: vi.fn(() => initialWindowState.promise),
      minimize: vi.fn(async () => undefined),
      toggleMaximize: vi.fn(async () => ({ isMaximized: true })),
      close: vi.fn(async () => undefined),
    }

    ;(globalThis as typeof globalThis & {
      desktop?: {
        getServiceState: () => Promise<{ phase: 'ready'; detail?: string }>
        pickImportFile: () => Promise<{ canceled: boolean; filePaths: string[] }>
        readImportFile: () => Promise<{ fileName: string; content: string }>
        getAppInfo: () => Promise<{ name: string; version: string }>
        window: typeof windowBridge
      }
    }).desktop = {
      getServiceState: async () => ({ phase: 'ready' }),
      pickImportFile: async () => ({ canceled: true, filePaths: [] }),
      readImportFile: async () => ({ fileName: 'chat.txt', content: '聊天记录' }),
      getAppInfo: async () => ({ name: 'if-then-desktop', version: '0.1.0' }),
      window: windowBridge,
    }

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    const maximizeButton = container.querySelector('button[aria-label="最大化窗口"]')
    expect(maximizeButton).not.toBeNull()

    if (!maximizeButton) {
      throw new Error('expected maximize button to render')
    }

    await act(async () => {
      getReactProps<{ onClick?: () => void }>(maximizeButton).onClick?.()
    })
    await flushAsyncWork(4)

    expect(windowBridge.toggleMaximize).toHaveBeenCalledTimes(1)
    expect(container.querySelector('button[aria-label="还原窗口"]')).not.toBeNull()

    await act(async () => {
      initialWindowState.resolve({ isMaximized: false })
    })
    await flushAsyncWork(4)

    expect(windowBridge.getState).toHaveBeenCalledTimes(1)
    expect(container.querySelector('button[aria-label="还原窗口"]')).not.toBeNull()
    expect(container.querySelector('button[aria-label="最大化窗口"]')).toBeNull()
  })

  it('把分析入口和内联改写推演流程挂回 frontUI 主壳', async () => {
    const settings: SettingRead[] = [
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
      { setting_key: 'simulation.default_mode', setting_value: 'short_thread', is_secret: false },
      { setting_key: 'simulation.default_turn_count', setting_value: '3', is_secret: false },
    ]
    const conversations: ConversationRead[] = [
      {
        id: 7,
        title: '和小李的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '小李',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
    ]
    const messages: MessageRead[] = [
      {
        id: 11,
        sequence_no: 1,
        speaker_name: '小李',
        speaker_role: 'other',
        timestamp: '2026-04-08T10:01:00',
        content_text: '收到，稍后回你',
        message_type: 'text',
        resource_items: null,
      },
      {
        id: 12,
        sequence_no: 2,
        speaker_name: '我',
        speaker_role: 'self',
        timestamp: '2026-04-08T10:02:00',
        content_text: '那我们先这样吧',
        message_type: 'text',
        resource_items: null,
      },
      {
        id: 13,
        sequence_no: 3,
        speaker_name: '小李',
        speaker_role: 'other',
        timestamp: '2026-04-08T10:03:00',
        content_text: '好，那晚点见。',
        message_type: 'text',
        resource_items: null,
      },
    ]
    const completedJob: JobRead = {
      id: 19,
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      current_stage_percent: 100,
      current_stage_total_units: 1,
      current_stage_completed_units: 1,
      overall_total_units: 1,
      overall_completed_units: 1,
      status_message: null,
    }

    mockedReadSettings.mockResolvedValue(settings)
    mockedListConversations.mockResolvedValue(conversations)
    mockedListMessages.mockResolvedValue([...messages].reverse())
    mockedListConversationJobs.mockResolvedValue([completedJob])
    mockedReadJob.mockResolvedValue(completedJob)
    const queuedSimulationJob = {
      id: 88,
      conversation_id: 7,
      target_message_id: 12,
      mode: 'short_thread',
      turn_count: 3,
      replacement_content: '我想先冷静一下，晚点继续聊可以吗？',
      status: 'queued',
      current_stage: 'queued',
      progress_percent: 0,
      current_stage_percent: 0,
      current_stage_total_units: 0,
      current_stage_completed_units: 0,
      overall_total_units: 0,
      overall_completed_units: 0,
      status_message: '等待 worker 处理',
      result_simulation_id: null,
      error_message: null,
    } as Awaited<ReturnType<typeof createSimulation>>
    const completedSimulationJob = {
      ...queuedSimulationJob,
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      current_stage_percent: 100,
      current_stage_total_units: 1,
      current_stage_completed_units: 1,
      overall_total_units: 1,
      overall_completed_units: 1,
      status_message: '推演完成',
      result_simulation_id: 188,
    }
    const finalSimulation = {
      id: 188,
      mode: 'short_thread',
      replacement_content: '我想先冷静一下，晚点继续聊可以吗？',
      first_reply_text: '好，那你先休息。',
      impact_summary: '冲突被降温。',
      simulated_turns: [
        {
          turn_index: 1,
          speaker_role: 'other',
          message_text: '好，那你先休息。',
          strategy_used: 'de-escalate',
          state_after_turn: {},
          generation_notes: null,
        },
        {
          turn_index: 2,
          speaker_role: 'self',
          message_text: '谢谢理解，我们晚点再聊。',
          strategy_used: 'repair',
          state_after_turn: {},
          generation_notes: null,
        },
      ],
    }
    const deferredSimulationJobs = createDeferred<Awaited<ReturnType<typeof listConversationSimulationJobs>>>()
    mockedCreateSimulation.mockResolvedValueOnce(queuedSimulationJob)
    mockedListConversationSimulationJobs.mockReturnValueOnce(deferredSimulationJobs.promise)
    mockedReadSimulation.mockResolvedValueOnce(finalSimulation)

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork()

    const allButtons = Array.from(container.querySelectorAll('button'))
    const analysisButtons = allButtons.filter((element) => element.textContent?.includes('分析') ?? false)

    // Should find the "分析" button in the header (not "开始分析")
    const inspectorButton = analysisButtons.find((btn) => btn.textContent === '分析')

    expect(inspectorButton).not.toBeUndefined()

    await act(async () => {
      if (inspectorButton) {
        getReactProps<{ onClick?: () => void }>(inspectorButton).onClick?.()
      }
    })
    await act(async () => {
      await flushAsyncWork(8)
    })

    const modalDialog = container.querySelector('[role="dialog"]')
    expect(modalDialog).not.toBeNull()
    expect(container.textContent).toContain('会话分析结果')
    expect(mockedListTopics).toHaveBeenCalledWith(7)

    const rewriteTarget = container.querySelector('[data-chat-message-id="message-12"] .cursor-pointer')
    expect(rewriteTarget).not.toBeNull()

    await act(async () => {
      if (rewriteTarget) {
        getReactProps<{ onDoubleClick?: () => void }>(rewriteTarget).onDoubleClick?.()
      }
    })
    await flushAsyncWork()

    const rewriteEditor = container.querySelector('textarea')
    expect(rewriteEditor).not.toBeNull()

    await act(async () => {
      if (rewriteEditor) {
        getReactProps<{
          onChange?: (event: { target: { value: string } }) => void
          onKeyDown?: (event: { key: string; shiftKey: boolean; preventDefault: () => void }) => void
        }>(rewriteEditor).onChange?.({
          target: { value: '我想先冷静一下，晚点继续聊可以吗？' },
        })
      }
    })
    await flushAsyncWork()

    expect(container.textContent).toContain('回车保存并推演')

    await act(async () => {
      if (rewriteEditor) {
        getReactProps<{
          onKeyDown?: (event: { key: string; shiftKey: boolean; preventDefault: () => void }) => void
        }>(rewriteEditor).onKeyDown?.({
          key: 'Enter',
          shiftKey: false,
          preventDefault: () => undefined,
        })
      }
    })
    await flushAsyncWork()

    expect(mockedCreateSimulation).toHaveBeenCalledTimes(1)
    expect(mockedCreateSimulation).toHaveBeenCalledWith({
      conversation_id: 7,
      target_message_id: 12,
      replacement_content: '我想先冷静一下，晚点继续聊可以吗？',
      mode: 'short_thread',
      turn_count: 3,
    })
    const pendingOverlay = container.querySelector('[data-testid="rewrite-pending-overlay"]')
    expect(pendingOverlay).not.toBeNull()
    expect(pendingOverlay?.className).toContain('absolute')
    expect(container.textContent).toContain('正在推演')
    expect(container.textContent).toContain('等待 worker 处理')
    expect(container.textContent).toContain('我想先冷静一下，晚点继续聊可以吗？')

    const ghostedMessage = container.querySelector('[data-chat-message-id="message-13"]')
    expect(ghostedMessage?.className).toContain('opacity-28')

    await act(async () => {
      deferredSimulationJobs.resolve([completedSimulationJob])
    })
    await flushAsyncWork(8)

    expect(container.textContent).toContain('正在查看推演结果')
    expect(container.textContent).toContain('原始历史已保留，可随时切回')
    expect(container.textContent).toContain('我想先冷静一下，晚点继续聊可以吗？')
    expect(container.textContent).toContain('好')
    expect(container.textContent).toContain('那你先休息')
    expect(container.textContent).toContain('谢谢理解')
    expect(container.textContent).toContain('我们晚点再聊')
    expect(container.textContent).not.toContain('好，那晚点见。')
    expect(container.querySelector('[data-chat-message-id="message-13"]')).toBeNull()
    expect(container.querySelectorAll('[data-chat-message-id^="simulation-188-"]').length).toBe(4)
    expect(container.querySelector('.rewrite-result-enter')).not.toBeNull()
    expect(container.querySelector('[data-testid="rewrite-completion-flash"]')).not.toBeNull()

    const resetButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('返回原始历史') ?? false,
    )
    expect(resetButton).not.toBeUndefined()

    await act(async () => {
      if (resetButton) {
        getReactProps<{ onClick?: () => void }>(resetButton).onClick?.()
      }
    })
    await flushAsyncWork(6)

    expect(container.textContent).not.toContain('正在查看推演结果')
    expect(container.textContent).toContain('那我们先这样吧')
    expect(container.textContent).not.toContain('我想先冷静一下，晚点继续聊可以吗？')
    expect(container.textContent).not.toContain('谢谢理解，我们晚点再聊。')
    expect(container.textContent).toContain('发送(S)')
  })

  it('推演完成后可直接进入继续改写状态', async () => {
    const settings: SettingRead[] = [
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
      { setting_key: 'simulation.default_mode', setting_value: 'single_reply', is_secret: false },
      { setting_key: 'simulation.default_turn_count', setting_value: '1', is_secret: false },
    ]
    const conversations: ConversationRead[] = [
      {
        id: 7,
        title: '和小李的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '小李',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
    ]
    const messages: MessageRead[] = [
      {
        id: 11,
        sequence_no: 1,
        speaker_name: '小李',
        speaker_role: 'other',
        timestamp: '2026-04-08T10:01:00',
        content_text: '收到，稍后回你',
        message_type: 'text',
        resource_items: null,
      },
      {
        id: 12,
        sequence_no: 2,
        speaker_name: '我',
        speaker_role: 'self',
        timestamp: '2026-04-08T10:02:00',
        content_text: '那我们先这样吧',
        message_type: 'text',
        resource_items: null,
      },
    ]
    const completedJob: JobRead = {
      id: 19,
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      current_stage_percent: 100,
      current_stage_total_units: 1,
      current_stage_completed_units: 1,
      overall_total_units: 1,
      overall_completed_units: 1,
      status_message: null,
    }

    mockedReadSettings.mockResolvedValue(settings)
    mockedListConversations.mockResolvedValue(conversations)
    mockedListMessages.mockResolvedValue([...messages].reverse())
    mockedListConversationJobs.mockResolvedValue([completedJob])
    mockedReadJob.mockResolvedValue(completedJob)
    const queuedSimulationJob = {
      id: 90,
      conversation_id: 7,
      target_message_id: 12,
      mode: 'single_reply',
      turn_count: 1,
      replacement_content: '我想先冷静一下，晚点继续聊可以吗？',
      status: 'queued',
      current_stage: 'queued',
      progress_percent: 0,
      current_stage_percent: 0,
      current_stage_total_units: 0,
      current_stage_completed_units: 0,
      overall_total_units: 0,
      overall_completed_units: 0,
      status_message: '等待 worker 处理',
      result_simulation_id: null,
      error_message: null,
    } as Awaited<ReturnType<typeof createSimulation>>
    const completedSimulationJob = {
      ...queuedSimulationJob,
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      current_stage_percent: 100,
      current_stage_total_units: 1,
      current_stage_completed_units: 1,
      overall_total_units: 1,
      overall_completed_units: 1,
      status_message: '推演完成',
      result_simulation_id: 190,
    }
    const finalSimulation = {
      id: 190,
      mode: 'single_reply',
      replacement_content: '我想先冷静一下，晚点继续聊可以吗？',
      first_reply_text: '好，那你先休息。',
      impact_summary: '冲突被降温。',
      simulated_turns: [],
    }
    const deferredSimulationJobs = createDeferred<Awaited<ReturnType<typeof listConversationSimulationJobs>>>()
    mockedCreateSimulation.mockResolvedValueOnce(queuedSimulationJob)
    mockedListConversationSimulationJobs.mockReturnValueOnce(deferredSimulationJobs.promise)
    mockedReadSimulation.mockResolvedValueOnce(finalSimulation)

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(10)

    const rewriteTarget = container.querySelector('[data-chat-message-id="message-12"] .cursor-pointer')
    expect(rewriteTarget).not.toBeNull()

    await act(async () => {
      if (rewriteTarget) {
        getReactProps<{ onDoubleClick?: () => void }>(rewriteTarget).onDoubleClick?.()
      }
    })
    await flushAsyncWork(4)

    const rewriteEditor = container.querySelector('textarea')
    expect(rewriteEditor).not.toBeNull()

    await act(async () => {
      if (rewriteEditor) {
        getReactProps<{
          onChange?: (event: { target: { value: string } }) => void
        }>(rewriteEditor).onChange?.({
          target: { value: '我想先冷静一下，晚点继续聊可以吗？' },
        })
      }
    })
    await flushAsyncWork(4)

    await act(async () => {
      if (rewriteEditor) {
        getReactProps<{
          onChange?: (event: { target: { value: string } }) => void
          onKeyDown?: (event: { key: string; shiftKey: boolean; preventDefault: () => void }) => void
        }>(rewriteEditor).onKeyDown?.({
          key: 'Enter',
          shiftKey: false,
          preventDefault: () => undefined,
        })
      }
    })
    await flushAsyncWork(8)

    expect(container.textContent).toContain('等待 worker 处理')

    await act(async () => {
      deferredSimulationJobs.resolve([completedSimulationJob])
    })
    await flushAsyncWork(8)

    const continueButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('继续改写') ?? false,
    )
    expect(continueButton).not.toBeUndefined()

    await act(async () => {
      if (continueButton) {
        getReactProps<{ onClick?: () => void }>(continueButton).onClick?.()
      }
    })
    await flushAsyncWork(6)

    const resumedEditor = container.querySelector('textarea') as HTMLTextAreaElement | null
    expect(resumedEditor).not.toBeNull()
    expect(resumedEditor?.value).toBe('我想先冷静一下，晚点继续聊可以吗？')
    expect(container.textContent).toContain('回车保存并推演')
    expect(container.textContent).toContain('我想先冷静一下，晚点继续聊可以吗？')
    expect(container.textContent).not.toContain('正在查看推演结果')
  })

  it('保存设置时会一并持久化默认推演模式和轮数', async () => {
    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
      { setting_key: 'llm.simulation_base_url', setting_value: 'https://simulation.example.test/v1', is_secret: false },
      { setting_key: 'llm.simulation_api_key', setting_value: 'simulation-secret', is_secret: true },
      { setting_key: 'simulation.default_mode', setting_value: 'single_reply', is_secret: false },
      { setting_key: 'simulation.default_turn_count', setting_value: '1', is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([])
    mockedWriteSetting.mockImplementation(async (payload) => payload)

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(8)

    const openSettingsButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('配置模型') ?? false,
    )
    expect(openSettingsButton).not.toBeUndefined()

    await act(async () => {
      if (openSettingsButton) {
        getReactProps<{ onClick?: () => void }>(openSettingsButton).onClick?.()
      }
    })
    await flushAsyncWork(4)

    const inputs = Array.from(container.querySelectorAll('.desktop-drawer__input'))
    const [
      baseUrlInput,
      apiKeyInput,
      chatModelInput,
      simulationBaseUrlInput,
      simulationApiKeyInput,
      simulationModelInput,
      simulationModeSelect,
      turnCountInput,
    ] = inputs as [
      HTMLInputElement,
      HTMLInputElement,
      HTMLInputElement,
      HTMLInputElement,
      HTMLInputElement,
      HTMLInputElement,
      HTMLSelectElement,
      HTMLInputElement,
    ]

    await act(async () => {
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(baseUrlInput).onChange?.({
        target: { value: 'https://api.example.dev/v1' },
      })
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(apiKeyInput).onChange?.({
        target: { value: 'next-secret' },
      })
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(chatModelInput).onChange?.({
        target: { value: 'gpt-5.4-mini' },
      })
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(simulationBaseUrlInput).onChange?.({
        target: { value: 'https://simulation.example.dev/v1' },
      })
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(simulationApiKeyInput).onChange?.({
        target: { value: 'simulation-next-secret' },
      })
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(simulationModelInput).onChange?.({
        target: { value: '' },
      })
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(simulationModeSelect).onChange?.({
        target: { value: 'short_thread' },
      })
      getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(turnCountInput).onChange?.({
        target: { value: '4' },
      })
    })
    await flushAsyncWork(2)

    const settingsForm = container.querySelector('.desktop-drawer__form')
    expect(settingsForm).not.toBeNull()

    await act(async () => {
      if (settingsForm) {
        await getReactProps<{
          onSubmit?: (event: { preventDefault: () => void }) => Promise<void> | void
        }>(settingsForm).onSubmit?.({
          preventDefault: () => undefined,
        })
      }
    })
    await flushAsyncWork(6)

    expect(mockedWriteSetting).toHaveBeenCalledTimes(9)
    expect(mockedWriteSetting).toHaveBeenCalledWith({
      setting_key: 'llm.simulation_base_url',
      setting_value: 'https://simulation.example.dev/v1',
      is_secret: false,
    })
    expect(mockedWriteSetting).toHaveBeenCalledWith({
      setting_key: 'llm.simulation_api_key',
      setting_value: 'simulation-next-secret',
      is_secret: true,
    })
    expect(mockedWriteSetting).toHaveBeenCalledWith({
      setting_key: 'simulation.default_mode',
      setting_value: 'short_thread',
      is_secret: false,
    })
    expect(mockedWriteSetting).toHaveBeenCalledWith({
      setting_key: 'simulation.default_turn_count',
      setting_value: '4',
      is_secret: false,
    })
    expect(mockedWriteSetting).toHaveBeenCalledWith({
      setting_key: 'llm.simulation_model',
      setting_value: '',
      is_secret: false,
    })
    expect(mockedWriteSetting).toHaveBeenCalledWith({
      setting_key: 'profile.self_avatar_url',
      setting_value: AVATAR_PRESETS[0].url,
      is_secret: false,
    })
  })

  it('点击设置右上角保存后会持久化配置并自动关闭抽屉', async () => {
    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
      { setting_key: 'llm.simulation_base_url', setting_value: '', is_secret: false },
      { setting_key: 'llm.simulation_api_key', setting_value: '', is_secret: true },
      { setting_key: 'simulation.default_mode', setting_value: 'single_reply', is_secret: false },
      { setting_key: 'simulation.default_turn_count', setting_value: '1', is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([])
    mockedWriteSetting.mockImplementation(async (payload) => payload)

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(8)

    const openSettingsButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('配置模型') ?? false,
    )
    expect(openSettingsButton).not.toBeUndefined()

    await act(async () => {
      if (openSettingsButton) {
        getReactProps<{ onClick?: () => void }>(openSettingsButton).onClick?.()
      }
    })
    await flushAsyncWork(4)

    const saveButton = Array.from(container.querySelectorAll('button')).find((element) => element.textContent === '保存')
    expect(saveButton).not.toBeUndefined()
    expect(Array.from(container.querySelectorAll('button')).some((element) => element.textContent === '关闭')).toBe(false)

    await act(async () => {
      if (saveButton) {
        await getReactProps<{ onClick?: () => Promise<void> | void }>(saveButton).onClick?.()
      }
    })
    await flushAsyncWork(6)

    expect(mockedWriteSetting).toHaveBeenCalledTimes(9)
    expect(container.querySelector('.desktop-drawer')).toBeNull()
  })

  it('在缺少模型配置或会话时仍保留欢迎引导流程', async () => {
    mockedReadSettings.mockResolvedValue([])
    mockedListConversations.mockResolvedValue([])

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork()

    expect(container.textContent).toContain('欢迎使用桌面壳层')
    expect(container.textContent).toContain('配置模型')
    expect(container.textContent).toContain('导入会话')
    expect(container.textContent).toContain('选择一段对话开始聊天')
  })

  it('首次欢迎流程支持选择并持久化自己的头像', async () => {
    mockedReadSettings.mockResolvedValue([])
    mockedListConversations.mockResolvedValue([])
    mockedWriteSetting.mockImplementation(async (payload) => payload)

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(8)

    const avatarPresetButton = container.querySelector('[data-testid="avatar-preset-avatar-preset-2"]')
    expect(avatarPresetButton).not.toBeNull()

    await act(async () => {
      if (avatarPresetButton) {
        getReactProps<{ onClick?: () => void }>(avatarPresetButton).onClick?.()
      }
    })
    await flushAsyncWork(2)

    const configureButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('配置模型') ?? false,
    )
    expect(configureButton).not.toBeUndefined()

    await act(async () => {
      if (configureButton) {
        await getReactProps<{ onClick?: () => Promise<void> | void }>(configureButton).onClick?.()
      }
    })
    await flushAsyncWork(4)

    expect(mockedWriteSetting).toHaveBeenCalledWith({
      setting_key: 'profile.self_avatar_url',
      setting_value: AVATAR_PRESETS[1].url,
      is_secret: false,
    })
  })

  it('点击左上角头像后可在独立弹窗里更换并持久化自己的头像', async () => {
    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
      { setting_key: 'profile.self_avatar_url', setting_value: AVATAR_PRESETS[0].url, is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([
      {
        id: 7,
        title: '和小李的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '小李',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
    ])
    mockedListMessages.mockResolvedValue([
      {
        id: 11,
        sequence_no: 1,
        speaker_name: '小李',
        speaker_role: 'other',
        timestamp: '2026-04-08T10:01:00',
        content_text: '收到，稍后回你',
        message_type: 'text',
        resource_items: null,
      },
    ])
    mockedListConversationJobs.mockResolvedValue([])
    mockedWriteSetting.mockImplementation(async (payload) => payload)

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(10)

    const selfAvatarButton = container.querySelector('button[aria-label="打开头像设置"]')
    expect(selfAvatarButton).not.toBeNull()

    await act(async () => {
      if (selfAvatarButton) {
        getReactProps<{ onClick?: () => void }>(selfAvatarButton).onClick?.()
      }
    })
    await flushAsyncWork(2)

    const avatarPresetButton = container.querySelector('[data-testid="avatar-preset-avatar-preset-4"]')
    expect(avatarPresetButton).not.toBeNull()

    await act(async () => {
      if (avatarPresetButton) {
        getReactProps<{ onClick?: () => void }>(avatarPresetButton).onClick?.()
      }
    })
    await flushAsyncWork(2)

    const saveButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('保存头像') ?? false,
    )
    expect(saveButton).not.toBeUndefined()

    await act(async () => {
      if (saveButton) {
        await getReactProps<{ onClick?: () => Promise<void> | void }>(saveButton).onClick?.()
      }
    })
    await flushAsyncWork(4)

    expect(mockedWriteSetting).toHaveBeenCalledWith({
      setting_key: 'profile.self_avatar_url',
      setting_value: AVATAR_PRESETS[3].url,
      is_secret: false,
    })
    expect(container.querySelector('.desktop-modal__panel')).toBeNull()
    expect((container.querySelector('img[alt="当前用户头像"]') as HTMLImageElement | null)?.src).toBe(AVATAR_PRESETS[3].url)
  })

  it('导入新会话后会在消息尚未落库时重试加载，直到聊天记录可渲染', async () => {
    vi.useFakeTimers()
    installReadyDesktopBridge({
      selectedImportPath: 'C:\\Users\\Tantless\\Desktop\\聊天记录.txt',
      importFileName: '聊天记录.txt',
      importFileContent: '第一行',
    })

    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([])
    mockedImportConversation.mockResolvedValue({
      conversation: {
        id: 99,
        title: '新导入的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '阿青',
        source_format: 'qq_export_v5',
        status: 'imported',
      },
      job: {
        id: 31,
        status: 'queued',
        current_stage: 'parsing',
        progress_percent: 0,
        current_stage_percent: 0,
        current_stage_total_units: 1000,
        current_stage_completed_units: 0,
        overall_total_units: 1059,
        overall_completed_units: 0,
        status_message: 'parsing 0/1000 messages',
      },
    })
    mockedListMessages
      .mockResolvedValueOnce([])
      .mockResolvedValueOnce([
        {
          id: 201,
          sequence_no: 1,
          speaker_name: '阿青',
          speaker_role: 'other',
          timestamp: '2026-04-09T02:03:00',
          content_text: '终于显示出来了',
          message_type: 'text',
          resource_items: null,
        },
      ])

    const { root, container } = setupDom()
    const scrollIntoViewSpy = vi.fn()
    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      value: scrollIntoViewSpy,
      configurable: true,
    })

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    const openImportButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('导入会话') ?? false,
    )
    expect(openImportButton).not.toBeUndefined()

    await act(async () => {
      if (openImportButton) {
        getReactProps<{ onClick?: () => void }>(openImportButton).onClick?.()
      }
    })
    await flushAsyncWork(4)

    const pathButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('选择文件') ?? false,
    )
    expect(pathButton).not.toBeUndefined()

    await act(async () => {
      if (pathButton) {
        getReactProps<{ onClick?: () => void }>(pathButton).onClick?.()
      }
    })
    await flushAsyncWork(4)
    expect(container.textContent).toContain('C:\\Users\\Tantless\\Desktop\\聊天记录.txt')

    const avatarPresetButton = container.querySelector('[data-testid="avatar-preset-avatar-preset-3"]')
    expect(avatarPresetButton).not.toBeNull()

    await act(async () => {
      if (avatarPresetButton) {
        getReactProps<{ onClick?: () => void }>(avatarPresetButton).onClick?.()
      }
    })
    await flushAsyncWork(2)

    const nameInput = container.querySelector('.desktop-modal__input') as HTMLInputElement | null
    expect(nameInput).not.toBeNull()

    await act(async () => {
      if (nameInput) {
        nameInput.value = '我'
        getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(nameInput).onChange?.({
          target: { value: '我' },
        })
      }
    })
    await flushAsyncWork(2)

    const importForm = container.querySelector('.desktop-modal__form') as HTMLFormElement | null
    expect(importForm).not.toBeNull()

    await act(async () => {
      if (importForm) {
        await getReactProps<{
          onSubmit?: (event: { preventDefault: () => void }) => Promise<void> | void
        }>(importForm).onSubmit?.({
          preventDefault: () => undefined,
        })
      }
    })
    await flushAsyncWork(8)

    expect(mockedImportConversation).toHaveBeenCalledTimes(1)
    expect(mockedImportConversation).toHaveBeenCalledWith(
      expect.objectContaining({
        autoAnalyze: false,
      }),
    )
    expect(mockedListMessages).toHaveBeenCalledTimes(1)
    expect(container.textContent).not.toContain('终于显示出来了')
    expect(Array.from(container.querySelectorAll('button')).some((element) => element.textContent === '分析')).toBe(false)
    expect(container.textContent).toContain('开始分析')
    expect(mockedWriteSetting).toHaveBeenCalledWith({
      setting_key: 'conversation.99.other_avatar_url',
      setting_value: AVATAR_PRESETS[2].url,
      is_secret: false,
    })

    await advanceTimersAndFlush(1500, 8)

    expect(mockedListMessages).toHaveBeenCalledTimes(2)
    expect(container.textContent).toContain('终于显示出来了')
    expect(scrollIntoViewSpy).toHaveBeenCalled()
    expect(scrollIntoViewSpy).toHaveBeenLastCalledWith({ behavior: 'auto' })
  })

  it('切换到导入并分析后会把 autoAnalyze=true 传给导入接口', async () => {
    installReadyDesktopBridge({
      selectedImportPath: 'C:\\Users\\Tantless\\Desktop\\聊天记录.txt',
      importFileName: '聊天记录.txt',
      importFileContent: '第一行',
    })

    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([])
    mockedImportConversation.mockResolvedValue({
      conversation: {
        id: 100,
        title: '导入并分析的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '阿青',
        source_format: 'qq_export_v5',
        status: 'queued',
      },
      job: {
        id: 32,
        status: 'queued',
        current_stage: 'created',
        progress_percent: 0,
        current_stage_percent: 0,
        current_stage_total_units: 0,
        current_stage_completed_units: 0,
        overall_total_units: 0,
        overall_completed_units: 0,
        status_message: 'queued',
      },
    })
    mockedListMessages.mockResolvedValue([])

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    const openImportButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('导入会话') ?? false,
    )
    expect(openImportButton).not.toBeUndefined()

    await act(async () => {
      if (openImportButton) {
        getReactProps<{ onClick?: () => void }>(openImportButton).onClick?.()
      }
    })
    await flushAsyncWork(4)

    const pathButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('选择文件') ?? false,
    )
    expect(pathButton).not.toBeUndefined()

    await act(async () => {
      if (pathButton) {
        getReactProps<{ onClick?: () => void }>(pathButton).onClick?.()
      }
    })
    await flushAsyncWork(4)

    const nameInput = container.querySelector('.desktop-modal__input') as HTMLInputElement | null
    expect(nameInput).not.toBeNull()

    await act(async () => {
      if (nameInput) {
        nameInput.value = '我'
        getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(nameInput).onChange?.({
          target: { value: '我' },
        })
      }
    })
    await flushAsyncWork(2)

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
    await flushAsyncWork(2)

    const importForm = container.querySelector('.desktop-modal__form') as HTMLFormElement | null
    expect(importForm).not.toBeNull()

    await act(async () => {
      if (importForm) {
        await getReactProps<{
          onSubmit?: (event: { preventDefault: () => void }) => Promise<void> | void
        }>(importForm).onSubmit?.({
          preventDefault: () => undefined,
        })
      }
    })
    await flushAsyncWork(8)

    expect(mockedImportConversation).toHaveBeenCalledWith(
      expect.objectContaining({
        autoAnalyze: true,
      }),
    )
  })

  it('导入后手动开始分析，完成后切换为已分析状态', async () => {
    vi.useFakeTimers()

    const importedConversation: ConversationRead = {
      id: 7,
      title: '和小李的聊天',
      chat_type: 'private',
      self_display_name: '我',
      other_display_name: '小李',
      source_format: 'qq_export_v5',
      status: 'imported',
    }
    const messages: MessageRead[] = [
      {
        id: 11,
        sequence_no: 1,
        speaker_name: '小李',
        speaker_role: 'other',
        timestamp: '2026-04-08T10:01:00',
        content_text: '收到，稍后回你',
        message_type: 'text',
        resource_items: null,
      },
      {
        id: 12,
        sequence_no: 2,
        speaker_name: '我',
        speaker_role: 'self',
        timestamp: '2026-04-08T10:02:00',
        content_text: '那我们先这样吧',
        message_type: 'text',
        resource_items: null,
      },
    ]
    const importOnlyJob: JobRead = {
      id: 31,
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      current_stage_percent: 100,
      current_stage_total_units: 6,
      current_stage_completed_units: 6,
      overall_total_units: 6,
      overall_completed_units: 6,
      status_message: 'imported 6 messages',
    }
    const queuedAnalysisJob: JobRead = {
      id: 32,
      status: 'queued',
      current_stage: 'created',
      progress_percent: 0,
      current_stage_percent: 0,
      current_stage_total_units: 0,
      current_stage_completed_units: 0,
      overall_total_units: 0,
      overall_completed_units: 0,
      status_message: 'queued',
    }
    const completedAnalysisJob: JobRead = {
      id: 32,
      status: 'completed',
      current_stage: 'completed',
      progress_percent: 100,
      current_stage_percent: 100,
      current_stage_total_units: 1,
      current_stage_completed_units: 1,
      overall_total_units: 1,
      overall_completed_units: 1,
      status_message: 'completed 1/1 units',
    }

    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([importedConversation])
    mockedListMessages.mockResolvedValue([...messages].reverse())
    mockedListConversationJobs.mockResolvedValue([importOnlyJob])
    mockedStartAnalysis.mockResolvedValue(queuedAnalysisJob)
    mockedReadJob.mockResolvedValue(completedAnalysisJob)

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    expect(Array.from(container.querySelectorAll('button')).some((element) => element.textContent === '分析')).toBe(false)

    const startAnalysisButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('开始分析') ?? false,
    )
    expect(startAnalysisButton).not.toBeUndefined()

    await act(async () => {
      if (startAnalysisButton) {
        getReactProps<{ onClick?: () => void }>(startAnalysisButton).onClick?.()
      }
    })
    await flushAsyncWork(4)

    expect(mockedStartAnalysis).toHaveBeenCalledWith(7)
    expect(Array.from(container.querySelectorAll('button')).some((element) => element.textContent?.includes('开始分析') ?? false)).toBe(false)

    await advanceTimersAndFlush(1500, 8)

    const analysisButton = Array.from(container.querySelectorAll('button')).find((element) => element.textContent === '分析')
    expect(analysisButton).not.toBeUndefined()
    expect(Array.from(container.querySelectorAll('button')).some((element) => element.textContent?.includes('开始分析') ?? false)).toBe(false)
  })

  it('聊天记录弹窗默认倒序加载，并在日期筛选后改为正序结果', async () => {
    const baseMessages: MessageRead[] = [
      {
        id: 101,
        sequence_no: 101,
        speaker_name: '阿青',
        speaker_role: 'other',
        timestamp: '2026-04-08T10:01:00',
        content_text: '最近消息 101',
        message_type: 'text',
        resource_items: null,
      },
      {
        id: 102,
        sequence_no: 102,
        speaker_name: '我',
        speaker_role: 'self',
        timestamp: '2026-04-08T10:02:00',
        content_text: '最近消息 102',
        message_type: 'text',
        resource_items: null,
      },
    ]
    const historyDefault: MessageRead[] = Array.from({ length: 20 }, (_, index) => {
      const sequence = 220 - index
      return {
        id: sequence,
        sequence_no: sequence,
        speaker_name: sequence % 2 === 0 ? '我' : '阿青',
        speaker_role: sequence % 2 === 0 ? 'self' : 'other',
        timestamp: `2026-04-08T${String(10 + Math.floor(index / 60)).padStart(2, '0')}:${String(index % 60).padStart(2, '0')}:00`,
        content_text: `默认结果 ${sequence}`,
        message_type: 'text',
        resource_items: null,
      } satisfies MessageRead
    })
    const historyFiltered: MessageRead[] = [
      {
        id: 31,
        sequence_no: 31,
        speaker_name: '阿青',
        speaker_role: 'other',
        timestamp: '2026-04-01T08:10:00',
        content_text: '4月1日清晨消息',
        message_type: 'text',
        resource_items: null,
      },
      {
        id: 35,
        sequence_no: 35,
        speaker_name: '我',
        speaker_role: 'self',
        timestamp: '2026-04-01T22:40:00',
        content_text: '4月1日晚间消息',
        message_type: 'text',
        resource_items: null,
      },
    ]
    const historyReset = [...historyDefault]

    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([
      {
        id: 7,
        title: '和阿青的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '阿青',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
    ])
    mockedListMessages
      .mockResolvedValueOnce([...baseMessages].reverse())
      .mockResolvedValueOnce(historyDefault)
      .mockResolvedValueOnce(historyFiltered)
      .mockResolvedValueOnce(historyReset)
    mockedListMessageDays.mockResolvedValue([
      { date: '2026-04-01', message_count: 2 },
      { date: '2026-04-03', message_count: 1 },
    ])
    mockedListConversationJobs.mockResolvedValue([
      {
        id: 19,
        status: 'completed',
        current_stage: 'completed',
        progress_percent: 100,
        current_stage_percent: 100,
        current_stage_total_units: 1,
        current_stage_completed_units: 1,
        overall_total_units: 1,
        overall_completed_units: 1,
        status_message: null,
      },
    ])

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    const historyButton = container.querySelector('button[aria-label="聊天记录"]')
    expect(historyButton).not.toBeNull()

    await act(async () => {
      if (historyButton) {
        getReactProps<{ onClick?: () => void }>(historyButton as Element).onClick?.()
      }
    })
    await flushAsyncWork(6)

    expect(container.textContent).toContain('聊天记录 - 阿青')
    expect(container.textContent).toContain('全部')
    expect(Array.from(container.querySelectorAll('button')).some((element) => element.textContent === '文件')).toBe(false)
    expect(Array.from(container.querySelectorAll('button')).some((element) => element.textContent === '日期')).toBe(false)
    expect(container.textContent).toContain('默认结果 220')
    expect(mockedListMessages).toHaveBeenNthCalledWith(2, 7, { order: 'desc', limit: 20 })
    expect(mockedListMessageDays).toHaveBeenCalledWith(7)

    const dateTrigger = container.querySelector('button[aria-label="打开聊天记录日期选择"]') as HTMLButtonElement | null
    expect(dateTrigger).not.toBeNull()

    await act(async () => {
      if (dateTrigger) {
        getReactProps<{ onClick?: () => void }>(dateTrigger).onClick?.()
      }
    })
    await flushAsyncWork(4)

    const unavailableDay = container.querySelector('[data-chat-history-date="2026-04-02"]') as HTMLButtonElement | null
    expect(unavailableDay).not.toBeNull()
    expect(unavailableDay?.disabled).toBe(true)
    const availableDay = container.querySelector('[data-chat-history-date="2026-04-01"]') as HTMLButtonElement | null
    expect(availableDay).not.toBeNull()
    expect(availableDay?.disabled).toBe(false)

    await act(async () => {
      if (availableDay) {
        getReactProps<{ onClick?: () => void }>(availableDay).onClick?.()
      }
    })
    await flushAsyncWork(8)

    expect(mockedListMessages).toHaveBeenNthCalledWith(3, 7, {
      order: 'asc',
      limit: 20,
      date: '2026-04-01',
    })
    expect(container.textContent).toContain('4月1日清晨消息')
    expect(container.textContent).toContain('4月1日晚间消息')

    const allTab = Array.from(container.querySelectorAll('button')).find((element) => element.textContent === '全部')
    expect(allTab).not.toBeUndefined()

    await act(async () => {
      if (allTab) {
        getReactProps<{ onClick?: () => void }>(allTab).onClick?.()
      }
    })
    await flushAsyncWork(8)

    expect(mockedListMessages).toHaveBeenNthCalledWith(4, 7, {
      order: 'desc',
      limit: 20,
    })
    expect(container.textContent).toContain('默认结果 220')
  })

  it('从聊天记录结果定位时会补齐更早消息并滚动到目标位置', async () => {
    const scrollTargets: string[] = []

    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([
      {
        id: 7,
        title: '和阿青的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '阿青',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
    ])
    mockedListConversationJobs.mockResolvedValue([
      {
        id: 19,
        status: 'completed',
        current_stage: 'completed',
        progress_percent: 100,
        current_stage_percent: 100,
        current_stage_total_units: 1,
        current_stage_completed_units: 1,
        overall_total_units: 1,
        overall_completed_units: 1,
        status_message: null,
      },
    ])
    mockedListMessageDays.mockResolvedValue([
      { date: '2026-04-07', message_count: 12 },
      { date: '2026-04-08', message_count: 80 },
    ])

    const recentMessages: MessageRead[] = Array.from({ length: 80 }, (_, index) => {
      const sequence = 120 - index
      return {
        id: sequence,
        sequence_no: sequence,
        speaker_name: sequence % 2 === 0 ? '我' : '阿青',
        speaker_role: sequence % 2 === 0 ? 'self' : 'other',
        timestamp: `2026-04-08T10:${String(index).padStart(2, '0')}:00`,
        content_text: `最近消息 ${sequence}`,
        message_type: 'text',
        resource_items: null,
      } satisfies MessageRead
    })
    const historyDefault: MessageRead[] = [
      {
        id: 120,
        sequence_no: 120,
        speaker_name: '我',
        speaker_role: 'self',
        timestamp: '2026-04-08T10:00:00',
        content_text: '默认结果 120',
        message_type: 'text',
        resource_items: null,
      },
    ]
    const locateTarget: MessageRead = {
      id: 10,
      sequence_no: 10,
      speaker_name: '我',
      speaker_role: 'self',
      timestamp: '2026-04-07T09:10:00',
      content_text: '需要定位的目标消息',
      message_type: 'text',
      resource_items: null,
    }
    const olderMessages: MessageRead[] = Array.from({ length: 40 }, (_, index) => {
      const sequence = 40 - index
      return {
        id: sequence,
        sequence_no: sequence,
        speaker_name: sequence % 2 === 0 ? '我' : '阿青',
        speaker_role: sequence % 2 === 0 ? 'self' : 'other',
        timestamp: `2026-04-07T09:${String(index).padStart(2, '0')}:00`,
        content_text: sequence === 10 ? '需要定位的目标消息' : `更早消息 ${sequence}`,
        message_type: 'text',
        resource_items: null,
      } satisfies MessageRead
    })

    mockedListMessages
      .mockResolvedValueOnce(recentMessages)
      .mockResolvedValueOnce(historyDefault)
      .mockResolvedValueOnce([locateTarget])
      .mockResolvedValueOnce(olderMessages)

    const { root, container } = setupDom()

    Object.defineProperty(window.HTMLElement.prototype, 'scrollIntoView', {
      value: function scrollIntoView() {
        scrollTargets.push(this.getAttribute?.('data-chat-message-id') ?? 'other')
      },
      configurable: true,
    })

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    const historyButton = container.querySelector('button[aria-label="聊天记录"]')
    expect(historyButton).not.toBeNull()

    await act(async () => {
      if (historyButton) {
        getReactProps<{ onClick?: () => void }>(historyButton as Element).onClick?.()
      }
    })
    await flushAsyncWork(6)

    const searchInput = container.querySelector('.chat-history-modal__search input') as HTMLInputElement | null
    expect(searchInput).not.toBeNull()

    await act(async () => {
      if (searchInput) {
        searchInput.value = '目标消息'
        getReactProps<{ onChange?: (event: { target: { value: string } }) => void }>(searchInput).onChange?.({
          target: { value: '目标消息' },
        })
      }
    })
    await flushAsyncWork(8)

    const locateButton = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('定位到此位置') ?? false,
    )
    expect(locateButton).not.toBeUndefined()

    await act(async () => {
      if (locateButton) {
        await getReactProps<{ onClick?: () => Promise<void> | void }>(locateButton).onClick?.()
      }
    })
    await flushAsyncWork(12)

    expect(
      mockedListMessages.mock.calls.some(
        (call) =>
          call[0] === 7 &&
          typeof call[1] === 'object' &&
          call[1] !== null &&
          'before' in call[1] &&
          'order' in call[1] &&
          'limit' in call[1] &&
          (call[1] as { order?: string }).order === 'desc' &&
          (call[1] as { limit?: number }).limit === 50,
      ),
    ).toBe(true)
    expect(container.textContent).toContain('需要定位的目标消息')
    expect(container.textContent).not.toContain('聊天记录 - 阿青')
    expect(scrollTargets).toContain('message-10')
  })

  it('snapshot 标签在历史视图下直接走后端最新快照，不依赖消息时间戳', async () => {
    mockedReadSettings.mockResolvedValue([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
      { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
      { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
    ])
    mockedListConversations.mockResolvedValue([
      {
        id: 7,
        title: '和小李的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '小李',
        source_format: 'qq_export_v5',
        status: 'ready',
      },
    ])
    mockedListMessages.mockResolvedValue([])
    mockedListConversationJobs.mockResolvedValue([
      {
        id: 19,
        status: 'completed',
        current_stage: 'completed',
        progress_percent: 100,
        current_stage_percent: 100,
        current_stage_total_units: 1,
        current_stage_completed_units: 1,
        overall_total_units: 1,
        overall_completed_units: 1,
        status_message: null,
      },
    ])

    const { root, container } = setupDom()

    await act(async () => {
      root.render(<App />)
    })
    await flushAsyncWork(12)

    const allButtons = Array.from(container.querySelectorAll('button'))
    const analysisButtons = allButtons.filter((element) => element.textContent?.includes('分析') ?? false)

    // Should find the "分析" button in the header (not "开始分析")
    const inspectorButton = analysisButtons.find((btn) => btn.textContent === '分析')
    expect(inspectorButton).not.toBeUndefined()

    await act(async () => {
      if (inspectorButton) {
        getReactProps<{ onClick?: () => void }>(inspectorButton).onClick?.()
      }
    })
    await act(async () => {
      await flushAsyncWork(8)
    })

    const snapshotTab = Array.from(container.querySelectorAll('button')).find(
      (element) => element.textContent?.includes('快照') ?? false,
    )
    expect(snapshotTab).not.toBeUndefined()

    await act(async () => {
      if (snapshotTab) {
        getReactProps<{ onClick?: () => void }>(snapshotTab).onClick?.()
      }
    })
    await act(async () => {
      await flushAsyncWork(8)
    })

    expect(mockedReadSnapshot).toHaveBeenCalledWith(7, undefined)
    expect(container.textContent).toContain('稳定')
  })
})
