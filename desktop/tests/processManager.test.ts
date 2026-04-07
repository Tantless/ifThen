import path from 'node:path'
import { describe, expect, it } from 'vitest'

import { buildPythonLaunchSpec, resolveDesktopRepoRoot } from '../electron/backend/paths'
import { toManagedServiceState } from '../electron/backend/processManager'

describe('buildPythonLaunchSpec', () => {
  it('points to scripts/run_api.py from the repo root', () => {
    const spec = buildPythonLaunchSpec('api', 'D:/newProj')
    expect(spec.args.at(-1)).toBe('scripts/run_api.py')
  })
})

describe('resolveDesktopRepoRoot', () => {
  it('resolves the repo root from the source electron entrypoint', () => {
    expect(resolveDesktopRepoRoot('D:/newProj/desktop/electron/main.ts')).toBe(path.normalize('D:/newProj'))
  })

  it('resolves the repo root from the built electron entrypoint', () => {
    expect(resolveDesktopRepoRoot('D:/newProj/desktop/dist-electron/electron/main.js')).toBe(
      path.normalize('D:/newProj'),
    )
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

  it('treats a running worker as ready once api health has passed', () => {
    expect(
      toManagedServiceState({
        api: { running: true, healthy: true },
        worker: { running: true, healthy: false },
      }),
    ).toMatchObject({ phase: 'ready' })
  })

  it('keeps api healthy and stopped worker in starting-worker', () => {
    expect(
      toManagedServiceState({
        api: { running: true, healthy: true },
        worker: { running: false, healthy: false },
      }),
    ).toMatchObject({ phase: 'starting-worker' })
  })

  it('surfaces worker failures instead of stale api success details', () => {
    expect(
      toManagedServiceState({
        api: { running: true, healthy: true, detail: 'api healthcheck passed' },
        worker: { running: false, healthy: false, detail: 'worker exited unexpectedly (code 1)' },
      }),
    ).toMatchObject({
      phase: 'error',
      detail: 'worker exited unexpectedly (code 1)',
    })
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
