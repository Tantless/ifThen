import { ipcMain } from 'electron'

import type { DesktopServiceState, ManagedServiceState } from './backend/contracts'
import { BackendProcessManager } from './backend/processManager'

export function registerDesktopIpc(processManager: BackendProcessManager) {
  ipcMain.handle('desktop:get-service-state', (): DesktopServiceState => {
    const state: ManagedServiceState = processManager.getState()
    return {
      phase: state.phase,
      detail: state.detail,
    }
  })
}
