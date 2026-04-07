import { beforeEach, describe, expect, it, vi } from 'vitest'

const { handlers, showOpenDialog, readFile } = vi.hoisted(() => ({
  handlers: new Map<string, (...args: unknown[]) => unknown>(),
  showOpenDialog: vi.fn(),
  readFile: vi.fn(),
}))

vi.mock('electron', () => ({
  app: {
    getName: vi.fn(() => 'if-then-desktop'),
    getVersion: vi.fn(() => '0.1.0'),
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
  beforeEach(() => {
    handlers.clear()
    vi.clearAllMocks()
    showOpenDialog.mockResolvedValue({
      canceled: false,
      filePaths: ['C:/exports/chat.txt'],
    })
    readFile.mockResolvedValue('聊天记录内容')
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
})
