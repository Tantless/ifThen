export type BootState = {
  phase: 'booting' | 'starting-api' | 'starting-worker' | 'waiting-api' | 'ready' | 'error'
  detail?: string
}

export type DesktopStatePayload = {
  phase: BootState['phase']
  detail?: string
}

type DesktopBridge = {
  getServiceState: () => Promise<DesktopStatePayload>
}

export function getBootLabel(state: BootState): string {
  switch (state.phase) {
    case 'waiting-api':
    case 'starting-api':
      return '正在启动本地分析服务…'
    case 'starting-worker':
      return '正在启动后台分析进程…'
    case 'ready':
      return '服务已就绪'
    case 'error':
      return '桌面服务启动失败'
    default:
      return '桌面应用正在初始化…'
  }
}

export function normalizeDesktopState(input: DesktopStatePayload): BootState {
  return { phase: input.phase, detail: input.detail }
}

export async function readDesktopServiceState(): Promise<BootState> {
  const desktopBridge = (globalThis as typeof globalThis & { desktop?: DesktopBridge }).desktop

  if (!desktopBridge) {
    return { phase: 'booting', detail: 'desktop bridge unavailable' }
  }

  const state = await desktopBridge.getServiceState()
  return normalizeDesktopState(state)
}
