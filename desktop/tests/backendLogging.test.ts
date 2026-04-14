import { EventEmitter } from 'node:events'
import path from 'node:path'

import { beforeEach, describe, expect, it, vi } from 'vitest'

const { appendFileSync, mkdirSync, spawn } = vi.hoisted(() => ({
  appendFileSync: vi.fn(),
  mkdirSync: vi.fn(),
  spawn: vi.fn(),
}))

vi.mock('node:child_process', () => ({
  spawn,
}))

vi.mock('node:fs', () => ({
  appendFileSync,
  mkdirSync,
}))

import { BackendProcessManager } from '../electron/backend/processManager'

class FakeChildProcess extends EventEmitter {
  pid = 321
  stdout = new EventEmitter()
  stderr = new EventEmitter()
  kill = vi.fn()
}

describe('BackendProcessManager logging', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('writes child stdout and stderr into a service log file when a log directory is configured', () => {
    const child = new FakeChildProcess()
    spawn.mockReturnValue(child)

    const manager = new BackendProcessManager('C:/Users/test/AppData/Roaming/if-then-desktop/data/logs')
    manager.startApi({
      command: 'python',
      args: ['scripts/run_api.py'],
      cwd: 'D:/newProj',
    })

    child.stdout.emit('data', Buffer.from('api booted\n'))
    child.stderr.emit('data', Buffer.from('api warning\n'))

    expect(mkdirSync).toHaveBeenCalledWith(
      path.normalize('C:/Users/test/AppData/Roaming/if-then-desktop/data/logs'),
      { recursive: true },
    )
    expect(appendFileSync).toHaveBeenCalledWith(
      path.normalize('C:/Users/test/AppData/Roaming/if-then-desktop/data/logs/api.log'),
      expect.stringContaining('api booted'),
      'utf8',
    )
    expect(appendFileSync).toHaveBeenCalledWith(
      path.normalize('C:/Users/test/AppData/Roaming/if-then-desktop/data/logs/api.log'),
      expect.stringContaining('api warning'),
      'utf8',
    )
  })
})
