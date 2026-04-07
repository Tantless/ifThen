import { describe, expect, it } from 'vitest'

import { toManagedServiceState } from '../electron/backend/processManager'

describe('toManagedServiceState', () => {
  it('marks both processes healthy as ready', () => {
    expect(
      toManagedServiceState({
        api: { running: true, healthy: true },
        worker: { running: true, healthy: true },
      }),
    ).toMatchObject({ phase: 'ready' })
  })
})
