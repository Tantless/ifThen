import type { DesktopBridge, DesktopWindowBridge, DesktopWindowState } from '../types/desktop'

const FALLBACK_WINDOW_STATE: DesktopWindowState = {
  isMaximized: false,
}

function getDesktopWindowBridge(): DesktopWindowBridge | null {
  const desktopBridge = (globalThis as typeof globalThis & { desktop?: DesktopBridge }).desktop
  return desktopBridge?.window ?? null
}

export async function getDesktopWindowState(): Promise<DesktopWindowState> {
  const desktopWindowBridge = getDesktopWindowBridge()

  if (!desktopWindowBridge) {
    return FALLBACK_WINDOW_STATE
  }

  return desktopWindowBridge.getState()
}

export async function minimizeDesktopWindow(): Promise<void> {
  const desktopWindowBridge = getDesktopWindowBridge()

  if (!desktopWindowBridge) {
    return
  }

  await desktopWindowBridge.minimize()
}

export async function toggleDesktopWindowMaximize(): Promise<DesktopWindowState> {
  const desktopWindowBridge = getDesktopWindowBridge()

  if (!desktopWindowBridge) {
    return FALLBACK_WINDOW_STATE
  }

  return desktopWindowBridge.toggleMaximize()
}

export async function closeDesktopWindow(): Promise<void> {
  const desktopWindowBridge = getDesktopWindowBridge()

  if (!desktopWindowBridge) {
    return
  }

  await desktopWindowBridge.close()
}
