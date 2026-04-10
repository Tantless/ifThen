import { existsSync } from 'node:fs'
import path from 'node:path'

import type { BackendLaunchSpec } from './contracts.js'

const DEFAULT_HEALTH_URL = 'http://127.0.0.1:8000/health'

export function resolveDesktopRepoRoot(entryFile: string): string {
  const entryDir = path.dirname(entryFile)
  const levelsToRepoRoot = path.basename(path.dirname(entryDir)) === 'dist-electron' ? 3 : 2

  return path.resolve(entryDir, ...Array.from({ length: levelsToRepoRoot }, () => '..'))
}

function resolvePythonCommand(repoRoot: string): string {
  const venvPython =
    process.platform === 'win32'
      ? path.join(repoRoot, '.venv', 'Scripts', 'python.exe')
      : path.join(repoRoot, '.venv', 'bin', 'python')

  return existsSync(venvPython) ? venvPython : 'python'
}

function buildPythonEnv(repoRoot: string, env: NodeJS.ProcessEnv = process.env): NodeJS.ProcessEnv {
  const pythonPathEntries = [path.join(repoRoot, 'src'), env.PYTHONPATH].filter(Boolean)

  return {
    ...env,
    IF_THEN_DATA_DIR: env.IF_THEN_DATA_DIR ?? path.join(repoRoot, '.data'),
    PYTHONPATH: pythonPathEntries.join(path.delimiter),
  }
}

export function getDesktopBackendPaths(rootDir: string) {
  return {
    rootDir,
    backendDir: path.join(rootDir, 'desktop', 'electron', 'backend'),
    dataDir: path.join(rootDir, '.data'),
    healthUrl: DEFAULT_HEALTH_URL,
    rendererHtml: path.join(rootDir, 'desktop', 'dist', 'index.html'),
  }
}

export function buildPythonLaunchSpec(
  kind: 'api' | 'worker',
  repoRoot: string,
  env: NodeJS.ProcessEnv = process.env,
): BackendLaunchSpec {
  const script = kind === 'api' ? 'scripts/run_api.py' : 'scripts/run_worker.py'

  return {
    command: resolvePythonCommand(repoRoot),
    args: [script],
    cwd: repoRoot,
    env: buildPythonEnv(repoRoot, env),
  }
}
