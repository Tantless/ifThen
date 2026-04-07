import { app, BrowserWindow } from 'electron'
import { fileURLToPath } from 'node:url'
import { BackendProcessManager } from './backend/processManager'

const processManager = new BackendProcessManager()

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

  await win.loadURL(process.env.IF_THEN_DESKTOP_RENDERER_URL ?? 'http://127.0.0.1:5173')
  win.show()
}

app.whenReady().then(createWindow)

app.on('before-quit', () => {
  processManager.stopAll()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
