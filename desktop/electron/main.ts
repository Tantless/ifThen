import { app, BrowserWindow } from 'electron'
import path from 'node:path'
import { fileURLToPath } from 'node:url'
import { waitForHealth } from './backend/health'
import { buildPythonLaunchSpec, getDesktopBackendPaths } from './backend/paths'
import { BackendProcessManager } from './backend/processManager'
import { registerDesktopIpc } from './ipc'

const processManager = new BackendProcessManager()
const repoRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..', '..')
const backendPaths = getDesktopBackendPaths(repoRoot)

async function bootstrapBackend() {
  processManager.startApi(buildPythonLaunchSpec('api', repoRoot))

  const apiHealthy = await waitForHealth(backendPaths.healthUrl)
  processManager.markApiHealthy(
    apiHealthy,
    apiHealthy ? 'api healthcheck passed' : `health polling timed out at ${backendPaths.healthUrl}`,
  )

  if (!apiHealthy) {
    return
  }

  processManager.startWorker(buildPythonLaunchSpec('worker', repoRoot))
  processManager.markWorkerHealthy(true, 'worker process running')
}

async function createWindow() {
  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    show: false,
    webPreferences: {
      preload: fileURLToPath(new URL('./preload.js', import.meta.url)),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  const rendererUrl = process.env.IF_THEN_DESKTOP_RENDERER_URL

  if (rendererUrl) {
    await win.loadURL(rendererUrl)
  } else {
    await win.loadFile(backendPaths.rendererHtml)
  }

  win.show()
}

app.whenReady().then(async () => {
  registerDesktopIpc(processManager)
  void bootstrapBackend()
  await createWindow()
})

app.on('before-quit', () => {
  processManager.stopAll()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
