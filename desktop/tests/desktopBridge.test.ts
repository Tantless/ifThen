import { afterEach, describe, expect, it } from 'vitest'

import {
  decideAppShellState,
  hasModelSettings,
  resolveShellHydrationStatus,
} from '../src/lib/bootstrap'
import {
  createImportFileBlob,
  normalizeDesktopFileSelection,
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
