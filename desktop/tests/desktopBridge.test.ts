import { describe, expect, it } from 'vitest'

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
