export type ServiceState = {
  running: boolean
  healthy: boolean
  pid?: number
  detail?: string
}

export type ManagedServicePhase =
  | 'booting'
  | 'starting-api'
  | 'starting-worker'
  | 'waiting-api'
  | 'ready'
  | 'error'

export type ManagedServiceState = {
  phase: ManagedServicePhase
  api: ServiceState
  worker: ServiceState
  detail?: string
}

export type DesktopServiceState = Pick<ManagedServiceState, 'phase' | 'detail'>

export type BackendLaunchSpec = {
  command: string
  args: string[]
  cwd: string
  env?: NodeJS.ProcessEnv
}
