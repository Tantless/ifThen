import { spawn, type ChildProcess } from 'node:child_process'
import type { BackendLaunchSpec, ManagedServiceState, ServiceState } from './contracts'

export function toManagedServiceState(input: {
  api: ServiceState
  worker: ServiceState
}): ManagedServiceState {
  if (input.api.running && input.api.healthy && input.worker.running && input.worker.healthy) {
    return { phase: 'ready', api: input.api, worker: input.worker }
  }

  if (input.api.running && !input.api.healthy) {
    return {
      phase: 'waiting-api',
      api: input.api,
      worker: input.worker,
      detail: 'waiting for /health',
    }
  }

  if (input.api.running && input.api.healthy && (!input.worker.running || !input.worker.healthy)) {
    return { phase: 'starting-worker', api: input.api, worker: input.worker }
  }

  return { phase: 'starting-api', api: input.api, worker: input.worker }
}

export class BackendProcessManager {
  private apiProcess: ChildProcess | null = null
  private workerProcess: ChildProcess | null = null

  private apiState: ServiceState = { running: false, healthy: false }
  private workerState: ServiceState = { running: false, healthy: false }

  startApi(spec: BackendLaunchSpec) {
    this.apiProcess = spawn(spec.command, spec.args, {
      cwd: spec.cwd,
      env: spec.env,
      stdio: 'pipe',
    })

    this.apiState = { running: true, healthy: false, pid: this.apiProcess.pid }
    this.apiProcess.once('exit', () => {
      this.apiState = { running: false, healthy: false }
      this.apiProcess = null
    })

    return this.apiProcess
  }

  startWorker(spec: BackendLaunchSpec) {
    this.workerProcess = spawn(spec.command, spec.args, {
      cwd: spec.cwd,
      env: spec.env,
      stdio: 'pipe',
    })

    this.workerState = { running: true, healthy: false, pid: this.workerProcess.pid }
    this.workerProcess.once('exit', () => {
      this.workerState = { running: false, healthy: false }
      this.workerProcess = null
    })

    return this.workerProcess
  }

  markApiHealthy(healthy: boolean, detail?: string) {
    this.apiState = { ...this.apiState, healthy, detail }
  }

  markWorkerHealthy(healthy: boolean, detail?: string) {
    this.workerState = { ...this.workerState, healthy, detail }
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
