import { useEffect, useMemo, useState } from 'react'
import { BootScreen } from './components/BootScreen'
import { DesktopShellPlaceholder } from './components/DesktopShellPlaceholder'
import { getBootLabel, readDesktopServiceState, type BootState } from './lib/desktop'

export default function App() {
  const [state, setState] = useState<BootState>({ phase: 'booting' })

  useEffect(() => {
    let cancelled = false

    const tick = async () => {
      const next = await readDesktopServiceState()
      if (!cancelled) {
        setState(next)
      }
    }

    void tick()
    const intervalId = window.setInterval(() => {
      void tick()
    }, 1000)

    return () => {
      cancelled = true
      window.clearInterval(intervalId)
    }
  }, [])

  const label = useMemo(() => getBootLabel(state), [state])

  if (state.phase !== 'ready') {
    return <BootScreen label={label} detail={state.detail} />
  }

  return <DesktopShellPlaceholder />
}
