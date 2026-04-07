import { useEffect, useMemo, useState } from 'react'
import { BootScreen } from './components/BootScreen'
import { AppShell } from './components/AppShell'
import { ConversationEmptyState } from './components/ConversationEmptyState'
import { SidebarNav } from './components/SidebarNav'
import { decideAppShellState, resolveShellHydrationStatus } from './lib/bootstrap'
import { getBootLabel, readDesktopServiceState, type BootState } from './lib/desktop'
import { listConversations } from './lib/services/conversationService'
import { readSettings } from './lib/services/settingsService'
import type { ConversationRead, SettingRead } from './types/api'

export default function App() {
  const [state, setState] = useState<BootState>({ phase: 'booting' })
  const [settings, setSettings] = useState<SettingRead[] | null>(null)
  const [conversations, setConversations] = useState<ConversationRead[] | null>(null)
  const [shellLoadError, setShellLoadError] = useState(false)

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

  useEffect(() => {
    if (state.phase !== 'ready') {
      setSettings(null)
      setConversations(null)
      setShellLoadError(false)
      return
    }

    let cancelled = false

    const hydrateShell = async () => {
      const [settingsResult, conversationsResult] = await Promise.allSettled([readSettings(), listConversations()])

      if (cancelled) {
        return
      }

      setShellLoadError(settingsResult.status === 'rejected' || conversationsResult.status === 'rejected')
      setSettings(settingsResult.status === 'fulfilled' ? settingsResult.value : [])
      setConversations(conversationsResult.status === 'fulfilled' ? conversationsResult.value : [])
    }

    void hydrateShell()

    return () => {
      cancelled = true
    }
  }, [state.phase])

  const label = useMemo(() => getBootLabel(state), [state])

  if (state.phase !== 'ready') {
    return <BootScreen label={label} detail={state.detail} />
  }

  const hydrationStatus = resolveShellHydrationStatus({
    settings,
    conversations,
    hasLoadError: shellLoadError,
  })

  const shellState =
    hydrationStatus === 'ready'
      ? decideAppShellState({
          bootPhase: state.phase,
          settings: settings ?? [],
          conversations: conversations ?? [],
        })
      : null

  const listPane = (
    <section className="conversation-list-placeholder">
      <header className="conversation-list-placeholder__header">
        <h2>会话</h2>
        <p>Task 2 先接入真实 app shell，列表交互留到后续任务。</p>
      </header>
      <div className="conversation-list-placeholder__body">
        {hydrationStatus === 'loading' ? (
          <p>正在读取会话…</p>
        ) : hydrationStatus === 'error' ? (
          <p>会话或设置数据读取失败，当前保留最小壳层。</p>
        ) : (conversations?.length ?? 0) === 0 ? (
          <p>还没有已导入会话。</p>
        ) : (
          <p>已发现 {conversations?.length ?? 0} 个会话，列表与详情逻辑将在后续任务接入。</p>
        )}
      </div>
    </section>
  )

  return (
    <AppShell
      sidebar={<SidebarNav />}
      listPane={listPane}
      chatPane={
        <ConversationEmptyState
          variant={
            hydrationStatus === 'loading'
              ? 'loading'
              : hydrationStatus === 'error'
                ? 'error'
                : shellState?.showWelcome
                  ? 'welcome'
                  : 'empty'
          }
        />
      }
    />
  )
}
