import { afterEach, describe, expect, it } from 'vitest'
import { getBootLabel, normalizeDesktopState, readDesktopServiceState } from '../src/lib/desktop'

afterEach(() => {
  delete (globalThis as typeof globalThis & { desktop?: unknown }).desktop
})

describe('getBootLabel', () => {
  it('maps waiting-api state to a user-facing label', () => {
    expect(getBootLabel({ phase: 'waiting-api', detail: 'polling /health' })).toBe('正在启动本地分析服务…')
  })
})

describe('normalizeDesktopState', () => {
  it('turns ipc ready payload into renderer-ready state', () => {
    const state = normalizeDesktopState({ phase: 'ready', detail: 'api healthy' })
    expect(getBootLabel(state)).toBe('服务已就绪')
  })
})

describe('readDesktopServiceState', () => {
  it('falls back to booting when desktop bridge is unavailable', async () => {
    await expect(readDesktopServiceState()).resolves.toMatchObject({
      phase: 'booting',
      detail: 'desktop bridge unavailable',
    })
  })

  it('reads the minimal service-state payload from the desktop bridge', async () => {
    ;(globalThis as typeof globalThis & {
      desktop?: { getServiceState: () => Promise<{ phase: 'ready'; detail: string }> }
    }).desktop = {
      getServiceState: async () => ({ phase: 'ready', detail: 'api healthy' }),
    }

    await expect(readDesktopServiceState()).resolves.toMatchObject({
      phase: 'ready',
      detail: 'api healthy',
    })
  })
})
