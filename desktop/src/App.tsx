import { useEffect, useMemo, useState } from 'react'
import { BootScreen } from './components/BootScreen'
import { DesktopShellPlaceholder } from './components/DesktopShellPlaceholder'
import { getBootLabel, readDesktopServiceState, type BootState } from './lib/desktop'

export default function App() {
  const [state, setState] = useState<BootState>({ phase: 'booting' })

  useEffect(() => {
    let cancelled = false
    let timeoutId: number | null = null

    const isTerminalPhase = (phase: BootState['phase']) => phase === 'ready' || phase === 'error'

    const tick = async () => {
      const next = await readDesktopServiceState()
      if (cancelled) {
        return
      }

      setState(next)

      if (!isTerminalPhase(next.phase)) {
        timeoutId = window.setTimeout(() => {
          void tick()
        }, 1000)
      }
    }

    void tick()

    return () => {
      cancelled = true
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [])

  const label = useMemo(() => getBootLabel(state), [state])

  if (state.phase !== 'ready') {
    return <BootScreen label={label} detail={state.detail} />
  }

  return <DesktopShellPlaceholder />
}
