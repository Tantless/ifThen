import { readFileSync } from 'node:fs'

import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { DesktopBridge, DesktopWindowState } from '../src/types/desktop'

const { exposeInMainWorld, invoke } = vi.hoisted(() => ({
  exposeInMainWorld: vi.fn(),
  invoke: vi.fn(),
}))

const preloadSource = readFileSync(new URL('../electron/preload.cts', import.meta.url), 'utf8')

function executePreload() {
  const loadModule = new Function('require', preloadSource)

  loadModule((moduleId: string) => {
    if (moduleId === 'electron') {
      return {
        contextBridge: {
          exposeInMainWorld,
        },
        ipcRenderer: {
          invoke,
        },
      }
    }

    throw new Error(`Unexpected preload dependency: ${moduleId}`)
  })
}

import {
  decideAppShellState,
  hasModelSettings,
  resolveShellHydrationStatus,
} from '../src/lib/bootstrap'
import {
  createImportFileBlob,
  normalizeDesktopFileSelection,
  pickAvatarFile,
  readImportFile,
  shouldUseDesktopBridge,
} from '../src/lib/desktop'

afterEach(() => {
  delete (globalThis as typeof globalThis & { desktop?: unknown }).desktop
})

describe('normalizeDesktopFileSelection', () => {
  it('turns a canceled selection into null', () => {
    expect(normalizeDesktopFileSelection({ canceled: true, filePaths: [] })).toBeNull()
  })
})

describe('shouldUseDesktopBridge', () => {
  it('requires the bridge for file picking only', () => {
    expect(shouldUseDesktopBridge('pick-import-file')).toBe(true)
    expect(shouldUseDesktopBridge('pick-avatar-file')).toBe(true)
    expect(shouldUseDesktopBridge('read-import-file')).toBe(true)
    expect(shouldUseDesktopBridge('read-conversations')).toBe(false)
  })
})

describe('createImportFileBlob', () => {
  it('builds a utf-8 text blob from imported desktop file content', async () => {
    const blob = createImportFileBlob({
      fileName: 'chat.txt',
      content: '第一行\\n第二行',
    })

    await expect(blob.text()).resolves.toBe('第一行\\n第二行')
    expect(blob.type).toBe('text/plain;charset=utf-8')
  })
})

describe('readImportFile', () => {
  it('returns null when the desktop bridge is unavailable', async () => {
    await expect(readImportFile()).resolves.toBeNull()
  })

  it('reads the pending import file payload from the desktop bridge', async () => {
    ;(globalThis as typeof globalThis & {
      desktop?: {
        readImportFile: () => Promise<{ fileName: string; content: string }>
      }
    }).desktop = {
      readImportFile: async () => ({ fileName: 'chat.txt', content: '第一行' }),
    }

    await expect(readImportFile()).resolves.toEqual({
      fileName: 'chat.txt',
      content: '第一行',
    })
  })
})

describe('pickAvatarFile', () => {
  it('returns null when the desktop bridge is unavailable', async () => {
    await expect(pickAvatarFile()).resolves.toBeNull()
  })

  it('reads the avatar payload from the desktop bridge', async () => {
    ;(globalThis as typeof globalThis & {
      desktop?: {
        pickAvatarFile: () => Promise<{ fileName: string; mimeType: string; dataUrl: string }>
      }
    }).desktop = {
      pickAvatarFile: async () => ({
        fileName: 'avatar.png',
        mimeType: 'image/png',
        dataUrl: 'data:image/png;base64,AAAB',
      }),
    }

    await expect(pickAvatarFile()).resolves.toEqual({
      fileName: 'avatar.png',
      mimeType: 'image/png',
      dataUrl: 'data:image/png;base64,AAAB',
    })
  })
})

describe('desktop preload bridge', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    executePreload()
  })

  it('exposes window controls on the desktop bridge', async () => {
    expect(exposeInMainWorld).toHaveBeenCalledTimes(1)
    expect(exposeInMainWorld).toHaveBeenCalledWith(
      'desktop',
      expect.objectContaining({
        window: expect.objectContaining({
          minimize: expect.any(Function),
          toggleMaximize: expect.any(Function),
          close: expect.any(Function),
          getState: expect.any(Function),
        }),
      }),
    )
  })

  it('routes desktop.window actions through the expected IPC channels', async () => {
    const bridge = exposeInMainWorld.mock.calls[0]?.[1]

    if (!bridge || typeof bridge !== 'object' || !('window' in bridge)) {
      throw new Error('expected preload to expose a desktop window bridge')
    }

    const windowBridge = (bridge as DesktopBridge).window
    invoke
      .mockResolvedValueOnce(undefined)
      .mockResolvedValueOnce({ isMaximized: true } satisfies DesktopWindowState)
      .mockResolvedValueOnce(undefined)
      .mockResolvedValueOnce({ isMaximized: false } satisfies DesktopWindowState)

    await windowBridge.minimize()
    await expect(windowBridge.toggleMaximize()).resolves.toEqual({ isMaximized: true })
    await windowBridge.close()
    await expect(windowBridge.getState()).resolves.toEqual({ isMaximized: false })

    expect(invoke).toHaveBeenNthCalledWith(1, 'desktop:window-minimize')
    expect(invoke).toHaveBeenNthCalledWith(2, 'desktop:window-toggle-maximize')
    expect(invoke).toHaveBeenNthCalledWith(3, 'desktop:window-close')
    expect(invoke).toHaveBeenNthCalledWith(4, 'desktop:window-get-state')
  })
})

describe('hasModelSettings', () => {
  it('requires base url, api key, and chat model settings', () => {
    expect(
      hasModelSettings([
        { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
        { setting_key: 'llm.api_key', setting_value: 'secret', is_secret: true },
      ]),
    ).toBe(false)
  })
})

describe('decideAppShellState', () => {
  it('opens welcome flow when settings or conversations are missing', () => {
    expect(decideAppShellState({ bootPhase: 'ready', settings: [], conversations: [] })).toMatchObject({
      ready: true,
      showWelcome: true,
    })
  })

  it('keeps showing boot UI until desktop services are ready', () => {
    expect(decideAppShellState({ bootPhase: 'starting-api', settings: [], conversations: [] })).toMatchObject({
      ready: false,
      showWelcome: false,
    })
  })
})

describe('resolveShellHydrationStatus', () => {
  it('stays loading until both settings and conversations are available', () => {
    expect(resolveShellHydrationStatus({ settings: null, conversations: [] })).toBe('loading')
  })

  it('surfaces fetch failure separately from empty successful data', () => {
    expect(resolveShellHydrationStatus({ settings: [], conversations: [], hasLoadError: true })).toBe('error')
  })
})
