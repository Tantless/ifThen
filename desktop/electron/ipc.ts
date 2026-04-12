import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { app, BrowserWindow, dialog, ipcMain } from 'electron'

import type { DesktopServiceState, ManagedServiceState } from './backend/contracts.js'
import type { DesktopWindowState } from '../src/types/desktop.js'
import type { IpcMainInvokeEvent } from 'electron'
import { BackendProcessManager } from './backend/processManager.js'

export function registerDesktopIpc(processManager: BackendProcessManager) {
  let selectedImportFilePath: string | null = null
  const getEventWindow = (event: IpcMainInvokeEvent, channel: string) => {
    const focusedWindow = BrowserWindow.fromWebContents(event.sender)

    if (!focusedWindow) {
      throw new Error(`No BrowserWindow found for ${channel}`)
    }

    return focusedWindow
  }

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

  ipcMain.handle('desktop:pick-avatar-file', async () => {
    const result = await dialog.showOpenDialog({
      properties: ['openFile'],
      filters: [{ name: 'Avatar image', extensions: ['png', 'jpg', 'jpeg', 'webp', 'gif', 'svg'] }],
    })

    const filePath = result.canceled ? null : (result.filePaths[0] ?? null)
    if (!filePath) {
      return null
    }

    const bytes = await readFile(filePath)
    const extension = path.extname(filePath).toLowerCase()
    const mimeType =
      extension === '.png'
        ? 'image/png'
        : extension === '.jpg' || extension === '.jpeg'
          ? 'image/jpeg'
          : extension === '.webp'
            ? 'image/webp'
            : extension === '.gif'
              ? 'image/gif'
              : extension === '.svg'
                ? 'image/svg+xml'
                : 'application/octet-stream'

    return {
      fileName: path.basename(filePath),
      mimeType,
      dataUrl: `data:${mimeType};base64,${Buffer.from(bytes).toString('base64')}`,
    }
  })

  ipcMain.handle('desktop:get-app-info', () => ({
    name: app.getName(),
    version: app.getVersion(),
  }))

  ipcMain.handle('desktop:window-minimize', (event) => {
    getEventWindow(event, 'desktop:window-minimize').minimize()
  })

  ipcMain.handle('desktop:window-toggle-maximize', (event): DesktopWindowState => {
    const focusedWindow = getEventWindow(event, 'desktop:window-toggle-maximize')

    if (focusedWindow.isMaximized()) {
      focusedWindow.unmaximize()
      return {
        isMaximized: false,
      }
    }

    focusedWindow.maximize()

    return {
      isMaximized: true,
    }
  })

  ipcMain.handle('desktop:window-close', (event) => {
    getEventWindow(event, 'desktop:window-close').close()
  })

  ipcMain.handle('desktop:window-get-state', (event): DesktopWindowState => ({
    isMaximized: getEventWindow(event, 'desktop:window-get-state').isMaximized(),
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
