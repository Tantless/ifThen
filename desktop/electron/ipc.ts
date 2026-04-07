import { app, ipcMain } from 'electron'

import type { ManagedServiceState } from './backend/contracts'
import { BackendProcessManager } from './backend/processManager'

type DesktopAppInfo = {
  name: string
  version: string
}

export function registerDesktopIpc(processManager: BackendProcessManager) {
  ipcMain.handle('desktop:get-service-state', (): ManagedServiceState => processManager.getState())
  ipcMain.handle(
    'desktop:get-app-info',
    (): DesktopAppInfo => ({
      name: app.getName(),
      version: app.getVersion(),
    }),
  )
  ipcMain.handle('desktop:restart-backend', (): ManagedServiceState => {
    processManager.stopAll()
    return processManager.getState()
  })
}
