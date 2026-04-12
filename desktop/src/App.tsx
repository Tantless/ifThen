import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react'
import { BootScreen } from './components/BootScreen'
import { WelcomeModal } from './components/WelcomeModal'
import { SettingsDrawer } from './components/SettingsDrawer'
import { ImportDialog } from './components/ImportDialog'
import { SelfAvatarDialog } from './components/SelfAvatarDialog'
import { AnalysisInspector, type AnalysisInspectorTab } from './components/AnalysisInspector'
import { ChatHistoryDialog } from './components/ChatHistoryDialog'
import { FrontAppShell } from './frontui/AppShell'
import { FrontSidebar } from './frontui/Sidebar'
import { FrontChatList } from './frontui/ChatList'
import { FrontChatWindow } from './frontui/ChatWindow'
import { WindowTitleBar } from './frontui/WindowTitleBar'
import {
  FRONTUI_SELF_AVATAR,
  FRONTUI_PLACEHOLDER_AVATAR,
  MOCK_CONTACTS_TAB_ITEMS,
  MOCK_FILES_TAB_ITEMS,
} from './frontui/mockState'
import type { FrontChatMessage, FrontSidebarTab } from './frontui/types'
import { decideAppShellState, resolveShellHydrationStatus } from './lib/bootstrap'
import {
  createImportFileBlob,
  getBootLabel,
  readDesktopServiceState,
  readImportFile,
  type BootState,
} from './lib/desktop'
import {
  closeDesktopWindow,
  getDesktopWindowState,
  minimizeDesktopWindow,
  toggleDesktopWindowMaximize,
} from './lib/windowControls'
import {
  buildSettingsFormState,
  type SettingsFormState,
} from './lib/adapters'
import { resolveJobProgress } from './lib/analysisProgress'
import {
  buildFrontChatItem,
  buildFrontChatMessagesFromSimulation,
  buildFrontChatWindowState,
  formatChatTimestampLabel,
} from './lib/frontUiAdapters'
import { resolveSimulationPendingStageLabel } from './lib/simulationPending'
import {
  deleteConversation,
  importConversation,
  listConversations,
  listMessages,
  listTopics,
  readProfile,
  readSnapshot,
  startAnalysis,
} from './lib/services/conversationService'
import { listConversationJobs, readJob } from './lib/services/jobService'
import { readSettings, writeSetting } from './lib/services/settingsService'
import { createSimulation, listConversationSimulationJobs, readSimulation } from './lib/services/simulationService'
import {
  isRewriteRequestCurrent,
  resolveInspectorSnapshotAt,
  shouldStartLatestJobLoad,
  type ChatViewState,
  type LatestJobLoadState,
  type MessageLoadState,
  type RewriteRequestSnapshot,
} from './lib/chatState'
import type {
  ConversationRead,
  JobRead,
  MessageRead,
  PersonaProfileRead,
  SettingRead,
  SnapshotRead,
  SimulationJobRead,
  SimulationRead,
  TopicRead,
} from './types/api'

type RewriteDraft = {
  conversationId: number
  targetMessageId: number
  originalMessage: string
  targetMessageTimestamp: string
  replacementContent: string
  simulationJobId: number | null
  status: 'editing' | 'pending' | 'completed'
  simulation: SimulationRead | null
  errorMessage: string | null
  pendingStageLabel: string | null
}

function isPollingJob(job: JobRead | null | undefined): job is JobRead {
  return job?.status === 'running' || job?.status === 'queued'
}

function isPollingSimulationJob(job: SimulationJobRead | null | undefined): boolean {
  return job?.status === 'running' || job?.status === 'queued'
}

function resolveConversationStatusFromJob(currentStatus: string, job: JobRead): string {
  if (job.status === 'failed') {
    return 'failed'
  }

  if (job.status === 'running') {
    return currentStatus === 'imported' ? 'imported' : 'analyzing'
  }

  if (job.status === 'queued') {
    return currentStatus === 'imported' ? 'imported' : 'queued'
  }

  if (job.status === 'completed') {
    return currentStatus === 'imported' ? 'imported' : 'ready'
  }

  return currentStatus
}

function resolveSettingValue(entries: SettingRead[] | null, key: string): string {
  return entries?.find((entry) => entry.setting_key === key)?.setting_value.trim() ?? ''
}

const MESSAGE_LOAD_RETRY_INTERVAL_MS = 1500
const MESSAGE_LOAD_TIMEOUT_MS = 10_000
const INITIAL_MESSAGE_PAGE_SIZE = 80
const OLDER_MESSAGE_PAGE_SIZE = 50
const CHAT_HISTORY_INITIAL_PAGE_SIZE = 20
const CHAT_HISTORY_LOAD_MORE_PAGE_SIZE = 10

type MessagePaginationState = {
  hasOlder: boolean
  loadingOlder: boolean
}

export default function App() {
  const [activeTab, setActiveTab] = useState<FrontSidebarTab>('chat')
  const [chatViewState, setChatViewState] = useState<ChatViewState>({ mode: 'history' })
  const [rewriteDraft, setRewriteDraft] = useState<RewriteDraft | null>(null)
  const [inspectorOpen, setInspectorOpen] = useState(false)
  const [inspectorTab, setInspectorTab] = useState<AnalysisInspectorTab>('topics')
  const [inspectorLoadingByTab, setInspectorLoadingByTab] = useState<Record<AnalysisInspectorTab, boolean>>({
    topics: false,
    profile: false,
    snapshot: false,
  })
  const [inspectorError, setInspectorError] = useState<string | null>(null)
  const [inspectorTopics, setInspectorTopics] = useState<TopicRead[]>([])
  const [inspectorProfile, setInspectorProfile] = useState<PersonaProfileRead[]>([])
  const [inspectorSnapshot, setInspectorSnapshot] = useState<SnapshotRead | null>(null)
  const [isDesktopWindowMaximized, setIsDesktopWindowMaximized] = useState(false)
  const [state, setState] = useState<BootState>({ phase: 'booting' })
  const [settings, setSettings] = useState<SettingRead[] | null>(null)
  const [conversations, setConversations] = useState<ConversationRead[] | null>(null)
  const [shellLoadError, setShellLoadError] = useState(false)
  const [showWelcome, setShowWelcome] = useState(false)
  const [showSelfAvatarDialog, setShowSelfAvatarDialog] = useState(false)
  const [showSettings, setShowSettings] = useState(false)
  const [showImportDialog, setShowImportDialog] = useState(false)
  const [showChatHistoryDialog, setShowChatHistoryDialog] = useState(false)
  const [selfAvatarSavePending, setSelfAvatarSavePending] = useState(false)
  const [selfAvatarError, setSelfAvatarError] = useState<string | null>(null)
  const [settingsSavePending, setSettingsSavePending] = useState(false)
  const [settingsError, setSettingsError] = useState<string | null>(null)
  const [importPending, setImportPending] = useState(false)
  const [importError, setImportError] = useState<string | null>(null)
  const [startAnalysisPending, setStartAnalysisPending] = useState(false)
  const [selectedConversationId, setSelectedConversationId] = useState<number | null>(null)
  const [conversationSearch, setConversationSearch] = useState('')
  const [latestJobsByConversation, setLatestJobsByConversation] = useState<Record<number, JobRead | null>>({})
  const [latestJobLoadStateByConversation, setLatestJobLoadStateByConversation] = useState<Record<number, LatestJobLoadState>>({})
  const [messagesByConversation, setMessagesByConversation] = useState<Record<number, MessageRead[] | null | undefined>>({})
  const [messagePaginationByConversation, setMessagePaginationByConversation] = useState<Record<number, MessagePaginationState>>({})
  const [messageLoadStateByConversation, setMessageLoadStateByConversation] = useState<Record<number, MessageLoadState>>({})
  const [messageLoadErrorByConversation, setMessageLoadErrorByConversation] = useState<Record<number, boolean>>({})
  const [mockMessagesByConversation, setMockMessagesByConversation] = useState<Record<number, FrontChatMessage[]>>({})
  const [chatHistoryKeyword, setChatHistoryKeyword] = useState('')
  const [chatHistoryDate, setChatHistoryDate] = useState('')
  const [chatHistoryResults, setChatHistoryResults] = useState<MessageRead[]>([])
  const [chatHistoryLoading, setChatHistoryLoading] = useState(false)
  const [chatHistoryLoadingMore, setChatHistoryLoadingMore] = useState(false)
  const [chatHistoryError, setChatHistoryError] = useState<string | null>(null)
  const [chatHistoryHasMore, setChatHistoryHasMore] = useState(false)
  const [chatHistoryLocatePendingId, setChatHistoryLocatePendingId] = useState<number | null>(null)
  const [jumpToMessageRequest, setJumpToMessageRequest] = useState<{ messageId: number; requestKey: number } | null>(null)
  const rewriteRequestCounterRef = useRef(0)
  const activeRewriteRequestRef = useRef<RewriteRequestSnapshot | null>(null)
  const selectedConversationIdRef = useRef<number | null>(null)
  const rewriteDraftRef = useRef<RewriteDraft | null>(null)
  const windowStateRequestIdRef = useRef(0)
  const deferredChatHistoryKeyword = useDeferredValue(chatHistoryKeyword.trim())
  const deferredChatHistoryDate = useDeferredValue(chatHistoryDate)

  useEffect(() => {
    selectedConversationIdRef.current = selectedConversationId
  }, [selectedConversationId])

  useEffect(() => {
    rewriteDraftRef.current = rewriteDraft
  }, [rewriteDraft])

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
      setLatestJobLoadStateByConversation({})
      setMessagesByConversation({})
      setMessagePaginationByConversation({})
      setMessageLoadStateByConversation({})
      setMessageLoadErrorByConversation({})
      setChatViewState({ mode: 'history' })
      setRewriteDraft(null)
      setInspectorOpen(false)
      setInspectorTab('topics')
      setInspectorLoadingByTab({ topics: false, profile: false, snapshot: false })
      setInspectorError(null)
      setInspectorTopics([])
      setInspectorProfile([])
      setInspectorSnapshot(null)
      setActiveTab('chat')
      setMockMessagesByConversation({})
      activeRewriteRequestRef.current = null
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

  useEffect(() => {
    if (state.phase !== 'ready') {
      return
    }

    let cancelled = false

    const hydrateDesktopWindowState = async () => {
      const requestId = windowStateRequestIdRef.current + 1
      windowStateRequestIdRef.current = requestId

      try {
        const nextWindowState = await getDesktopWindowState()

        if (!cancelled && windowStateRequestIdRef.current === requestId) {
          setIsDesktopWindowMaximized(nextWindowState.isMaximized)
        }
      } catch {
        if (!cancelled && windowStateRequestIdRef.current === requestId) {
          setIsDesktopWindowMaximized(false)
        }
      }
    }

    void hydrateDesktopWindowState()

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
      setChatViewState({ mode: 'history' })
      setRewriteDraft(null)
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
  const selectedConversationJobState = selectedConversationId === null ? undefined : latestJobLoadStateByConversation[selectedConversationId]
  const selectedConversationMessagesState =
    selectedConversationId === null ? undefined : messagesByConversation[selectedConversationId]
  const selectedConversationPaginationState =
    selectedConversationId === null ? undefined : messagePaginationByConversation[selectedConversationId]
  const selectedConversationMessageLoadState =
    selectedConversationId === null ? undefined : messageLoadStateByConversation[selectedConversationId]
  const settingsFormState = useMemo(() => buildSettingsFormState(settings ?? []), [settings])
  const selfAvatarUrl = useMemo(
    () => resolveSettingValue(settings, 'profile.self_avatar_url') || FRONTUI_SELF_AVATAR,
    [settings],
  )
  const resolveConversationAvatarUrl = (conversationId: number) =>
    resolveSettingValue(settings, `conversation.${conversationId}.other_avatar_url`) || FRONTUI_PLACEHOLDER_AVATAR
  const filteredConversationItems = useMemo(() => {
    const normalizedSearch = conversationSearch.trim().toLowerCase()
    const items = (conversations ?? []).map((conversation) =>
      buildFrontChatItem({
        conversation,
        otherAvatarUrl: resolveConversationAvatarUrl(conversation.id),
        latestJob: latestJobsByConversation[conversation.id] ?? null,
        isActive: conversation.id === selectedConversationId,
      }),
    )

    if (!normalizedSearch) {
      return items
    }

    return items.filter((item) =>
      [item.displayName, item.previewText, item.timestampLabel].some((value) =>
        value.toLowerCase().includes(normalizedSearch),
      ),
    )
  }, [conversationSearch, conversations, latestJobsByConversation, selectedConversationId, settings])

  const contactsListItems = useMemo(() => {
    if (!conversations || conversations.length === 0) {
      return []
    }

    return conversations.map((conversation) => ({
      id: `contact-${conversation.id}`,
      conversationId: conversation.id,
      displayName: conversation.other_display_name || '未命名联系人',
      avatarUrl: resolveConversationAvatarUrl(conversation.id),
      previewText: `共 ${conversation.id} 条聊天记录`,
      timestampLabel: '',
      progress: null,
      unreadCount: 0,
      active: false,
      source: 'real' as const,
    }))
  }, [conversations, settings])

  const rewriteGeneratedMessages = useMemo(() => {
    if (
      !rewriteDraft ||
      rewriteDraft.status !== 'completed' ||
      !rewriteDraft.simulation ||
      !selectedConversation ||
      rewriteDraft.conversationId !== selectedConversation.id
    ) {
      return []
    }

    return buildFrontChatMessagesFromSimulation({
      simulation: rewriteDraft.simulation,
      selfDisplayName: selectedConversation.self_display_name,
      otherDisplayName: selectedConversation.other_display_name,
      selfAvatarUrl,
      otherAvatarUrl: resolveConversationAvatarUrl(selectedConversation.id),
      timestampRaw: rewriteDraft.targetMessageTimestamp,
    })
  }, [rewriteDraft, selectedConversation, selfAvatarUrl, settings])
  const selectedMessageModels = useMemo(() => {
    const realState = buildFrontChatWindowState({
      selectedConversation: activeTab === 'chat' ? selectedConversation : null,
      selfAvatarUrl,
      otherAvatarUrl: selectedConversation ? resolveConversationAvatarUrl(selectedConversation.id) : FRONTUI_PLACEHOLDER_AVATAR,
      messages: selectedConversationMessagesState ?? [],
    })

    if (realState.mode !== 'conversation' || selectedConversationId === null) {
      return realState
    }

    let messages = [...realState.messages]

    if (rewriteDraft && rewriteDraft.conversationId === selectedConversationId) {
      const targetIndex = messages.findIndex((message) => message.messageId === rewriteDraft.targetMessageId)

      if (targetIndex >= 0) {
        messages[targetIndex] = {
          ...messages[targetIndex],
          text: rewriteDraft.replacementContent,
          bubbleTone: 'rewrite-target',
        }

        if (rewriteDraft.status === 'pending' || rewriteDraft.status === 'completed') {
          if (rewriteDraft.status === 'pending') {
            messages = messages.map((message, index) =>
              index > targetIndex
                ? {
                    ...message,
                    ghosted: true,
                  }
                : message,
            )
          } else {
            messages = messages.slice(0, targetIndex + 1)
          }
        }
      }
    }

    return {
      ...realState,
      messages: [...messages, ...(mockMessagesByConversation[selectedConversationId] ?? [])],
    }
  }, [
    activeTab,
    mockMessagesByConversation,
    rewriteDraft,
    selectedConversation,
    selectedConversationId,
    selectedConversationMessagesState,
    selfAvatarUrl,
    settings,
  ])
  const analysisCompleted = selectedConversation?.status === 'ready' && selectedJob?.status === 'completed'
  const selectedConversationProgress = useMemo(() => {
    if (selectedConversation?.status === 'imported' && selectedJob?.status === 'completed') {
      return null
    }

    return resolveJobProgress(selectedJob)
  }, [selectedConversation?.status, selectedJob])
  const snapshotAt = useMemo(
    () =>
      resolveInspectorSnapshotAt(
        chatViewState,
        (selectedConversationMessagesState ?? []).map((message) => ({
          id: message.id,
          timestamp: message.timestamp,
        })),
      ),
    [chatViewState, selectedConversationMessagesState],
  )

  useEffect(() => {
    if (activeTab === 'chat') {
      return
    }

    setInspectorOpen(false)
    setRewriteDraft(null)
    activeRewriteRequestRef.current = null
    setChatViewState({ mode: 'history' })
    setShowChatHistoryDialog(false)
  }, [activeTab])

  useEffect(() => {
    setChatViewState({ mode: 'history' })
    setRewriteDraft(null)
    setInspectorOpen(false)
    setInspectorTab('topics')
    setInspectorLoadingByTab({ topics: false, profile: false, snapshot: false })
    setInspectorError(null)
    setInspectorTopics([])
    setInspectorProfile([])
    setInspectorSnapshot(null)
    activeRewriteRequestRef.current = null
    setShowChatHistoryDialog(false)
    setChatHistoryKeyword('')
    setChatHistoryDate('')
    setChatHistoryResults([])
    setChatHistoryError(null)
    setChatHistoryLoading(false)
    setChatHistoryLoadingMore(false)
    setChatHistoryHasMore(false)
    setChatHistoryLocatePendingId(null)
    setJumpToMessageRequest(null)
  }, [selectedConversationId])

  useEffect(() => {
    if (!analysisCompleted) {
      setInspectorOpen(false)
      setRewriteDraft(null)
      activeRewriteRequestRef.current = null
    }
  }, [analysisCompleted])

  useEffect(() => {
    if (showChatHistoryDialog) {
      return
    }

    setChatHistoryKeyword('')
    setChatHistoryDate('')
    setChatHistoryResults([])
    setChatHistoryError(null)
    setChatHistoryLoading(false)
    setChatHistoryLoadingMore(false)
    setChatHistoryHasMore(false)
    setChatHistoryLocatePendingId(null)
  }, [showChatHistoryDialog])

  useEffect(() => {
    if (state.phase !== 'ready' || selectedConversationId === null) {
      return
    }

    const conversationId = selectedConversationId
    const currentLoadState = selectedConversationJobState
    const now = Date.now()

    if (!shouldStartLatestJobLoad(currentLoadState, now)) {
      if (currentLoadState?.status === 'retry_wait') {
        const delay = Math.max(0, currentLoadState.retryAt - now)
        const timeoutId = window.setTimeout(() => {
          setLatestJobLoadStateByConversation((current) => {
            if (current[conversationId]?.status !== 'retry_wait') {
              return current
            }

            return {
              ...current,
              [conversationId]: { status: 'idle' },
            }
          })
        }, delay)

        return () => {
          window.clearTimeout(timeoutId)
        }
      }

      return
    }

    const loadLatestJob = async () => {
      setLatestJobLoadStateByConversation((current) => ({
        ...current,
        [conversationId]: { status: 'loading' },
      }))

      try {
        const jobs = await listConversationJobs(conversationId, 1)
        if (selectedConversationIdRef.current !== conversationId) {
          return
        }

        setLatestJobsByConversation((current) => ({
          ...current,
          [conversationId]: jobs[0] ?? null,
        }))
        setLatestJobLoadStateByConversation((current) => ({
          ...current,
          [conversationId]: { status: 'loaded' },
        }))
      } catch {
        if (selectedConversationIdRef.current !== conversationId) {
          return
        }

        setLatestJobLoadStateByConversation((current) => ({
          ...current,
          [conversationId]: {
            status: 'retry_wait',
            retryAt: Date.now() + 1500,
          },
        }))
      }
    }

    void loadLatestJob()
  }, [selectedConversationId, selectedConversationJobState, state.phase])

  useEffect(() => {
    if (state.phase !== 'ready' || selectedConversationId === null) {
      return
    }

    if (selectedConversationMessageLoadState?.status === 'loaded' || selectedConversationMessageLoadState?.status === 'failed') {
      return
    }

    const now = Date.now()

    if (
      selectedConversationMessageLoadState?.status === 'retry_wait' &&
      selectedConversationMessageLoadState.retryAt > now
    ) {
      const delay = Math.max(0, selectedConversationMessageLoadState.retryAt - now)
      const timeoutId = window.setTimeout(() => {
        setMessageLoadStateByConversation((current) => {
          const currentState = current[selectedConversationId]
          if (!currentState || currentState.status !== 'retry_wait') {
            return current
          }

          return {
            ...current,
            [selectedConversationId]: { status: 'idle' },
          }
        })
      }, delay)

      return () => {
        window.clearTimeout(timeoutId)
      }
    }

    let cancelled = false
    const startedAt =
      selectedConversationMessageLoadState?.status === 'retry_wait'
        ? selectedConversationMessageLoadState.startedAt
        : now

    const loadMessages = async () => {
      try {
        const messages = await listMessages(selectedConversationId, {
          order: 'desc',
          limit: INITIAL_MESSAGE_PAGE_SIZE,
        })
        if (cancelled) {
          return
        }

        const normalizedMessages = [...messages].reverse()

        setMessagesByConversation((current) => ({
          ...current,
          [selectedConversationId]: normalizedMessages,
        }))
        setMessagePaginationByConversation((current) => ({
          ...current,
          [selectedConversationId]: {
            hasOlder: messages.length === INITIAL_MESSAGE_PAGE_SIZE,
            loadingOlder: false,
          },
        }))

        const timedOut = Date.now() - startedAt >= MESSAGE_LOAD_TIMEOUT_MS
        const shouldRetry =
          normalizedMessages.length === 0 &&
          !timedOut &&
          (!selectedJob || isPollingJob(selectedJob))

        if (shouldRetry) {
          setMessageLoadStateByConversation((current) => ({
            ...current,
            [selectedConversationId]: {
              status: 'retry_wait',
              startedAt,
              retryAt: Date.now() + MESSAGE_LOAD_RETRY_INTERVAL_MS,
            },
          }))
          setMessageLoadErrorByConversation((current) => ({
            ...current,
            [selectedConversationId]: false,
          }))
          return
        }

        if (normalizedMessages.length === 0 && timedOut && (!selectedJob || isPollingJob(selectedJob))) {
          setMessageLoadStateByConversation((current) => ({
            ...current,
            [selectedConversationId]: { status: 'failed' },
          }))
          setMessageLoadErrorByConversation((current) => ({
            ...current,
            [selectedConversationId]: true,
          }))
          return
        }

        setMessageLoadStateByConversation((current) => ({
          ...current,
          [selectedConversationId]: { status: 'loaded' },
        }))
        setMessageLoadErrorByConversation((current) => ({
          ...current,
          [selectedConversationId]: false,
        }))
      } catch {
        if (cancelled) {
          return
        }

        const timedOut = Date.now() - startedAt >= MESSAGE_LOAD_TIMEOUT_MS

        if (!timedOut) {
          setMessageLoadStateByConversation((current) => ({
            ...current,
            [selectedConversationId]: {
              status: 'retry_wait',
              startedAt,
              retryAt: Date.now() + MESSAGE_LOAD_RETRY_INTERVAL_MS,
            },
          }))
          return
        }

        setMessageLoadStateByConversation((current) => ({
          ...current,
          [selectedConversationId]: { status: 'failed' },
        }))
        setMessagesByConversation((current) => ({
          ...current,
          [selectedConversationId]: null,
        }))
        setMessagePaginationByConversation((current) => ({
          ...current,
          [selectedConversationId]: {
            hasOlder: false,
            loadingOlder: false,
          },
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
  }, [
    selectedConversationId,
    selectedConversationMessageLoadState,
    selectedJob,
    state.phase,
  ])

  const chatHistoryUsesFilteredOrder = deferredChatHistoryKeyword.length > 0 || deferredChatHistoryDate.length > 0
  const chatHistoryOrder: 'asc' | 'desc' = chatHistoryUsesFilteredOrder ? 'asc' : 'desc'

  useEffect(() => {
    if (state.phase !== 'ready' || activeTab !== 'chat' || selectedConversationId === null || !showChatHistoryDialog) {
      return
    }

    let cancelled = false

    const loadChatHistory = async () => {
      setChatHistoryLoading(true)
      setChatHistoryLoadingMore(false)
      setChatHistoryError(null)

      try {
        const results = await listMessages(selectedConversationId, {
          limit: CHAT_HISTORY_INITIAL_PAGE_SIZE,
          order: chatHistoryOrder,
          keyword: deferredChatHistoryKeyword || undefined,
          date: deferredChatHistoryDate || undefined,
        })

        if (cancelled) {
          return
        }

        setChatHistoryResults(results)
        setChatHistoryHasMore(results.length === CHAT_HISTORY_INITIAL_PAGE_SIZE)
      } catch (error) {
        if (cancelled) {
          return
        }

        setChatHistoryResults([])
        setChatHistoryHasMore(false)
        setChatHistoryError(error instanceof Error ? error.message : '加载聊天记录失败')
      } finally {
        if (!cancelled) {
          setChatHistoryLoading(false)
        }
      }
    }

    void loadChatHistory()

    return () => {
      cancelled = true
    }
  }, [
    activeTab,
    chatHistoryOrder,
    deferredChatHistoryDate,
    deferredChatHistoryKeyword,
    selectedConversationId,
    showChatHistoryDialog,
    state.phase,
  ])

  const handleLoadOlderMessages = async () => {
    if (state.phase !== 'ready' || selectedConversationId === null) {
      return
    }

    const currentMessages = messagesByConversation[selectedConversationId]
    const paginationState = messagePaginationByConversation[selectedConversationId]

    if (
      !currentMessages ||
      currentMessages.length === 0 ||
      !paginationState?.hasOlder ||
      paginationState.loadingOlder
    ) {
      return
    }

    const oldestSequence = currentMessages[0]?.sequence_no
    if (!oldestSequence) {
      return
    }

    setMessagePaginationByConversation((current) => ({
      ...current,
      [selectedConversationId]: {
        hasOlder: current[selectedConversationId]?.hasOlder ?? false,
        loadingOlder: true,
      },
    }))

    try {
      const olderMessages = await listMessages(selectedConversationId, {
        before: oldestSequence,
        order: 'desc',
        limit: OLDER_MESSAGE_PAGE_SIZE,
      })
      const normalizedOlderMessages = [...olderMessages].reverse()

      setMessagesByConversation((current) => {
        const existingMessages = current[selectedConversationId] ?? []
        const existingMessageIds = new Set(existingMessages.map((message) => message.id))
        const uniqueOlderMessages = normalizedOlderMessages.filter((message) => !existingMessageIds.has(message.id))

        return {
          ...current,
          [selectedConversationId]: [...uniqueOlderMessages, ...existingMessages],
        }
      })
      setMessagePaginationByConversation((current) => ({
        ...current,
        [selectedConversationId]: {
          hasOlder: olderMessages.length === OLDER_MESSAGE_PAGE_SIZE,
          loadingOlder: false,
        },
      }))
    } catch {
      setMessagePaginationByConversation((current) => ({
        ...current,
        [selectedConversationId]: {
          hasOlder: current[selectedConversationId]?.hasOlder ?? false,
          loadingOlder: false,
        },
      }))
    }
  }

  const handleLoadMoreChatHistory = async () => {
    if (
      state.phase !== 'ready' ||
      activeTab !== 'chat' ||
      selectedConversationId === null ||
      chatHistoryLoading ||
      chatHistoryLoadingMore ||
      !chatHistoryHasMore ||
      chatHistoryResults.length === 0
    ) {
      return
    }

    const cursorSequence = chatHistoryResults[chatHistoryResults.length - 1]?.sequence_no
    if (!cursorSequence) {
      return
    }

    setChatHistoryLoadingMore(true)

    try {
      const nextResults = await listMessages(selectedConversationId, {
        limit: CHAT_HISTORY_LOAD_MORE_PAGE_SIZE,
        order: chatHistoryOrder,
        keyword: deferredChatHistoryKeyword || undefined,
        date: deferredChatHistoryDate || undefined,
        ...(chatHistoryOrder === 'asc' ? { after: cursorSequence } : { before: cursorSequence }),
      })

      setChatHistoryResults((current) => {
        const existingIds = new Set(current.map((message) => message.id))
        const uniqueResults = nextResults.filter((message) => !existingIds.has(message.id))
        return [...current, ...uniqueResults]
      })
      setChatHistoryHasMore(nextResults.length === CHAT_HISTORY_LOAD_MORE_PAGE_SIZE)
    } catch (error) {
      setChatHistoryError(error instanceof Error ? error.message : '加载更多聊天记录失败')
    } finally {
      setChatHistoryLoadingMore(false)
    }
  }

  const handleLocateChatHistoryMessage = async (targetMessage: MessageRead) => {
    if (state.phase !== 'ready' || selectedConversationId === null) {
      return
    }

    const conversationId = selectedConversationId
    setChatHistoryLocatePendingId(targetMessage.id)
    setChatHistoryError(null)

    try {
      let loadedMessages = messagesByConversation[conversationId] ?? []

      if (loadedMessages.length === 0) {
        const latestMessages = await listMessages(conversationId, {
          order: 'desc',
          limit: INITIAL_MESSAGE_PAGE_SIZE,
        })
        loadedMessages = [...latestMessages].reverse()
        setMessagesByConversation((current) => ({
          ...current,
          [conversationId]: loadedMessages,
        }))
        setMessagePaginationByConversation((current) => ({
          ...current,
          [conversationId]: {
            hasOlder: latestMessages.length === INITIAL_MESSAGE_PAGE_SIZE,
            loadingOlder: false,
          },
        }))
      }

      while (!loadedMessages.some((message) => message.id === targetMessage.id)) {
        const oldestSequence = loadedMessages[0]?.sequence_no

        if (!oldestSequence) {
          break
        }

        const olderMessages = await listMessages(conversationId, {
          before: oldestSequence,
          order: 'desc',
          limit: OLDER_MESSAGE_PAGE_SIZE,
        })
        const normalizedOlderMessages = [...olderMessages].reverse()

        if (normalizedOlderMessages.length === 0) {
          setMessagePaginationByConversation((current) => ({
            ...current,
            [conversationId]: {
              hasOlder: false,
              loadingOlder: false,
            },
          }))
          break
        }

        const existingMessageIds = new Set(loadedMessages.map((message) => message.id))
        const uniqueOlderMessages = normalizedOlderMessages.filter((message) => !existingMessageIds.has(message.id))
        loadedMessages = [...uniqueOlderMessages, ...loadedMessages]

        setMessagesByConversation((current) => ({
          ...current,
          [conversationId]: loadedMessages,
        }))
        setMessagePaginationByConversation((current) => ({
          ...current,
          [conversationId]: {
            hasOlder: olderMessages.length === OLDER_MESSAGE_PAGE_SIZE,
            loadingOlder: false,
          },
        }))

        if (olderMessages.length < OLDER_MESSAGE_PAGE_SIZE) {
          break
        }
      }

      if (!loadedMessages.some((message) => message.id === targetMessage.id)) {
        setChatHistoryError('未能定位到这条消息')
        return
      }

      setShowChatHistoryDialog(false)
      setJumpToMessageRequest((current) => ({
        messageId: targetMessage.id,
        requestKey: (current?.requestKey ?? 0) + 1,
      }))
    } catch (error) {
      setChatHistoryError(error instanceof Error ? error.message : '定位消息失败')
    } finally {
      setChatHistoryLocatePendingId(null)
    }
  }

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
        setConversations((current) => {
          if (!current) {
            return current
          }

          return current.map((conversation) =>
            conversation.id === selectedConversationId
              ? {
                  ...conversation,
                  status: resolveConversationStatusFromJob(conversation.status, nextJob),
                }
              : conversation,
          )
        })

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

  useEffect(() => {
    if (
      state.phase !== 'ready' ||
      selectedConversationId === null ||
      !rewriteDraft ||
      rewriteDraft.status !== 'pending' ||
      rewriteDraft.conversationId !== selectedConversationId ||
      rewriteDraft.simulationJobId === null
    ) {
      return
    }

    let cancelled = false
    let timeoutId: number | null = null
    const conversationId = selectedConversationId
    const simulationJobId = rewriteDraft.simulationJobId

    const scheduleRetry = () => {
      timeoutId = window.setTimeout(() => {
        void pollSimulationJob()
      }, 1500)
    }

    const pollSimulationJob = async () => {
      try {
        const jobs = await listConversationSimulationJobs(conversationId, 10)
        if (cancelled) {
          return
        }

        const currentDraft = rewriteDraftRef.current
        if (
          !currentDraft ||
          currentDraft.status !== 'pending' ||
          currentDraft.conversationId !== conversationId ||
          currentDraft.simulationJobId !== simulationJobId
        ) {
          return
        }

        const simulationJob = jobs.find((job) => job.id === simulationJobId)
        if (!simulationJob) {
          scheduleRetry()
          return
        }

        setRewriteDraft((current) =>
          current && current.simulationJobId === simulationJob.id
            ? simulationJob.status_message && simulationJob.status_message !== current.pendingStageLabel
              ? {
                  ...current,
                  pendingStageLabel: simulationJob.status_message,
                }
              : current
            : current,
        )

        if (isPollingSimulationJob(simulationJob)) {
          scheduleRetry()
          return
        }

        if (simulationJob.status === 'completed' && simulationJob.result_simulation_id !== null) {
          const simulation = await readSimulation(simulationJob.result_simulation_id)
          if (cancelled) {
            return
          }

          const nextDraft = rewriteDraftRef.current
          if (
            !nextDraft ||
            nextDraft.status !== 'pending' ||
            nextDraft.conversationId !== conversationId ||
            nextDraft.simulationJobId !== simulationJob.id
          ) {
            return
          }

          setChatViewState({ mode: 'history' })
          setRewriteDraft((current) =>
            current && current.simulationJobId === simulationJob.id
              ? {
                  ...current,
                  simulationJobId: null,
                  status: 'completed',
                  simulation,
                  errorMessage: null,
                  pendingStageLabel: null,
                }
              : current,
          )
          return
        }

        if (simulationJob.status === 'failed') {
          setRewriteDraft((current) =>
            current && current.simulationJobId === simulationJob.id
              ? {
                  ...current,
                  simulationJobId: null,
                  status: 'editing',
                  simulation: null,
                  errorMessage: simulationJob.error_message ?? '推演失败',
                  pendingStageLabel: null,
                }
              : current,
          )
          return
        }

        scheduleRetry()
      } catch {
        if (!cancelled) {
          scheduleRetry()
        }
      }
    }

    void pollSimulationJob()

    return () => {
      cancelled = true
      if (timeoutId !== null) {
        window.clearTimeout(timeoutId)
      }
    }
  }, [rewriteDraft?.conversationId, rewriteDraft?.simulationJobId, rewriteDraft?.status, selectedConversationId, state.phase])

  useEffect(() => {
    if (!inspectorOpen || !analysisCompleted || state.phase !== 'ready' || selectedConversationId === null) {
      return
    }

    let cancelled = false

    const loadInspector = async () => {
      setInspectorLoadingByTab((current) => ({
        ...current,
        [inspectorTab]: true,
      }))
      setInspectorError(null)

      if (inspectorTab === 'topics') {
        const result = await listTopics(selectedConversationId)
          .then((value) => ({ status: 'fulfilled' as const, value }))
          .catch(() => ({ status: 'rejected' as const }))

        if (cancelled) {
          return
        }

        setInspectorTopics(result.status === 'fulfilled' ? result.value : [])
        if (result.status === 'rejected') {
          setInspectorError('分析数据读取失败')
        }
      } else if (inspectorTab === 'profile') {
        const result = await readProfile(selectedConversationId)
          .then((value) => ({ status: 'fulfilled' as const, value }))
          .catch(() => ({ status: 'rejected' as const }))

        if (cancelled) {
          return
        }

        setInspectorProfile(result.status === 'fulfilled' ? result.value : [])
        if (result.status === 'rejected') {
          setInspectorError('分析数据读取失败')
        }
      } else {
        const result = await readSnapshot(selectedConversationId, snapshotAt ?? undefined)
          .then((value) => ({ status: 'fulfilled' as const, value }))
          .catch(() => ({ status: 'rejected' as const }))

        if (cancelled) {
          return
        }

        setInspectorSnapshot(result.status === 'fulfilled' ? result.value : null)
        if (result.status === 'rejected') {
          setInspectorError('分析数据读取失败')
        }
      }

      setInspectorLoadingByTab((current) => ({
        ...current,
        [inspectorTab]: false,
      }))
    }

    void loadInspector()

    return () => {
      cancelled = true
    }
  }, [analysisCompleted, inspectorOpen, inspectorTab, selectedConversationId, snapshotAt, state.phase])

  const upsertSettings = (entries: SettingRead[], updates: SettingRead[]) => {
    const next = new Map(entries.map((entry) => [entry.setting_key, entry]))

    for (const update of updates) {
      next.set(update.setting_key, update)
    }

    return Array.from(next.values())
  }

  const persistSelfAvatarSetting = async (avatarUrl: string) => {
    const savedAvatarUrl = resolveSettingValue(settings, 'profile.self_avatar_url')
    const normalizedAvatarUrl = avatarUrl.trim()

    if (!normalizedAvatarUrl || normalizedAvatarUrl === savedAvatarUrl) {
      return
    }

    const updatedSetting = await writeSetting({
      setting_key: 'profile.self_avatar_url',
      setting_value: normalizedAvatarUrl,
      is_secret: false,
    })

    setSettings((current) => upsertSettings(current ?? [], [updatedSetting]))
  }

  const handleSaveSettings = async (formState: SettingsFormState) => {
    setSettingsSavePending(true)
    setSettingsError(null)

    try {
      const updates = await Promise.all([
        writeSetting({ setting_key: 'llm.base_url', setting_value: formState.baseUrl.trim(), is_secret: false }),
        writeSetting({ setting_key: 'llm.api_key', setting_value: formState.apiKey.trim(), is_secret: true }),
        writeSetting({ setting_key: 'llm.chat_model', setting_value: formState.chatModel.trim(), is_secret: false }),
        writeSetting({
          setting_key: 'llm.simulation_base_url',
          setting_value: formState.simulationBaseUrl.trim(),
          is_secret: false,
        }),
        writeSetting({
          setting_key: 'llm.simulation_api_key',
          setting_value: formState.simulationApiKey.trim(),
          is_secret: true,
        }),
        writeSetting({ setting_key: 'llm.simulation_model', setting_value: formState.simulationModel.trim(), is_secret: false }),
        writeSetting({
          setting_key: 'simulation.default_mode',
          setting_value: formState.simulationMode,
          is_secret: false,
        }),
        writeSetting({
          setting_key: 'simulation.default_turn_count',
          setting_value: String(formState.simulationTurnCount),
          is_secret: false,
        }),
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

  const handleImportConversation = async ({
    filePath,
    selfDisplayName,
    autoAnalyze,
    otherAvatarUrl,
  }: {
    filePath: string
    selfDisplayName: string
    autoAnalyze: boolean
    otherAvatarUrl: string
  }) => {
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
        autoAnalyze,
      })
      const settingsUpdates: SettingRead[] = []

      if (otherAvatarUrl.trim()) {
        const otherAvatarSetting = await writeSetting({
          setting_key: `conversation.${response.conversation.id}.other_avatar_url`,
          setting_value: otherAvatarUrl.trim(),
          is_secret: false,
        })
        settingsUpdates.push(otherAvatarSetting)
      }

      if (settingsUpdates.length > 0) {
        setSettings((current) => upsertSettings(current ?? [], settingsUpdates))
      }

      setConversations((current) => {
        const existing = current ?? []
        const withoutDuplicate = existing.filter((item) => item.id !== response.conversation.id)
        return [response.conversation, ...withoutDuplicate]
      })
      setActiveTab('chat')
      setSelectedConversationId(response.conversation.id)
      setLatestJobsByConversation((current) => ({
        ...current,
        [response.conversation.id]: response.job,
      }))
      setLatestJobLoadStateByConversation((current) => ({
        ...current,
        [response.conversation.id]: { status: 'loaded' },
      }))
        setMessagesByConversation((current) => ({
          ...current,
          [response.conversation.id]: undefined,
        }))
        setMessagePaginationByConversation((current) => ({
          ...current,
          [response.conversation.id]: {
            hasOlder: false,
            loadingOlder: false,
          },
        }))
        setMessageLoadStateByConversation((current) => ({
          ...current,
          [response.conversation.id]: { status: 'idle' },
      }))
      setMessageLoadErrorByConversation((current) => ({
        ...current,
        [response.conversation.id]: false,
      }))
      setShowImportDialog(false)
      setShowWelcome(false)
    } catch (error) {
      setImportError(error instanceof Error ? error.message : '导入会话失败')
    } finally {
      setImportPending(false)
    }
  }

  const handleStartAnalysis = async () => {
    if (selectedConversationId === null) {
      return
    }

    setStartAnalysisPending(true)

    try {
      const job = await startAnalysis(selectedConversationId)

      setLatestJobsByConversation((current) => ({
        ...current,
        [selectedConversationId]: job,
      }))
      setLatestJobLoadStateByConversation((current) => ({
        ...current,
        [selectedConversationId]: { status: 'loaded' },
      }))
      setConversations((current) => {
        if (!current) return current
        return current.map((conv) =>
          conv.id === selectedConversationId
            ? { ...conv, status: 'queued' }
            : conv
        )
      })
    } catch (error) {
      console.error('Failed to start analysis:', error)
    } finally {
      setStartAnalysisPending(false)
    }
  }

  const handleOpenRewrite = (messageId: number) => {
    if (!analysisCompleted || selectedConversationId === null) {
      return
    }

    const targetMessage = selectedConversationMessagesState?.find((message) => message.id === messageId)
    if (!targetMessage || targetMessage.speaker_role !== 'self' || targetMessage.message_type !== 'text') {
      return
    }

    setChatViewState({ mode: 'history' })
    activeRewriteRequestRef.current = null
    setRewriteDraft({
      conversationId: selectedConversationId,
      targetMessageId: targetMessage.id,
      originalMessage: targetMessage.content_text,
      targetMessageTimestamp: targetMessage.timestamp,
      replacementContent: targetMessage.content_text,
      simulationJobId: null,
      status: 'editing',
      simulation: null,
      errorMessage: null,
      pendingStageLabel: null,
    })
  }

  const handleChangeRewriteDraft = (value: string) => {
    setRewriteDraft((current) =>
      current
        ? {
            ...current,
            replacementContent: value,
            errorMessage: null,
          }
        : current,
    )
  }

  const handleCancelRewrite = () => {
    setRewriteDraft(null)
    activeRewriteRequestRef.current = null
  }

  const handleResetRewriteView = () => {
    setRewriteDraft(null)
    activeRewriteRequestRef.current = null
  }

  const handleContinueRewrite = () => {
    setRewriteDraft((current) =>
      current
        ? {
            ...current,
            status: 'editing',
            simulationJobId: null,
            simulation: null,
            errorMessage: null,
            pendingStageLabel: null,
          }
        : current,
    )
  }

  const handleSubmitRewrite = async () => {
    if (!rewriteDraft || selectedConversationId === null) {
      return
    }

    if (rewriteDraft.status !== 'editing') {
      return
    }

    const trimmedReplacementContent = rewriteDraft.replacementContent.trim()

    if (!trimmedReplacementContent || trimmedReplacementContent === rewriteDraft.originalMessage.trim()) {
      setRewriteDraft(null)
      activeRewriteRequestRef.current = null
      return
    }

    const requestId = rewriteRequestCounterRef.current + 1
    rewriteRequestCounterRef.current = requestId
    activeRewriteRequestRef.current = {
      requestId,
      conversationId: selectedConversationId,
      targetMessageId: rewriteDraft.targetMessageId,
      targetMessageTimestamp: rewriteDraft.targetMessageTimestamp,
    }

    setRewriteDraft((current) =>
      current
        ? {
            ...current,
            replacementContent: trimmedReplacementContent,
            simulationJobId: null,
            status: 'pending',
            simulation: null,
            errorMessage: null,
            pendingStageLabel: resolveSimulationPendingStageLabel(
              settingsFormState.simulationMode,
              settingsFormState.simulationTurnCount,
            ),
          }
        : current,
    )

    try {
      const simulationJob = await createSimulation({
        conversation_id: selectedConversationId,
        target_message_id: rewriteDraft.targetMessageId,
        replacement_content: trimmedReplacementContent,
        mode: settingsFormState.simulationMode,
        turn_count: settingsFormState.simulationTurnCount,
      })

      if (
        !isRewriteRequestCurrent({
          activeRequest: activeRewriteRequestRef.current,
          requestId,
          conversationId: selectedConversationIdRef.current,
          draft: rewriteDraftRef.current
            ? {
                targetMessageId: rewriteDraftRef.current.targetMessageId,
                targetMessageTimestamp: rewriteDraftRef.current.targetMessageTimestamp,
              }
            : null,
        })
      ) {
        return
      }

      setRewriteDraft((current) =>
        current
          ? {
              ...current,
              replacementContent: trimmedReplacementContent,
              simulationJobId: simulationJob.id,
              status: 'pending',
              simulation: null,
              errorMessage: null,
              pendingStageLabel: simulationJob.status_message ?? current.pendingStageLabel,
            }
          : current,
      )
      activeRewriteRequestRef.current = null
    } catch (error) {
      if (
        !isRewriteRequestCurrent({
          activeRequest: activeRewriteRequestRef.current,
          requestId,
          conversationId: selectedConversationIdRef.current,
          draft: rewriteDraftRef.current
            ? {
                targetMessageId: rewriteDraftRef.current.targetMessageId,
                targetMessageTimestamp: rewriteDraftRef.current.targetMessageTimestamp,
              }
            : null,
        })
      ) {
        return
      }

      setRewriteDraft((current) =>
        current
          ? {
              ...current,
              replacementContent: trimmedReplacementContent,
              simulationJobId: null,
              status: 'editing',
              simulation: null,
              errorMessage: error instanceof Error ? error.message : '推演失败',
            }
          : current,
      )
    } finally {
      if (activeRewriteRequestRef.current?.requestId === requestId) {
        activeRewriteRequestRef.current = null
      }
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

  const currentListItems =
    activeTab === 'chat'
      ? hydrationStatus === 'ready'
        ? filteredConversationItems
        : []
      : activeTab === 'contacts'
        ? hydrationStatus === 'ready'
          ? contactsListItems
          : []
        : MOCK_FILES_TAB_ITEMS

  const handleSelectFrontConversation = (conversationId: number) => {
    setActiveTab('chat')
    setSelectedConversationId(conversationId)
  }

  const handleDeleteConversation = async (conversationId: number) => {
    await deleteConversation(conversationId)

    setConversations((current) => current?.filter((conversation) => conversation.id !== conversationId) ?? [])
    setLatestJobsByConversation((current) => {
      const next = { ...current }
      delete next[conversationId]
      return next
    })
    setLatestJobLoadStateByConversation((current) => {
      const next = { ...current }
      delete next[conversationId]
      return next
    })
    setMessagesByConversation((current) => {
      const next = { ...current }
      delete next[conversationId]
      return next
    })
    setMessagePaginationByConversation((current) => {
      const next = { ...current }
      delete next[conversationId]
      return next
    })
    setMessageLoadStateByConversation((current) => {
      const next = { ...current }
      delete next[conversationId]
      return next
    })
    setMessageLoadErrorByConversation((current) => {
      const next = { ...current }
      delete next[conversationId]
      return next
    })
    setMockMessagesByConversation((current) => {
      const next = { ...current }
      delete next[conversationId]
      return next
    })
    setSettings((current) => current?.filter((entry) => entry.setting_key !== `conversation.${conversationId}.other_avatar_url`) ?? [])

    if (selectedConversationId === conversationId) {
      setChatViewState({ mode: 'history' })
      setRewriteDraft(null)
      setInspectorOpen(false)
      setSelectedConversationId((current) => (current === conversationId ? null : current))
    }
  }

  const handleSendFrontMessage = (text: string) => {
    if (activeTab !== 'chat' || selectedConversationId === null) {
      return
    }

    const speakerName = selectedConversation?.self_display_name.trim() || '我'
    const now = new Date()
    const localMessage: FrontChatMessage = {
      id: `mock-local-${Date.now()}`,
      messageId: null,
      align: 'right',
      speakerName,
      avatarUrl: selfAvatarUrl,
      text,
      timestampLabel: formatChatTimestampLabel(now.toISOString(), now),
      timestampRaw: now.toISOString(),
      canRewrite: false,
      source: 'mock',
    }

    setMockMessagesByConversation((current) => ({
      ...current,
      [selectedConversationId]: [...(current[selectedConversationId] ?? []), localMessage],
    }))
  }

  const handleToggleDesktopWindowMaximize = async () => {
    const requestId = windowStateRequestIdRef.current + 1
    windowStateRequestIdRef.current = requestId
    const nextWindowState = await toggleDesktopWindowMaximize()
    if (windowStateRequestIdRef.current === requestId) {
      setIsDesktopWindowMaximized(nextWindowState.isMaximized)
    }
  }

  if (state.phase !== 'ready') {
    return <BootScreen label={label} detail={state.detail} />
  }

  const handleSaveSelfAvatar = async (avatarUrl: string) => {
    setSelfAvatarSavePending(true)
    setSelfAvatarError(null)

    try {
      await persistSelfAvatarSetting(avatarUrl)
      setShowSelfAvatarDialog(false)
    } catch (error) {
      setSelfAvatarError(error instanceof Error ? error.message : '保存头像失败')
    } finally {
      setSelfAvatarSavePending(false)
    }
  }

  return (
    <>
      <FrontAppShell
        titleBar={
          <WindowTitleBar
            appTitle="If Then"
            isMaximized={isDesktopWindowMaximized}
            onMinimize={() => {
              void minimizeDesktopWindow()
            }}
            onToggleMaximize={() => {
              void handleToggleDesktopWindowMaximize()
            }}
            onClose={() => {
              void closeDesktopWindow()
            }}
          />
        }
        sidebar={
          <FrontSidebar
            activeTab={activeTab}
            selfAvatarUrl={selfAvatarUrl}
            onOpenAvatarDialog={() => {
              setSelfAvatarError(null)
              setShowSelfAvatarDialog(true)
            }}
            onTabChange={setActiveTab}
            onOpenSettings={() => setShowSettings(true)}
          />
        }
        list={
          <FrontChatList
            items={currentListItems}
            activeChatId={activeTab === 'chat' ? selectedConversationId : null}
            searchQuery={conversationSearch}
            onSearchChange={setConversationSearch}
            onSelectChat={handleSelectFrontConversation}
            onDeleteChat={handleDeleteConversation}
            onOpenImport={() => {
              setImportError(null)
              setShowImportDialog(true)
            }}
          />
        }
        window={
          <FrontChatWindow
            state={selectedMessageModels}
            analysisProgress={activeTab === 'chat' ? selectedConversationProgress : null}
            conversationKey={
              activeTab === 'chat' && selectedConversationId !== null ? `conversation-${selectedConversationId}` : activeTab
            }
            showChatHistoryButton={activeTab === 'chat' && selectedMessageModels.mode === 'conversation'}
            onOpenChatHistory={() => setShowChatHistoryDialog(true)}
            showInspectorButton={activeTab === 'chat' && analysisCompleted}
            onToggleInspector={() => setInspectorOpen((current) => !current)}
            showStartAnalysisButton={activeTab === 'chat' && selectedConversation?.status === 'imported'}
            onStartAnalysis={handleStartAnalysis}
            startAnalysisPending={startAnalysisPending}
            rewriteState={
              activeTab === 'chat' && rewriteDraft && rewriteDraft.conversationId === selectedConversationId
                ? {
                    state: rewriteDraft.status,
                    targetMessageId: rewriteDraft.targetMessageId,
                    draftText: rewriteDraft.replacementContent,
                    stageLabel: rewriteDraft.status === 'pending' ? rewriteDraft.pendingStageLabel : null,
                    errorMessage: rewriteDraft.errorMessage,
                    generatedMessages: rewriteGeneratedMessages,
                  }
                : null
            }
            onStartRewrite={handleOpenRewrite}
            onChangeRewriteDraft={handleChangeRewriteDraft}
            onSubmitRewrite={() => {
              void handleSubmitRewrite()
            }}
            onCancelRewrite={handleCancelRewrite}
            onResetRewriteView={handleResetRewriteView}
            onContinueRewrite={handleContinueRewrite}
            onSendMessage={handleSendFrontMessage}
            hasOlderMessages={activeTab === 'chat' && selectedMessageModels.mode === 'conversation' && !!selectedConversationPaginationState?.hasOlder}
            olderMessagesPending={activeTab === 'chat' && !!selectedConversationPaginationState?.loadingOlder}
            onLoadOlderMessages={handleLoadOlderMessages}
            jumpToMessageRequest={activeTab === 'chat' ? jumpToMessageRequest : null}
          />
        }
      />
      <WelcomeModal
        open={showWelcome}
        initialSelfAvatarUrl={selfAvatarUrl}
        onConfigureModel={async (avatarUrl) => {
          await persistSelfAvatarSetting(avatarUrl)
          setShowWelcome(false)
          setShowSettings(true)
        }}
        onImportConversation={async (avatarUrl) => {
          await persistSelfAvatarSetting(avatarUrl)
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
      <SelfAvatarDialog
        open={showSelfAvatarDialog}
        initialAvatarUrl={selfAvatarUrl}
        pending={selfAvatarSavePending}
        errorMessage={selfAvatarError}
        onClose={() => setShowSelfAvatarDialog(false)}
        onSave={handleSaveSelfAvatar}
      />
      <ImportDialog
        open={showImportDialog}
        pending={importPending}
        errorMessage={importError}
        onClose={() => setShowImportDialog(false)}
        onSubmit={handleImportConversation}
      />
      <AnalysisInspector
        open={inspectorOpen}
        currentTab={inspectorTab}
        loadingByTab={inspectorLoadingByTab}
        errorMessage={inspectorError}
        topics={inspectorTopics}
        profile={inspectorProfile}
        snapshot={inspectorSnapshot}
        onTabChange={setInspectorTab}
        onClose={() => setInspectorOpen(false)}
      />
      <ChatHistoryDialog
        open={showChatHistoryDialog && activeTab === 'chat' && selectedConversation !== null}
        conversationTitle={selectedMessageModels.mode === 'conversation' ? selectedMessageModels.title : '聊天记录'}
        keyword={chatHistoryKeyword}
        dateValue={chatHistoryDate}
        results={chatHistoryResults}
        loading={chatHistoryLoading}
        loadingMore={chatHistoryLoadingMore}
        errorMessage={chatHistoryError}
        hasMore={chatHistoryHasMore}
        locatePendingMessageId={chatHistoryLocatePendingId}
        onClose={() => setShowChatHistoryDialog(false)}
        onKeywordChange={setChatHistoryKeyword}
        onDateChange={setChatHistoryDate}
        onLoadMore={handleLoadMoreChatHistory}
        onLocate={handleLocateChatHistoryMessage}
      />
    </>
  )
}
