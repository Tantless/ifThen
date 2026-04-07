import { useMemo } from 'react'
import { BootScreen } from './components/BootScreen'
import { DesktopShellPlaceholder } from './components/DesktopShellPlaceholder'
import { getBootLabel, type BootState } from './lib/desktop'

const initialState: BootState = { phase: 'booting' }

export default function App() {
  const label = useMemo(() => getBootLabel(initialState), [])

  if (initialState.phase !== 'ready') {
    return <BootScreen label={label} detail="等待 Electron 主进程接入…" />
  }

  return <DesktopShellPlaceholder />
}
