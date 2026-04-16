import { existsSync } from 'node:fs'
import path from 'node:path'

import type { BackendLaunchSpec } from './contracts.js'

export type DesktopBackendPathOptions = {
  entryFile: string
  isPackaged: boolean
  resourcesPath: string
  userDataDir: string
  env?: NodeJS.ProcessEnv
}

export type DesktopBackendPaths = {
  rootDir: string
  backendDir: string
  dataDir: string
  logsDir: string
  apiOrigin: string
  healthUrl: string
  apiAuthToken?: string
  rendererHtml: string
  isPackaged: boolean
}

export function resolveDesktopRepoRoot(entryFile: string): string {
  const entryDir = path.dirname(entryFile)
  const levelsToRepoRoot = path.basename(path.dirname(entryDir)) === 'dist-electron' ? 3 : 2

  return path.resolve(entryDir, ...Array.from({ length: levelsToRepoRoot }, () => '..'))
}

export function resolveDesktopRendererHtml(entryFile: string): string {
  const entryDir = path.dirname(entryFile)
  const relativeSegments =
    path.basename(path.dirname(entryDir)) === 'dist-electron'
      ? ['..', '..', 'dist', 'index.html']
      : ['..', 'dist', 'index.html']

  return path.resolve(entryDir, ...relativeSegments)
}

function resolvePythonCommand(repoRoot: string): string {
  const venvPython =
    process.platform === 'win32'
      ? path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
      : path.join(repoRoot, '.venv', 'bin', 'python')

  return existsSync(venvPython) ? venvPython : 'python'
}

function buildPythonEnv(paths: DesktopBackendPaths, env: NodeJS.ProcessEnv = process.env): NodeJS.ProcessEnv {
  const baseEnv: NodeJS.ProcessEnv = {
    ...env,
    IF_THEN_DATA_DIR: env.IF_THEN_DATA_DIR ?? paths.dataDir,
    IF_THEN_DESKTOP_LOG_DIR: env.IF_THEN_DESKTOP_LOG_DIR ?? paths.logsDir,
    IF_THEN_API_PORT: env.IF_THEN_API_PORT ?? paths.apiOrigin.split(':').at(-1),
    IF_THEN_API_AUTH_TOKEN: env.IF_THEN_API_AUTH_TOKEN ?? paths.apiAuthToken,
  }

  if (paths.isPackaged) {
    return baseEnv
  }

  const pythonPathEntries = [path.join(paths.rootDir, 'src'), env.PYTHONPATH].filter(Boolean)

  return {
    ...baseEnv,
    PYTHONPATH: pythonPathEntries.join(path.delimiter),
  }
}

export function getDesktopBackendPaths(options: DesktopBackendPathOptions): DesktopBackendPaths {
  const env = options.env ?? process.env
  const apiPort = env.IF_THEN_API_PORT ?? '8000'
  const apiOrigin = `http://127.0.0.1:${apiPort}`
  const rootDir = options.isPackaged ? options.resourcesPath : resolveDesktopRepoRoot(options.entryFile)
  const dataDir =
    env.IF_THEN_DATA_DIR ?? (options.isPackaged ? path.join(options.userDataDir, 'data') : path.join(rootDir, '.data'))

  return {
    rootDir: path.normalize(rootDir),
    backendDir: path.normalize(options.isPackaged ? path.join(options.resourcesPath, 'backend') : rootDir),
    dataDir: path.normalize(dataDir),
    logsDir: path.normalize(env.IF_THEN_DESKTOP_LOG_DIR ?? path.join(dataDir, 'logs')),
    apiOrigin,
    healthUrl: `${apiOrigin}/health`,
    apiAuthToken: env.IF_THEN_API_AUTH_TOKEN,
    rendererHtml: path.normalize(resolveDesktopRendererHtml(options.entryFile)),
    isPackaged: options.isPackaged,
  }
}

export function buildPythonLaunchSpec(
  kind: 'api' | 'worker',
  paths: DesktopBackendPaths,
  env: NodeJS.ProcessEnv = process.env,
): BackendLaunchSpec {
  if (paths.isPackaged) {
    const serviceDir = path.join(paths.backendDir, kind)
    const executableName = kind === 'api' ? 'if-then-api.exe' : 'if-then-worker.exe'

    return {
      command: path.join(serviceDir, executableName),
      args: [],
      cwd: serviceDir,
      env: buildPythonEnv(paths, env),
    }
  }

  const script = kind === 'api' ? 'scripts/run_api.py' : 'scripts/run_worker.py'

  return {
    command: resolvePythonCommand(paths.rootDir),
    args: [script],
    cwd: paths.rootDir,
    env: buildPythonEnv(paths, env),
  }
}
