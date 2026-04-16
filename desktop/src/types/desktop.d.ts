import type { DesktopBridge } from './desktop'

declare global {
  interface Window {
    desktop?: DesktopBridge
  }
}

export {}
