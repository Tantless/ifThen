import type { BootState } from '../lib/desktop'

export type DesktopBridge = {
  getServiceState: () => Promise<BootState>
  getAppInfo: () => Promise<{ name: string; version: string }>
  restartBackend: () => Promise<BootState>
}

declare global {
  interface Window {
    desktop?: DesktopBridge
  }
}

export {}
