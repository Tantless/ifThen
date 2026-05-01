import { readFile } from 'node:fs/promises'
import path from 'node:path'
import { app, BrowserWindow, dialog, ipcMain } from 'electron'

import type { DesktopServiceState, ManagedServiceState } from './backend/contracts.js'
import type { DesktopWindowState } from '../src/types/desktop.js'
import type {
  ImportConversationRequest,
  ListConversationJobsInput,
  ListConversationSimulationJobsInput,
  ListMessagesInput,
  ReadMessageContextInput,
  ReadSnapshotInput,
  SettingWrite,
  SimulationCreate,
} from '../src/types/api.js'
import type { IpcMainInvokeEvent } from 'electron'
import { DesktopBackendClient } from './backend/client.js'
import { BackendProcessManager } from './backend/processManager.js'

export function registerDesktopIpc(processManager: BackendProcessManager, backendClient: DesktopBackendClient) {
  let selectedImportFilePath: string | null = null
  const getEventWindow = (event: IpcMainInvokeEvent, channel: string) => {
    const focusedWindow = BrowserWindow.fromWebContents(event.sender)

    if (!focusedWindow) {
      throw new Error(`No BrowserWindow found for ${channel}`)
    }

    return focusedWindow
  }

  const consumeSelectedImportFilePath = () => {
    if (!selectedImportFilePath) {
      throw new Error('No import file has been selected')
    }

    const filePath = selectedImportFilePath
    selectedImportFilePath = null
    return filePath
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

  ipcMain.handle('desktop:settings-read', async () => backendClient.readSettings())

  ipcMain.handle('desktop:settings-write', async (_event, payload: SettingWrite) => backendClient.writeSetting(payload))

  ipcMain.handle('desktop:conversations-list', async () => backendClient.listConversations())

  ipcMain.handle('desktop:conversations-delete', async (_event, conversationId: number) => {
    await backendClient.deleteConversation(conversationId)
  })

  ipcMain.handle('desktop:conversations-list-messages', async (_event, payload: ListMessagesInput) =>
    backendClient.listMessages(payload),
  )

  ipcMain.handle('desktop:conversations-list-message-days', async (_event, conversationId: number) =>
    backendClient.listMessageDays(conversationId),
  )

  ipcMain.handle('desktop:conversations-read-message-context', async (_event, payload: ReadMessageContextInput) =>
    backendClient.readMessageContext(payload),
  )

  ipcMain.handle('desktop:conversations-list-topics', async (_event, conversationId: number) =>
    backendClient.listTopics(conversationId),
  )

  ipcMain.handle('desktop:conversations-read-profile', async (_event, conversationId: number) =>
    backendClient.readProfile(conversationId),
  )

  ipcMain.handle('desktop:conversations-read-snapshot', async (_event, payload: ReadSnapshotInput) =>
    backendClient.readSnapshot(payload),
  )

  ipcMain.handle('desktop:conversations-import', async (_event, payload: ImportConversationRequest) =>
    backendClient.importConversation({
      ...payload,
      filePath: consumeSelectedImportFilePath(),
    }),
  )

  ipcMain.handle('desktop:conversations-start-analysis', async (_event, conversationId: number) =>
    backendClient.startAnalysis(conversationId),
  )

  ipcMain.handle('desktop:jobs-list-conversation', async (_event, payload: ListConversationJobsInput) =>
    backendClient.listConversationJobs(payload),
  )

  ipcMain.handle('desktop:jobs-read', async (_event, jobId: number) => backendClient.readJob(jobId))

  ipcMain.handle('desktop:jobs-rerun-analysis', async (_event, conversationId: number) =>
    backendClient.rerunAnalysis(conversationId),
  )

  ipcMain.handle('desktop:simulations-create', async (_event, payload: SimulationCreate) =>
    backendClient.createSimulation(payload),
  )

  ipcMain.handle('desktop:simulations-list-conversation-jobs', async (_event, payload: ListConversationSimulationJobsInput) =>
    backendClient.listConversationSimulationJobs(payload),
  )

  ipcMain.handle('desktop:simulations-read', async (_event, simulationId: number) =>
    backendClient.readSimulation(simulationId),
  )

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

}
