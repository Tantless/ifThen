import { app, BrowserWindow, Menu } from 'electron'
import { release as getOsRelease } from 'node:os'
import { fileURLToPath } from 'node:url'
import { waitForHealth } from './backend/health.js'
import { buildPythonLaunchSpec, getDesktopBackendPaths, resolveDesktopRepoRoot } from './backend/paths.js'
import { BackendProcessManager } from './backend/processManager.js'
import { getWindowsAppearanceOptions } from './backend/windowAppearance.js'
import { registerDesktopIpc } from './ipc.js'

const processManager = new BackendProcessManager()
const repoRoot = resolveDesktopRepoRoot(fileURLToPath(import.meta.url))
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
}

export async function createWindow() {
  const appearanceOptions = getWindowsAppearanceOptions({
    platform: process.platform,
    release: getOsRelease(),
  })

  const win = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    ...appearanceOptions,
    show: false,
    webPreferences: {
      preload: fileURLToPath(new URL('./preload.cjs', import.meta.url)),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })
  Menu.setApplicationMenu(null)

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
