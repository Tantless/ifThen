export type BootState = {
  phase: 'booting' | 'starting-api' | 'starting-worker' | 'waiting-api' | 'ready' | 'error'
  detail?: string
}

export type DesktopStatePayload = {
  phase: BootState['phase']
  detail?: string
}

export type DesktopFileSelectionPayload = {
  canceled: boolean
  filePaths: string[]
}

export type DesktopAppInfo = {
  name: string
  version: string
}

export type DesktopImportFilePayload = {
  fileName: string
  content: string
}

type DesktopBridge = {
  getServiceState: () => Promise<DesktopStatePayload>
  pickImportFile: () => Promise<DesktopFileSelectionPayload>
  getAppInfo: () => Promise<DesktopAppInfo>
  readImportFile: () => Promise<DesktopImportFilePayload>
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

export function normalizeDesktopFileSelection(input: DesktopFileSelectionPayload): string | null {
  if (input.canceled) {
    return null
  }

  return input.filePaths[0] ?? null
}

export function shouldUseDesktopBridge(capability: string): boolean {
  return capability === 'pick-import-file' || capability === 'read-import-file'
}

function getDesktopBridge(): DesktopBridge | undefined {
  return (globalThis as typeof globalThis & { desktop?: DesktopBridge }).desktop
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

export function createImportFileBlob(input: DesktopImportFilePayload): Blob {
  return new Blob([input.content], { type: 'text/plain;charset=utf-8' })
}

export async function readImportFile(): Promise<DesktopImportFilePayload | null> {
  const desktopBridge = getDesktopBridge()

  if (!desktopBridge || !shouldUseDesktopBridge('read-import-file')) {
    return null
  }

  return desktopBridge.readImportFile()
}
