import { beforeEach, describe, expect, it, vi } from 'vitest'
import path from 'node:path'

const {
  BrowserWindow,
  appHandlers,
  appGetName,
  appGetPath,
  appQuit,
  appRequestSingleInstanceLock,
  appSetPath,
  loadFile,
  loadURL,
  show,
  setApplicationMenu,
  appOn,
  appWhenReady,
  pathState,
  waitForHealth,
  buildPythonLaunchSpec,
  getDesktopBackendPaths,
  resolveDesktopRepoRoot,
  startApi,
  markApiHealthy,
  startWorker,
  stopAll,
  getState,
} = vi.hoisted(() => {
  const pathState = {
    appData: 'C:/Users/test/AppData/Roaming',
    userData: 'C:/Users/test/AppData/Roaming/if-then-desktop',
  }
  const loadFile = vi.fn(async () => undefined)
  const loadURL = vi.fn(async () => undefined)
  const show = vi.fn()
  const appHandlers = new Map<string, (...args: unknown[]) => unknown>()
  const BrowserWindow = vi.fn().mockImplementation(function (this: Record<string, unknown>, _options: unknown) {
    this.loadFile = loadFile
    this.loadURL = loadURL
    this.show = show
    this.isMinimized = vi.fn(() => false)
    this.on = vi.fn()
    this.restore = vi.fn()
    this.focus = vi.fn()
  })

  return {
    BrowserWindow,
    appHandlers,
    appGetName: vi.fn(() => 'if-then-desktop'),
    appGetPath: vi.fn((name: string) => pathState[name as 'appData' | 'userData']),
    appQuit: vi.fn(),
    appRequestSingleInstanceLock: vi.fn(() => true),
    appSetPath: vi.fn((name: string, value: string) => {
      if (name === 'userData') {
        pathState.userData = value
      }
    }),
    loadFile,
    loadURL,
    show,
    setApplicationMenu: vi.fn(),
    appOn: vi.fn((event: string, handler: (...args: unknown[]) => unknown) => {
      appHandlers.set(event, handler)
    }),
    appWhenReady: vi.fn(() => new Promise<void>(() => {})),
    pathState,
    waitForHealth: vi.fn(async () => true),
    buildPythonLaunchSpec: vi.fn((kind: string) => ({ command: kind })),
    getDesktopBackendPaths: vi.fn(() => ({
      healthUrl: 'http://127.0.0.1:8000/health',
      rendererHtml: 'dist/index.html',
      logsDir: 'D:/logs',
    })),
    resolveDesktopRepoRoot: vi.fn(() => 'D:/newProj/desktop'),
    startApi: vi.fn(),
    markApiHealthy: vi.fn(),
    startWorker: vi.fn(),
    stopAll: vi.fn(),
    getState: vi.fn(() => ({
      phase: 'starting-api',
      api: { running: true, healthy: false },
      worker: { running: false, healthy: false },
    })),
  }
})

vi.mock('electron', () => ({
  app: {
    getName: appGetName,
    getPath: appGetPath,
    requestSingleInstanceLock: appRequestSingleInstanceLock,
    setPath: appSetPath,
    isPackaged: false,
    whenReady: appWhenReady,
    on: appOn,
    quit: appQuit,
  },
  BrowserWindow,
  Menu: {
    setApplicationMenu,
  },
}))

vi.mock('../electron/backend/health.js', () => ({
  waitForHealth,
}))

vi.mock('../electron/backend/paths.js', () => ({
  buildPythonLaunchSpec,
  getDesktopBackendPaths,
  resolveDesktopRepoRoot,
}))

vi.mock('../electron/backend/processManager.js', () => ({
  BackendProcessManager: vi.fn().mockImplementation(() => ({
    startApi,
    markApiHealthy,
    startWorker,
    stopAll,
    getState,
  })),
}))

vi.mock('../electron/ipc.js', () => ({
  registerDesktopIpc: vi.fn(),
}))

describe('createWindow', () => {
  beforeEach(() => {
    vi.resetModules()
    vi.clearAllMocks()
    delete process.env.IF_THEN_DESKTOP_RENDERER_URL
    pathState.appData = 'C:/Users/test/AppData/Roaming'
    pathState.userData = 'C:/Users/test/AppData/Roaming/if-then-desktop'
    appHandlers.clear()
    appRequestSingleInstanceLock.mockReturnValue(true)
    waitForHealth.mockResolvedValue(true)
    getState.mockReturnValue({
      phase: 'starting-api',
      api: { running: true, healthy: false },
      worker: { running: false, healthy: false },
    } as any)
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

  it('refuses to start the worker when the claimed api process exited before health succeeded', async () => {
    const mainModule = await import('../electron/main')

    expect(mainModule).toMatchObject({
      bootstrapBackend: expect.any(Function),
    })

    const { bootstrapBackend } = mainModule as { bootstrapBackend: () => Promise<void> }

    getState.mockReturnValue({
      phase: 'error',
      api: {
        running: false,
        healthy: false,
        detail: 'process exited unexpectedly (code 1)',
      },
      worker: { running: false, healthy: false },
    } as any)

    await bootstrapBackend()

    expect(startApi).toHaveBeenCalledTimes(1)
    expect(waitForHealth).toHaveBeenCalledWith('http://127.0.0.1:8000/health')
    expect(markApiHealthy).toHaveBeenCalledWith(
      false,
      expect.stringContaining('process exited unexpectedly (code 1)'),
    )
    expect(startWorker).not.toHaveBeenCalled()
  })

  it('separates dev userData from the packaged app and requests a single-instance lock on startup', async () => {
    const mainModule = await import('../electron/main')
    const { createWindow } = mainModule as { createWindow: () => Promise<void> }

    await createWindow()

    expect(appSetPath).toHaveBeenCalledWith(
      'userData',
      path.normalize('C:/Users/test/AppData/Roaming/if-then-desktop-dev'),
    )
    expect(appRequestSingleInstanceLock).toHaveBeenCalledTimes(1)
    expect(getDesktopBackendPaths).toHaveBeenCalledWith(
      expect.objectContaining({
        userDataDir: path.normalize('C:/Users/test/AppData/Roaming/if-then-desktop-dev'),
      }),
    )
    expect(appHandlers.get('second-instance')).toBeTypeOf('function')
  })

  it('quits immediately when another desktop instance already holds the single-instance lock', async () => {
    appRequestSingleInstanceLock.mockReturnValue(false)

    await import('../electron/main')

    expect(appQuit).toHaveBeenCalledTimes(1)
    expect(appWhenReady).not.toHaveBeenCalled()
  })

  it('restores and focuses the existing window when a second instance is launched', async () => {
    const mainModule = await import('../electron/main')
    const { createWindow } = mainModule as { createWindow: () => Promise<void> }

    await createWindow()

    const secondInstance = appHandlers.get('second-instance')
    expect(secondInstance).toBeTypeOf('function')

    const existingWindow = BrowserWindow.mock.instances[0] as {
      isMinimized: ReturnType<typeof vi.fn>
      restore: ReturnType<typeof vi.fn>
      focus: ReturnType<typeof vi.fn>
    }

    existingWindow.isMinimized.mockReturnValue(true)

    if (!secondInstance) {
      throw new Error('expected second-instance handler to be registered')
    }

    secondInstance()

    expect(existingWindow.restore).toHaveBeenCalledTimes(1)
    expect(existingWindow.focus).toHaveBeenCalledTimes(1)
  })
})
