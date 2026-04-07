import { describe, expect, it } from 'vitest'

import { buildPythonLaunchSpec } from '../electron/backend/paths'
import { toManagedServiceState } from '../electron/backend/processManager'

describe('buildPythonLaunchSpec', () => {
  it('points to scripts/run_api.py from the repo root', () => {
    const spec = buildPythonLaunchSpec('api', 'D:/newProj')
    expect(spec.args.at(-1)).toBe('scripts/run_api.py')
  })
})

describe('toManagedServiceState', () => {
  it('marks both processes healthy as ready', () => {
    expect(
      toManagedServiceState({
        api: { running: true, healthy: true },
        worker: { running: true, healthy: true },
      }),
    ).toMatchObject({ phase: 'ready' })
  })

  it('marks api healthy and worker booting as starting-worker', () => {
    expect(
      toManagedServiceState({
        api: { running: true, healthy: true },
        worker: { running: true, healthy: false },
      }),
    ).toMatchObject({ phase: 'starting-worker' })
  })

  it('marks everything stopped as starting-api', () => {
    expect(
      toManagedServiceState({
        api: { running: false, healthy: false },
        worker: { running: false, healthy: false },
      }),
    ).toMatchObject({ phase: 'starting-api' })
  })
})
