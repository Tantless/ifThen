import { app, BrowserWindow, Menu } from 'electron'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { waitForHealth } from './backend/health.js'
import { buildPythonLaunchSpec, getDesktopBackendPaths } from './backend/paths.js'
import { BackendProcessManager } from './backend/processManager.js'
import { registerDesktopIpc } from './ipc.js'

type DesktopAppBootstrapConfig = {
  hasSingleInstanceLock: boolean
  userDataDir: string
}

let cachedProcessManager: BackendProcessManager | null = null
let cachedBackendPaths: ReturnType<typeof getDesktopBackendPaths> | null = null
let mainWindow: BrowserWindow | null = null

function resolveDesktopUserDataDir(): string {
  if (app.isPackaged) {
    return app.getPath('userData')
  }

  return path.join(app.getPath('appData'), `${app.getName()}-dev`)
}

export function configureDesktopApp(): DesktopAppBootstrapConfig {
  const userDataDir = resolveDesktopUserDataDir()

  if (!app.isPackaged && userDataDir !== app.getPath('userData')) {
    app.setPath('userData', userDataDir)
  }

  const hasSingleInstanceLock = app.requestSingleInstanceLock()

  if (!hasSingleInstanceLock) {
    app.quit()
  }

  return {
    hasSingleInstanceLock,
    userDataDir,
  }
}

function focusMainWindow() {
  if (!mainWindow) {
    return
  }

  if (mainWindow.isMinimized()) {
    mainWindow.restore()
  }

  mainWindow.focus()
}

const desktopAppBootstrapConfig = configureDesktopApp()

function getDesktopRuntime() {
  if (cachedBackendPaths === null) {
    const entryFile = fileURLToPath(import.meta.url)

    cachedBackendPaths = getDesktopBackendPaths({
      entryFile,
      isPackaged: app.isPackaged,
      resourcesPath: process.resourcesPath,
      userDataDir: desktopAppBootstrapConfig.userDataDir,
      env: process.env,
    })
  }

  if (cachedProcessManager === null) {
    cachedProcessManager = new BackendProcessManager(cachedBackendPaths.logsDir)
  }

  return {
    backendPaths: cachedBackendPaths,
    processManager: cachedProcessManager,
  }
}

export async function bootstrapBackend() {
  const { backendPaths, processManager } = getDesktopRuntime()
  processManager.startApi(buildPythonLaunchSpec('api', backendPaths))

  const apiHealthy = await waitForHealth(backendPaths.healthUrl)
  const stateAfterHealthCheck = processManager.getState()

  if (!stateAfterHealthCheck.api.running) {
    const existingDetail = stateAfterHealthCheck.api.detail ?? 'api process exited before healthcheck completed'
    const detail = apiHealthy
      ? `${existingDetail}; another service may already be responding on ${backendPaths.healthUrl}`
      : existingDetail

    processManager.markApiHealthy(false, detail)
    return
  }

  processManager.markApiHealthy(
    apiHealthy,
    apiHealthy ? 'api healthcheck passed' : `health polling timed out at ${backendPaths.healthUrl}`,
  )

  if (!apiHealthy) {
    return
  }

  processManager.startWorker(buildPythonLaunchSpec('worker', backendPaths))
}

export async function createWindow() {
  const { backendPaths } = getDesktopRuntime()
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    frame: false,
    titleBarStyle: 'hidden',
    backgroundColor: '#f5f5f5',
    show: false,
    webPreferences: {
      preload: fileURLToPath(new URL('./preload.cjs', import.meta.url)),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })
  Menu.setApplicationMenu(null)
  mainWindow = win
  win.on('closed', () => {
    if (mainWindow === win) {
      mainWindow = null
    }
  })

  const rendererUrl = process.env.IF_THEN_DESKTOP_RENDERER_URL

  if (rendererUrl) {
    await win.loadURL(rendererUrl)
  } else {
    await win.loadFile(backendPaths.rendererHtml)
  }

  win.show()
}

if (desktopAppBootstrapConfig.hasSingleInstanceLock) {
  app.on('second-instance', () => {
    focusMainWindow()
  })

  app.whenReady().then(async () => {
    const { processManager } = getDesktopRuntime()
    registerDesktopIpc(processManager)
    void bootstrapBackend()
    await createWindow()
  })

  app.on('before-quit', () => {
    cachedProcessManager?.stopAll()
  })

  app.on('window-all-closed', () => {
    if (process.platform !== 'darwin') {
      app.quit()
    }
  })
}
