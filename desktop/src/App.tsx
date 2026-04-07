import { useEffect, useMemo, useState } from 'react'
import { BootScreen } from './components/BootScreen'
import { AppShell } from './components/AppShell'
import { SidebarNav } from './components/SidebarNav'
import { WelcomeModal } from './components/WelcomeModal'
import { SettingsDrawer } from './components/SettingsDrawer'
import { ImportDialog } from './components/ImportDialog'
import { ConversationListPane } from './components/ConversationListPane'
import { ChatPane } from './components/ChatPane'
import { decideAppShellState, resolveShellHydrationStatus } from './lib/bootstrap'
import {
  createImportFileBlob,
  getBootLabel,
  readDesktopServiceState,
  readImportFile,
  type BootState,
} from './lib/desktop'
import {
  buildConversationListItem,
  buildMessageBubbleModel,
  buildSettingsFormState,
  type SettingsFormState,
} from './lib/adapters'
import { importConversation, listConversations, listMessages } from './lib/services/conversationService'
import { listConversationJobs, readJob } from './lib/services/jobService'
import { readSettings, writeSetting } from './lib/services/settingsService'
import type { ConversationRead, JobRead, MessageRead, SettingRead } from './types/api'

function isPollingJob(job: JobRead | null | undefined): job is JobRead {
  return job?.status === 'running' || job?.status === 'queued'
}

export default function App() {
  const [state, setState] = useState<BootState>({ phase: 'booting' })
  const [settings, setSettings] = useState<SettingRead[] | null>(null)
  const [conversations, setConversations] = useState<ConversationRead[] | null>(null)
  const [shellLoadError, setShellLoadError] = useState(false)
  const [showWelcome, setShowWelcome] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [settingsSavePending, setSettingsSavePending] = useState(false)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [importPending, setImportPending] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null)
  const [conversationSearch, setConversationSearch] = useState('')
  const [latestJobsByConversation, setLatestJobsByConversation] = useState<Record<number, JobRead | null>>({})
  const [messagesByConversation, setMessagesByConversation] = useState<Record<number, MessageRead[] | null | undefined>>({})
  const [messageLoadErrorByConversation, setMessageLoadErrorByConversation] = useState<Record<number, boolean>>({})

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
      setMessagesByConversation({})
      setMessageLoadErrorByConversation({})
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

  useEffect(() => {
    if (shellState?.showWelcome) {
      setShowWelcome(true)
    }
  }, [shellState?.showWelcome])

  useEffect(() => {
    if (!conversations || conversations.length === 0) {
      setSelectedConversationId(null)
      return
    }

    setSelectedConversationId((current) => {
      if (current !== null && conversations.some((conversation) => conversation.id === current)) {
        return current
      }

      return conversations[0]?.id ?? null
    })
  }, [conversations])

  const selectedConversation =
    conversations?.find((conversation) => conversation.id === selectedConversationId) ?? conversations?.[0] ?? null
  const selectedJob = selectedConversation ? latestJobsByConversation[selectedConversation.id] ?? null : null
  const selectedConversationJobState =
    selectedConversationId === null ? undefined : latestJobsByConversation[selectedConversationId]
  const selectedConversationListItem = selectedConversation
    ? buildConversationListItem({
        conversation: selectedConversation,
        latestJob: selectedJob,
      })
    : null
  const selectedConversationMessagesState =
    selectedConversationId === null ? undefined : messagesByConversation[selectedConversationId]
  const settingsFormState = useMemo(
    () => buildSettingsFormState(settings ?? []),
    [settings],
  )
  const filteredConversationItems = useMemo(() => {
    const normalizedSearch = conversationSearch.trim().toLowerCase()
    const items = (conversations ?? []).map((conversation) =>
      buildConversationListItem({
        conversation,
        latestJob: latestJobsByConversation[conversation.id] ?? null,
      }),
    )

    if (!normalizedSearch) {
      return items
    }

    return items.filter((item) =>
      [item.title, item.secondaryText, item.statusLabel].some((value) => value.toLowerCase().includes(normalizedSearch)),
    )
  }, [conversationSearch, conversations, latestJobsByConversation])
  const selectedMessageModels = useMemo(
    () => (selectedConversationMessagesState ?? []).map((message) => buildMessageBubbleModel(message)),
    [selectedConversationMessagesState],
  )

  useEffect(() => {
    if (state.phase !== 'ready' || selectedConversationId === null) {
      return
    }

    if (latestJobsByConversation[selectedConversationId] !== undefined) {
      return
    }

    let cancelled = false

    const loadLatestJob = async () => {
      try {
        const jobs = await listConversationJobs(selectedConversationId, 1)
        if (cancelled) {
          return
        }

        setLatestJobsByConversation((current) => ({
          ...current,
          [selectedConversationId]: jobs[0] ?? null,
        }))
      } catch {
        if (cancelled) {
          return
        }

        setLatestJobsByConversation((current) => ({
          ...current,
          [selectedConversationId]: null,
        }))
      }
    }

    void loadLatestJob()

    return () => {
      cancelled = true
    }
  }, [selectedConversationId, selectedConversationJobState, state.phase])

  useEffect(() => {
    if (state.phase !== 'ready' || selectedConversationId === null) {
      return
    }

    if (selectedConversationMessagesState !== undefined) {
      return
    }

    let cancelled = false

    const loadMessages = async () => {
      try {
        const messages = await listMessages(selectedConversationId, { order: 'asc' })
        if (cancelled) {
          return
        }

        setMessagesByConversation((current) => ({
          ...current,
          [selectedConversationId]: messages,
        }))
        setMessageLoadErrorByConversation((current) => ({
          ...current,
          [selectedConversationId]: false,
        }))
      } catch {
        if (cancelled) {
          return
        }

        setMessagesByConversation((current) => ({
          ...current,
          [selectedConversationId]: null,
        }))
        setMessageLoadErrorByConversation((current) => ({
          ...current,
          [selectedConversationId]: true,
        }))
      }
    }

    void loadMessages()

    return () => {
      cancelled = true
    }
  }, [selectedConversationId, selectedConversationMessagesState, state.phase])

  useEffect(() => {
    if (state.phase !== 'ready' || selectedConversationId === null || !isPollingJob(selectedJob)) {
      return
    }

    let cancelled = false
    let timeoutId: number | null = null

    const pollLatestJob = async () => {
      try {
        const nextJob = await readJob(selectedJob.id)
        if (cancelled) {
          return
        }

        setLatestJobsByConversation((current) => ({
          ...current,
          [selectedConversationId]: nextJob,
        }))

        if (!isPollingJob(nextJob)) {
          return
        }

        timeoutId = window.setTimeout(() => {
          void pollLatestJob()
        }, 1500)
      } catch {
        // 保留当前最新状态，下次切换会话或重新触发分析时再继续轮询。
      }
    }

    timeoutId = window.setTimeout(() => {
      void pollLatestJob()
    }, 1500)

    return () => {
      cancelled = true
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [selectedConversationId, selectedJob?.id, selectedJob?.status, state.phase])

  const upsertSettings = (entries: SettingRead[], updates: SettingRead[]) => {
    const next = new Map(entries.map((entry) => [entry.setting_key, entry]))

    for (const update of updates) {
      next.set(update.setting_key, update)
    }

    return Array.from(next.values())
  }

  const handleSaveSettings = async (formState: SettingsFormState) => {
    setSettingsSavePending(true)
    setSettingsError(null)

    try {
      const updates = await Promise.all([
        writeSetting({ setting_key: 'llm.base_url', setting_value: formState.baseUrl.trim(), is_secret: false }),
        writeSetting({ setting_key: 'llm.api_key', setting_value: formState.apiKey.trim(), is_secret: true }),
        writeSetting({ setting_key: 'llm.chat_model', setting_value: formState.chatModel.trim(), is_secret: false }),
      ])

      setSettings((current) => upsertSettings(current ?? [], updates))
      setShowSettings(false)
      if ((conversations?.length ?? 0) > 0) {
        setShowWelcome(false)
      }
    } catch (error) {
      setSettingsError(error instanceof Error ? error.message : '保存设置失败')
    } finally {
      setSettingsSavePending(false)
    }
  }

  const handleImportConversation = async ({ filePath, selfDisplayName }: { filePath: string; selfDisplayName: string }) => {
    setImportPending(true)
    setImportError(null)

    try {
      if (!filePath.trim()) {
        throw new Error('请先选择导出文件')
      }

      if (!selfDisplayName.trim()) {
        throw new Error('请填写你的显示名')
      }

      const importFile = await readImportFile()
      if (!importFile) {
        throw new Error('当前桌面环境无法读取导出文件内容')
      }

      const response = await importConversation({
        file: createImportFileBlob(importFile),
        fileName: importFile.fileName,
        selfDisplayName: selfDisplayName.trim(),
      })

      setConversations((current) => {
        const existing = current ?? []
        const withoutDuplicate = existing.filter((item) => item.id !== response.conversation.id)
        return [response.conversation, ...withoutDuplicate]
      })
      setSelectedConversationId(response.conversation.id)
      setLatestJobsByConversation((current) => ({
        ...current,
        [response.conversation.id]: response.job,
      }))
      setMessagesByConversation((current) => ({
        ...current,
        [response.conversation.id]: undefined,
      }))
      setShowImportDialog(false)
      setShowWelcome(false)
    } catch (error) {
      setImportError(error instanceof Error ? error.message : '导入会话失败')
    } finally {
      setImportPending(false)
    }
  }

  const listEmptyMessage =
    hydrationStatus === 'loading'
      ? '正在读取会话…'
      : hydrationStatus === 'error'
        ? '会话或设置数据读取失败，当前仅保留桌面壳层。'
        : filteredConversationItems.length === 0 && (conversations?.length ?? 0) > 0
          ? '没有匹配的会话。'
          : '还没有已导入会话，请先导入聊天记录。'

  if (state.phase !== 'ready') {
    return <BootScreen label={label} detail={state.detail} />
  }

  return (
    <>
      <AppShell
        sidebar={<SidebarNav />}
        listPane={
          <ConversationListPane
            items={hydrationStatus === 'ready' ? filteredConversationItems : []}
            selectedConversationId={selectedConversationId}
            searchValue={conversationSearch}
            emptyMessage={listEmptyMessage}
            onSearchChange={setConversationSearch}
            onImportConversation={() => {
              setImportError(null)
              setShowImportDialog(true)
            }}
            onOpenSettings={() => setShowSettings(true)}
            onSelectConversation={setSelectedConversationId}
          />
        }
        chatPane={
          <ChatPane
            title={hydrationStatus === 'ready' ? selectedConversationListItem?.title : undefined}
            subtitle={selectedConversationListItem?.secondaryText}
            status={selectedJob?.status}
            progressPercent={selectedJob?.progress_percent}
            messages={selectedMessageModels}
            loading={hydrationStatus === 'loading' || (selectedConversationId !== null && selectedConversationMessagesState === undefined)}
            error={hydrationStatus === 'error' || (selectedConversationId !== null && messageLoadErrorByConversation[selectedConversationId] === true)}
            emptyVariant={shellState?.showWelcome ? 'welcome' : 'empty'}
          />
        }
      />
      <WelcomeModal
        open={showWelcome}
        onConfigureModel={() => {
          setShowWelcome(false)
          setShowSettings(true)
        }}
        onImportConversation={() => {
          setShowWelcome(false)
          setShowImportDialog(true)
        }}
        onClose={() => setShowWelcome(false)}
      />
      <SettingsDrawer
        open={showSettings}
        initialState={settingsFormState}
        pending={settingsSavePending}
        errorMessage={settingsError}
        onClose={() => setShowSettings(false)}
        onSave={handleSaveSettings}
      />
      <ImportDialog
        open={showImportDialog}
        pending={importPending}
        errorMessage={importError}
        onClose={() => setShowImportDialog(false)}
        onSubmit={handleImportConversation}
      />
    </>
  )
}
