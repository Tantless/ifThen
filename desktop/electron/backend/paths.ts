import path from 'node:path'

export function getDesktopBackendPaths(rootDir: string) {
  return {
    rootDir,
    backendDir: path.join(rootDir, 'desktop', 'electron', 'backend'),
  }
}
