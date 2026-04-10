export type DesktopServiceState = {
  phase: 'booting' | 'starting-api' | 'starting-worker' | 'waiting-api' | 'ready' | 'error'
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

export type DesktopWindowState = {
  isMaximized: boolean
}

export type DesktopWindowBridge = {
  minimize: () => Promise<void>
  toggleMaximize: () => Promise<DesktopWindowState>
  close: () => Promise<void>
  getState: () => Promise<DesktopWindowState>
}

export type DesktopBridge = {
  getServiceState: () => Promise<DesktopServiceState>
  pickImportFile: () => Promise<DesktopFileSelectionPayload>
  getAppInfo: () => Promise<DesktopAppInfo>
  readImportFile: () => Promise<DesktopImportFilePayload>
  window: DesktopWindowBridge
}
