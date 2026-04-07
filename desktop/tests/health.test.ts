import { describe, expect, it } from 'vitest'
import { getBootLabel, normalizeDesktopState } from '../src/lib/desktop'

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
