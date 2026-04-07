import { app, dialog, ipcMain } from 'electron'

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

  ipcMain.handle('desktop:pick-import-file', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: [{ name: 'QQ chat export', extensions: ['txt'] }],
    })

    return {
      canceled: result.canceled,
      filePaths: result.filePaths,
    }
  })

  ipcMain.handle('desktop:get-app-info', () => ({
    name: app.getName(),
    version: app.getVersion(),
  }))
}
