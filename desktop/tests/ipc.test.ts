import type { IpcMainInvokeEvent } from 'electron'

import { beforeEach, describe, expect, it, vi } from 'vitest'

const { handlers, showOpenDialog, readFile, fromWebContents, sender, invokingWindow } = vi.hoisted(() => ({
  handlers: new Map<string, (...args: unknown[]) => unknown>(),
  showOpenDialog: vi.fn(),
  readFile: vi.fn(),
  fromWebContents: vi.fn(),
  sender: {},
  invokingWindow: {
    minimize: vi.fn(),
    maximize: vi.fn(),
    unmaximize: vi.fn(),
    close: vi.fn(),
    isMaximized: vi.fn(() => false),
  },
}))

vi.mock('electron', () => ({
  app: {
    getName: vi.fn(() => 'if-then-desktop'),
    getVersion: vi.fn(() => '0.1.0'),
  },
  BrowserWindow: {
    fromWebContents,
  },
  dialog: {
    showOpenDialog,
  },
  ipcMain: {
    handle: vi.fn((channel: string, handler: (...args: unknown[]) => unknown) => {
      handlers.set(channel, handler)
    }),
  },
}))

vi.mock('node:fs/promises', () => ({
  readFile,
}))

import { registerDesktopIpc } from '../electron/ipc'

describe('registerDesktopIpc', () => {
  const invokeEvent = { sender } as IpcMainInvokeEvent

  beforeEach(() => {
    handlers.clear()
    vi.clearAllMocks()
    showOpenDialog.mockResolvedValue({
      canceled: false,
      filePaths: ['C:/exports/chat.txt'],
    })
    readFile.mockResolvedValue('聊天记录内容')
    invokingWindow.isMaximized.mockReturnValue(false)
    fromWebContents.mockReturnValue(invokingWindow)
  })

  it('returns a data-url avatar payload after selecting an image file', async () => {
    showOpenDialog.mockResolvedValueOnce({
      canceled: false,
      filePaths: ['C:/avatars/avatar.png'],
    })
    readFile.mockResolvedValueOnce(Uint8Array.from([137, 80, 78, 71]))

    registerDesktopIpc({
      getState: () => ({ phase: 'ready' }),
    } as any, {} as any)

    const pickAvatarFile = handlers.get('desktop:pick-avatar-file')
    expect(pickAvatarFile).toBeTypeOf('function')

    if (!pickAvatarFile) {
      throw new Error('expected avatar IPC handler to be registered')
    }

    await expect(pickAvatarFile()).resolves.toEqual({
      fileName: 'avatar.png',
      mimeType: 'image/png',
      dataUrl: 'data:image/png;base64,iVBORw==',
    })
  })

  it('registers window control handlers against the invoking window', async () => {
    registerDesktopIpc({
      getState: () => ({ phase: 'ready' }),
    } as any, {} as any)

    const minimizeWindow = handlers.get('desktop:window-minimize')
    const toggleMaximizeWindow = handlers.get('desktop:window-toggle-maximize')
    const closeWindow = handlers.get('desktop:window-close')
    const getWindowState = handlers.get('desktop:window-get-state')

    expect(minimizeWindow).toBeTypeOf('function')
    expect(toggleMaximizeWindow).toBeTypeOf('function')
    expect(closeWindow).toBeTypeOf('function')
    expect(getWindowState).toBeTypeOf('function')

    if (!minimizeWindow || !toggleMaximizeWindow || !closeWindow || !getWindowState) {
      throw new Error('expected window IPC handlers to be registered')
    }

    expect(() => minimizeWindow(invokeEvent)).not.toThrow()
    expect(fromWebContents).toHaveBeenNthCalledWith(1, sender)
    expect(invokingWindow.minimize).toHaveBeenCalledTimes(1)

    expect(toggleMaximizeWindow(invokeEvent)).toEqual({
      isMaximized: true,
    })
    expect(fromWebContents).toHaveBeenNthCalledWith(2, sender)
    expect(invokingWindow.maximize).toHaveBeenCalledTimes(1)
    expect(invokingWindow.unmaximize).not.toHaveBeenCalled()

    invokingWindow.isMaximized.mockReturnValue(true)
    expect(toggleMaximizeWindow(invokeEvent)).toEqual({
      isMaximized: false,
    })
    expect(fromWebContents).toHaveBeenNthCalledWith(3, sender)
    expect(invokingWindow.unmaximize).toHaveBeenCalledTimes(1)

    expect(() => closeWindow(invokeEvent)).not.toThrow()
    expect(fromWebContents).toHaveBeenNthCalledWith(4, sender)
    expect(invokingWindow.close).toHaveBeenCalledTimes(1)

    expect(getWindowState(invokeEvent)).toEqual({
      isMaximized: true,
    })
    expect(fromWebContents).toHaveBeenNthCalledWith(5, sender)
  })

  it('throws a clear error when a window control handler runs without an invoking window', async () => {
    fromWebContents.mockReturnValue(null)

    registerDesktopIpc({
      getState: () => ({ phase: 'ready' }),
    } as any, {} as any)

    const closeWindow = handlers.get('desktop:window-close')

    expect(closeWindow).toBeTypeOf('function')

    if (!closeWindow) {
      throw new Error('expected window close IPC handler to be registered')
    }

    expect(() => closeWindow(invokeEvent)).toThrow('No BrowserWindow found for desktop:window-close')
  })

  it('proxies settings reads through the backend client facade', async () => {
    const readSettings = vi.fn(async () => [
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
    ])

    registerDesktopIpc({
      getState: () => ({ phase: 'ready' }),
    } as any, {
      readSettings,
    } as any)

    const readSettingsHandler = handlers.get('desktop:settings-read')
    expect(readSettingsHandler).toBeTypeOf('function')

    if (!readSettingsHandler) {
      throw new Error('expected desktop settings read handler to be registered')
    }

    await expect(readSettingsHandler()).resolves.toEqual([
      { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
    ])
    expect(readSettings).toHaveBeenCalledTimes(1)
  })

  it('imports conversations through the backend client after a file has been selected', async () => {
    const importConversation = vi.fn(async () => ({
      conversation: {
        id: 7,
        title: '和阿青的聊天',
        chat_type: 'private',
        self_display_name: '我',
        other_display_name: '阿青',
        source_format: 'qq_export_v5',
        status: 'queued',
      },
      job: {
        id: 31,
        status: 'queued',
        current_stage: 'parsing',
        progress_percent: 0,
        current_stage_percent: 0,
        current_stage_total_units: 0,
        current_stage_completed_units: 0,
        overall_total_units: 0,
        overall_completed_units: 0,
        status_message: 'parsing 0/0 messages',
      },
    }))

    registerDesktopIpc({
      getState: () => ({ phase: 'ready' }),
    } as any, {
      importConversation,
    } as any)

    const pickImportFile = handlers.get('desktop:pick-import-file')
    const importHandler = handlers.get('desktop:conversations-import')

    expect(pickImportFile).toBeTypeOf('function')
    expect(importHandler).toBeTypeOf('function')

    if (!pickImportFile || !importHandler) {
      throw new Error('expected import handlers to be registered')
    }

    await pickImportFile()

    await expect(importHandler(invokeEvent, { selfDisplayName: '我', autoAnalyze: true })).resolves.toMatchObject({
      conversation: {
        id: 7,
      },
    })
    expect(importConversation).toHaveBeenCalledWith({
      filePath: 'C:/exports/chat.txt',
      selfDisplayName: '我',
      autoAnalyze: true,
    })
  })

  it('proxies message context reads through the backend client facade', async () => {
    const readMessageContext = vi.fn(async () => ({
      target: { id: 12 },
      before: [],
      after: [],
    }))

    registerDesktopIpc({
      getState: () => ({ phase: 'ready' }),
    } as any, {
      readMessageContext,
    } as any)

    const readMessageContextHandler = handlers.get('desktop:conversations-read-message-context')
    expect(readMessageContextHandler).toBeTypeOf('function')

    if (!readMessageContextHandler) {
      throw new Error('expected message context IPC handler to be registered')
    }

    await expect(readMessageContextHandler(invokeEvent, { messageId: 12, radius: 30 })).resolves.toEqual({
      target: { id: 12 },
      before: [],
      after: [],
    })
    expect(readMessageContext).toHaveBeenCalledWith({ messageId: 12, radius: 30 })
  })
})
