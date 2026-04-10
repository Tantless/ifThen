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

  it('invalidates the selected import file after a successful read', async () => {
    registerDesktopIpc({
      getState: () => ({ phase: 'ready' }),
    } as any)

    const pickImportFile = handlers.get('desktop:pick-import-file')
    const readImportFile = handlers.get('desktop:read-import-file')

    expect(pickImportFile).toBeTypeOf('function')
    expect(readImportFile).toBeTypeOf('function')

    if (!pickImportFile || !readImportFile) {
      throw new Error('expected import IPC handlers to be registered')
    }

    await pickImportFile()

    await expect(readImportFile()).resolves.toEqual({
      fileName: 'chat.txt',
      content: '聊天记录内容',
    })
    await expect(readImportFile()).rejects.toThrow('No import file has been selected')
    expect(readFile).toHaveBeenCalledTimes(1)
  })

  it('registers window control handlers against the invoking window', async () => {
    registerDesktopIpc({
      getState: () => ({ phase: 'ready' }),
    } as any)

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
    } as any)

    const closeWindow = handlers.get('desktop:window-close')

    expect(closeWindow).toBeTypeOf('function')

    if (!closeWindow) {
      throw new Error('expected window close IPC handler to be registered')
    }

    expect(() => closeWindow(invokeEvent)).toThrow('No BrowserWindow found for desktop:window-close')
  })
})
