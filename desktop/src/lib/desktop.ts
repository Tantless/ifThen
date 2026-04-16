import type {
  DesktopAppInfo,
  DesktopAvatarFilePayload,
  DesktopBridge,
  DesktopFileSelectionPayload,
  DesktopServiceState,
} from '../types/desktop'

export type BootState = {
  phase: 'booting' | 'starting-api' | 'starting-worker' | 'waiting-api' | 'ready' | 'error'
  detail?: string
}

export type DesktopStatePayload = DesktopServiceState

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

export function normalizeDesktopFileSelection(input: DesktopFileSelectionPayload): string | null {
  if (input.canceled) {
    return null
  }

  return input.filePaths[0] ?? null
}

export function shouldUseDesktopBridge(capability: string): boolean {
  return capability === 'pick-import-file' || capability === 'pick-avatar-file'
}

export function getDesktopBridge(): DesktopBridge | undefined {
  return (globalThis as typeof globalThis & { desktop?: DesktopBridge }).desktop
}

export function requireDesktopBridge(): DesktopBridge {
  const desktopBridge = getDesktopBridge()

  if (!desktopBridge) {
    throw new Error('desktop bridge unavailable')
  }

  return desktopBridge
}

export async function readDesktopServiceState(): Promise<BootState> {
  const desktopBridge = getDesktopBridge()

  if (!desktopBridge) {
    return { phase: 'booting', detail: 'desktop bridge unavailable' }
  }

  const state = await desktopBridge.getServiceState()
  return normalizeDesktopState(state)
}

export async function openImportFileDialog(): Promise<string | null> {
  const desktopBridge = getDesktopBridge()

  if (!desktopBridge || !shouldUseDesktopBridge('pick-import-file')) {
    return null
  }

  const selection = await desktopBridge.pickImportFile()
  return normalizeDesktopFileSelection(selection)
}

export async function pickAvatarFile(): Promise<DesktopAvatarFilePayload | null> {
  const desktopBridge = getDesktopBridge()

  if (!desktopBridge || !shouldUseDesktopBridge('pick-avatar-file')) {
    return null
  }

  return desktopBridge.pickAvatarFile()
}
