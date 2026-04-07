import { describe, expect, it } from 'vitest'

import {
  decideAppShellState,
  hasModelSettings,
  resolveShellHydrationStatus,
} from '../src/lib/bootstrap'
import { normalizeDesktopFileSelection, shouldUseDesktopBridge } from '../src/lib/desktop'

describe('normalizeDesktopFileSelection', () => {
  it('turns a canceled selection into null', () => {
    expect(normalizeDesktopFileSelection({ canceled: true, filePaths: [] })).toBeNull()
  })
})

describe('shouldUseDesktopBridge', () => {
  it('requires the bridge for file picking only', () => {
    expect(shouldUseDesktopBridge('pick-import-file')).toBe(true)
    expect(shouldUseDesktopBridge('read-conversations')).toBe(false)
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
