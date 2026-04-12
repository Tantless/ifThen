import { beforeEach, describe, expect, it, vi } from 'vitest'

const { BrowserWindow, loadFile, loadURL, show, setApplicationMenu, appOn, appWhenReady } = vi.hoisted(() => {
  const loadFile = vi.fn(async () => undefined)
  const loadURL = vi.fn(async () => undefined)
  const show = vi.fn()
  const BrowserWindow = vi.fn().mockImplementation(function (this: Record<string, unknown>, _options: unknown) {
    this.loadFile = loadFile
    this.loadURL = loadURL
    this.show = show
  })

  return {
    BrowserWindow,
    loadFile,
    loadURL,
    show,
    setApplicationMenu: vi.fn(),
    appOn: vi.fn(),
    appWhenReady: vi.fn(() => new Promise<void>(() => {})),
  }
})

vi.mock('electron', () => ({
  app: {
    getPath: vi.fn(() => 'C:/Users/test/AppData/Roaming/if-then-desktop'),
    isPackaged: false,
    whenReady: appWhenReady,
    on: appOn,
    quit: vi.fn(),
  },
  BrowserWindow,
  Menu: {
    setApplicationMenu,
  },
}))

vi.mock('../electron/backend/health.js', () => ({
  waitForHealth: vi.fn(async () => true),
}))

vi.mock('../electron/backend/paths.js', () => ({
  buildPythonLaunchSpec: vi.fn(() => ({ command: 'python' })),
  getDesktopBackendPaths: vi.fn(() => ({
    healthUrl: 'http://127.0.0.1:8000/health',
    rendererHtml: 'dist/index.html',
  })),
  resolveDesktopRepoRoot: vi.fn(() => 'D:/newProj/desktop'),
}))

vi.mock('../electron/backend/processManager.js', () => ({
  BackendProcessManager: vi.fn().mockImplementation(() => ({
    startApi: vi.fn(),
    markApiHealthy: vi.fn(),
    startWorker: vi.fn(),
    stopAll: vi.fn(),
  })),
}))

vi.mock('../electron/ipc.js', () => ({
  registerDesktopIpc: vi.fn(),
}))

describe('createWindow', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    delete process.env.IF_THEN_DESKTOP_RENDERER_URL
  })

  it('creates a frameless hidden window and removes the default menu bar', async () => {
    const mainModule = await import('../electron/main')

    expect(mainModule).toMatchObject({
      createWindow: expect.any(Function),
    })

    const { createWindow } = mainModule as { createWindow: () => Promise<void> }

    await createWindow()

    expect(BrowserWindow).toHaveBeenCalledWith(
      expect.objectContaining({
        frame: false,
        titleBarStyle: 'hidden',
        backgroundColor: '#f5f5f5',
        show: false,
        webPreferences: expect.objectContaining({
          preload: expect.stringMatching(/preload\.cjs$/),
          contextIsolation: true,
          nodeIntegration: false,
        }),
      }),
    )
    expect(setApplicationMenu).toHaveBeenCalledWith(null)
    expect(loadFile).toHaveBeenCalledWith('dist/index.html')
    expect(loadURL).not.toHaveBeenCalled()
    expect(show).toHaveBeenCalledTimes(1)
  })
})
