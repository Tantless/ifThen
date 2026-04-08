import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { app, dialog, ipcMain } from 'electron'

import type { DesktopServiceState, ManagedServiceState } from './backend/contracts'
import { BackendProcessManager } from './backend/processManager.js'

export function registerDesktopIpc(processManager: BackendProcessManager) {
  let selectedImportFilePath: string | null = null

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

    selectedImportFilePath = result.canceled ? null : (result.filePaths[0] ?? null)

    return {
      canceled: result.canceled,
      filePaths: result.filePaths,
    }
  })

  ipcMain.handle('desktop:get-app-info', () => ({
    name: app.getName(),
    version: app.getVersion(),
  }))

  ipcMain.handle('desktop:read-import-file', async () => {
    if (!selectedImportFilePath) {
      throw new Error('No import file has been selected')
    }

    const filePath = selectedImportFilePath
    selectedImportFilePath = null

    const content = await readFile(filePath, 'utf8')

    return {
      fileName: path.basename(filePath),
      content,
    }
  })
}
