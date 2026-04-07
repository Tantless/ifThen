import { spawn, type ChildProcess } from 'node:child_process'
import type { BackendLaunchSpec, ManagedServiceState, ServiceState } from './contracts'

export function toManagedServiceState(input: {
  api: ServiceState
  worker: ServiceState
}): ManagedServiceState {
  if ((!input.api.running && input.api.detail) || (!input.worker.running && input.worker.detail)) {
    return {
      phase: 'error',
      api: input.api,
      worker: input.worker,
      detail: input.api.detail ?? input.worker.detail,
    }
  }

  if (input.api.running && input.api.healthy && input.worker.running && input.worker.healthy) {
    return {
      phase: 'ready',
      api: input.api,
      worker: input.worker,
      detail: input.worker.detail ?? input.api.detail,
    }
  }

  if (input.api.running && !input.api.healthy) {
    return {
      phase: 'waiting-api',
      api: input.api,
      worker: input.worker,
      detail: input.api.detail ?? 'waiting for /health',
    }
  }

  if (input.api.running && input.api.healthy && (!input.worker.running || !input.worker.healthy)) {
    return {
      phase: 'starting-worker',
      api: input.api,
      worker: input.worker,
      detail: input.worker.detail ?? input.api.detail,
    }
  }

  return {
    phase: 'starting-api',
    api: input.api,
    worker: input.worker,
    detail: input.api.detail ?? input.worker.detail,
  }
}

export class BackendProcessManager {
  private apiProcess: ChildProcess | null = null
  private workerProcess: ChildProcess | null = null

  private apiState: ServiceState = { running: false, healthy: false }
  private workerState: ServiceState = { running: false, healthy: false }

  private attachLifecycleListeners(
    processRef: ChildProcess,
    updateState: (state: ServiceState) => void,
    clearProcess: () => void,
  ) {
    processRef.once('error', (error) => {
      updateState({
        running: false,
        healthy: false,
        detail: error.message,
      })
      clearProcess()
    })

    processRef.once('exit', (code, signal) => {
      updateState({
        running: false,
        healthy: false,
        detail:
          code === 0 || signal === 'SIGTERM'
            ? undefined
            : `process exited unexpectedly${code !== null ? ` (code ${code})` : ''}`,
      })
      clearProcess()
    })
  }

  startApi(spec: BackendLaunchSpec) {
    this.apiProcess = spawn(spec.command, spec.args, {
      cwd: spec.cwd,
      env: spec.env,
      stdio: 'pipe',
    })

    this.apiState = {
      running: true,
      healthy: false,
      pid: this.apiProcess.pid,
      detail: 'starting python api',
    }
    this.attachLifecycleListeners(
      this.apiProcess,
      (state) => {
        this.apiState = state
      },
      () => {
        this.apiProcess = null
      },
    )

    return this.apiProcess
  }

  startWorker(spec: BackendLaunchSpec) {
    this.workerProcess = spawn(spec.command, spec.args, {
      cwd: spec.cwd,
      env: spec.env,
      stdio: 'pipe',
    })

    this.workerState = {
      running: true,
      healthy: false,
      pid: this.workerProcess.pid,
      detail: 'starting python worker',
    }
    this.attachLifecycleListeners(
      this.workerProcess,
      (state) => {
        this.workerState = state
      },
      () => {
        this.workerProcess = null
      },
    )

    return this.workerProcess
  }

  markApiHealthy(healthy: boolean, detail?: string) {
    this.apiState = {
      ...this.apiState,
      running: this.apiProcess !== null,
      healthy,
      detail,
    }
  }

  markWorkerHealthy(healthy: boolean, detail?: string) {
    this.workerState = {
      ...this.workerState,
      running: this.workerProcess !== null,
      healthy,
      detail,
    }
  }

  getState(): ManagedServiceState {
    return toManagedServiceState({ api: this.apiState, worker: this.workerState })
  }

  stopAll() {
    this.apiProcess?.kill()
    this.workerProcess?.kill()
    this.apiProcess = null
    this.workerProcess = null
    this.apiState = { running: false, healthy: false }
    this.workerState = { running: false, healthy: false }
  }
}
