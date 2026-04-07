export type DesktopBridge = {
  getServiceState: () => Promise<{ phase: string; detail?: string }>
}
