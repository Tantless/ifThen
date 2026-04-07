import type { BootState } from '../lib/desktop'

export type DesktopBridge = {
  getBootState?: () => Promise<BootState> | BootState
}

declare global {
  interface Window {
    desktop?: DesktopBridge
  }
}

export {}
