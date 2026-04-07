export type DesktopBridge = {
  getServiceState: () => Promise<{ phase: string; detail?: string }>
  pickImportFile: () => Promise<{ canceled: boolean; filePaths: string[] }>
  getAppInfo: () => Promise<{ name: string; version: string }>
  readImportFile: () => Promise<{ fileName: string; content: string }>
}

declare global {
  interface Window {
    desktop?: DesktopBridge
  }
}

export {}
