import { describe, expect, it } from 'vitest'
import { getBootLabel } from '../src/lib/desktop'

describe('getBootLabel', () => {
  it('maps waiting-api state to a user-facing label', () => {
    expect(getBootLabel({ phase: 'waiting-api', detail: 'polling /health' })).toBe('正在启动本地分析服务…')
  })
})
