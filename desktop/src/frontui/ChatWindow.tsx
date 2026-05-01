import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from 'react'
import { Folder, History, MessageSquare, MoreHorizontal, Phone, Scissors, Smile } from 'lucide-react'

import type { FrontAnalysisProgress, FrontAnalysisStage, FrontChatMessage, FrontChatWindowState } from './types'

const TOP_LOAD_TRIGGER_PX = 24
const TOP_LOAD_REARM_PX = 72

type RewriteState =
  | {
      state: 'editing' | 'pending' | 'completed'
      targetMessageId: number
      draftText: string
      stageLabel?: string | null
      errorMessage?: string | null
      generatedMessages?: FrontChatMessage[]
    }
  | null

type FrontChatWindowProps = {
  state: FrontChatWindowState
  analysisProgress?: FrontAnalysisProgress | null
  onSendMessage: (text: string) => void
  conversationKey?: string
  showInspectorButton?: boolean
  onToggleInspector?: () => void
  showChatHistoryButton?: boolean
  onOpenChatHistory?: () => void
  rewriteState?: RewriteState
  onStartRewrite?: (messageId: number) => void
  onChangeRewriteDraft?: (value: string) => void
  onSubmitRewrite?: () => void
  onCancelRewrite?: () => void
  onResetRewriteView?: () => void
  onContinueRewrite?: () => void
  hasOlderMessages?: boolean
  olderMessagesPending?: boolean
  onLoadOlderMessages?: () => Promise<void> | void
  showStartAnalysisButton?: boolean
  onStartAnalysis?: () => void
  startAnalysisPending?: boolean
  jumpToMessageRequest?: {
    messageId: number
    requestKey: number
  } | null
}

export function FrontChatWindow({
  state,
  analysisProgress = null,
  onSendMessage,
  conversationKey,
  showInspectorButton = false,
  onToggleInspector,
  showChatHistoryButton = false,
  onOpenChatHistory,
  rewriteState = null,
  onStartRewrite,
  onChangeRewriteDraft,
  onSubmitRewrite,
  onCancelRewrite,
  onResetRewriteView,
  onContinueRewrite,
  hasOlderMessages = false,
  olderMessagesPending = false,
  onLoadOlderMessages,
  showStartAnalysisButton = false,
  onStartAnalysis,
  startAnalysisPending = false,
  jumpToMessageRequest = null,
}: FrontChatWindowProps) {
  const [inputText, setInputText] = useState('')
  const [historyLoadHint, setHistoryLoadHint] = useState<'hidden' | 'loading' | 'loaded'>('hidden')
  const [contextMenu, setContextMenu] = useState<{ messageId: number; x: number; y: number } | null>(null)
  const [showCompletionMotion, setShowCompletionMotion] = useState(false)
  const [showAnalysisProgressDetails, setShowAnalysisProgressDetails] = useState(false)
  const [jumpHighlightMessageId, setJumpHighlightMessageId] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const inlineEditorRef = useRef<HTMLTextAreaElement>(null)
  const completionMotionTimerRef = useRef<number | null>(null)
  const jumpHighlightTimerRef = useRef<number | null>(null)
  const previousRewriteStateRef = useRef<RewriteState>(null)
  const conversationMessages = state.mode === 'conversation' ? state.messages : []
  const previousMessageStateRef = useRef<{
    conversationKey?: string
    firstMessageId?: string
    lastMessageId?: string
    count: number
  }>({ count: 0 })
  const olderMessageAnchorRef = useRef<{
    messageId: string
    topOffset: number
  } | null>(null)
  const olderLoadArmedRef = useRef(true)
  const previousOlderMessagesPendingRef = useRef(false)
  const historyLoadHintTimerRef = useRef<number | null>(null)

  const clearHistoryLoadHintTimer = () => {
    if (historyLoadHintTimerRef.current !== null) {
      window.clearTimeout(historyLoadHintTimerRef.current)
      historyLoadHintTimerRef.current = null
    }
  }

  const clearCompletionMotionTimer = () => {
    if (completionMotionTimerRef.current !== null) {
      window.clearTimeout(completionMotionTimerRef.current)
      completionMotionTimerRef.current = null
    }
  }

  const clearJumpHighlightTimer = () => {
    if (jumpHighlightTimerRef.current !== null) {
      window.clearTimeout(jumpHighlightTimerRef.current)
      jumpHighlightTimerRef.current = null
    }
  }

  const scheduleHideHistoryLoadHint = () => {
    clearHistoryLoadHintTimer()
    historyLoadHintTimerRef.current = window.setTimeout(() => {
      setHistoryLoadHint('hidden')
      historyLoadHintTimerRef.current = null
    }, 900)
  }

  const captureFirstVisibleMessageAnchor = () => {
    if (!scrollContainerRef.current) {
      return null
    }

    const containerRect = scrollContainerRef.current.getBoundingClientRect()
    const messageElements = Array.from(scrollContainerRef.current.querySelectorAll<HTMLElement>('[data-chat-message-id]'))
    const anchorElement =
      messageElements.find((element) => element.getBoundingClientRect().bottom > containerRect.top + 6) ?? messageElements[0]

    if (!anchorElement) {
      return null
    }

    return {
      messageId: anchorElement.dataset.chatMessageId ?? '',
      topOffset: anchorElement.getBoundingClientRect().top - containerRect.top,
    }
  }

  const generatedMessages = rewriteState?.generatedMessages ?? []
  const historyHintLabel =
    historyLoadHint === 'loading' ? '正在加载聊天记录...' : hasOlderMessages ? '已加载更早消息' : '已到最早消息'
  const hasActiveRewrite = rewriteState !== null
  const renderedMessages = useMemo(
    () => (rewriteState?.state === 'completed' ? [...conversationMessages, ...generatedMessages] : conversationMessages),
    [conversationMessages, generatedMessages, rewriteState?.state],
  )

  useEffect(() => {
    setInputText('')
  }, [conversationKey, state.mode])

  useEffect(() => {
    return () => {
      clearHistoryLoadHintTimer()
      clearCompletionMotionTimer()
      clearJumpHighlightTimer()
    }
  }, [])

  useEffect(() => {
    if (!analysisProgress) {
      setShowAnalysisProgressDetails(false)
    }
  }, [analysisProgress])

  useEffect(() => {
    clearHistoryLoadHintTimer()
    setHistoryLoadHint('hidden')
    previousOlderMessagesPendingRef.current = false
    olderMessageAnchorRef.current = null
    olderLoadArmedRef.current = true
    setContextMenu(null)
    setShowCompletionMotion(false)
    setJumpHighlightMessageId(null)
    previousRewriteStateRef.current = null
  }, [conversationKey])

  useEffect(() => {
    const previousState = previousRewriteStateRef.current?.state ?? null
    const nextState = rewriteState?.state ?? null

    if (previousState === 'pending' && nextState === 'completed') {
      clearCompletionMotionTimer()
      setShowCompletionMotion(true)
      completionMotionTimerRef.current = window.setTimeout(() => {
        setShowCompletionMotion(false)
        completionMotionTimerRef.current = null
      }, 950)
    } else if (nextState !== 'completed') {
      clearCompletionMotionTimer()
      setShowCompletionMotion(false)
    }

    previousRewriteStateRef.current = rewriteState
  }, [rewriteState])

  useEffect(() => {
    if (olderMessagesPending) {
      clearHistoryLoadHintTimer()
      setHistoryLoadHint('loading')
    } else if (previousOlderMessagesPendingRef.current) {
      setHistoryLoadHint('loaded')
      scheduleHideHistoryLoadHint()
    }

    previousOlderMessagesPendingRef.current = olderMessagesPending
  }, [hasOlderMessages, olderMessagesPending])

  useEffect(() => {
    if (rewriteState?.state !== 'editing') {
      return
    }

    inlineEditorRef.current?.focus()
    inlineEditorRef.current?.setSelectionRange(rewriteState.draftText.length, rewriteState.draftText.length)
  }, [rewriteState?.state, rewriteState?.targetMessageId, rewriteState?.draftText])

  useEffect(() => {
    if (!contextMenu) {
      return
    }

    const dismiss = () => setContextMenu(null)
    window.addEventListener('click', dismiss)
    window.addEventListener('scroll', dismiss, true)

    return () => {
      window.removeEventListener('click', dismiss)
      window.removeEventListener('scroll', dismiss, true)
    }
  }, [contextMenu])

  useLayoutEffect(() => {
    if (state.mode !== 'conversation') {
      previousMessageStateRef.current = { count: 0 }
      olderMessageAnchorRef.current = null
      return
    }

    const firstMessageId = renderedMessages[0]?.id
    const lastMessageId = renderedMessages[renderedMessages.length - 1]?.id
    const previous = previousMessageStateRef.current
    const conversationChanged = previous.conversationKey !== conversationKey
    const appendedNewMessage = !conversationChanged && renderedMessages.length > previous.count && lastMessageId !== previous.lastMessageId
    const initialConversationLoad = !conversationChanged && previous.count === 0 && renderedMessages.length > 0
    const shouldScrollToBottom = conversationChanged || appendedNewMessage || initialConversationLoad

    if (olderMessageAnchorRef.current && scrollContainerRef.current) {
      const containerRect = scrollContainerRef.current.getBoundingClientRect()
      const anchorElement = scrollContainerRef.current.querySelector<HTMLElement>(
        `[data-chat-message-id="${olderMessageAnchorRef.current.messageId}"]`,
      )

      if (anchorElement) {
        const anchorTop = anchorElement.getBoundingClientRect().top - containerRect.top
        scrollContainerRef.current.scrollTop += anchorTop - olderMessageAnchorRef.current.topOffset
      }

      olderMessageAnchorRef.current = null
    } else if (shouldScrollToBottom) {
      messagesEndRef.current?.scrollIntoView({ behavior: conversationChanged || initialConversationLoad ? 'auto' : 'smooth' })
    }

    previousMessageStateRef.current = {
      conversationKey,
      firstMessageId,
      lastMessageId,
      count: renderedMessages.length,
    }
  }, [conversationKey, renderedMessages, state.mode])

  useLayoutEffect(() => {
    if (!jumpToMessageRequest || state.mode !== 'conversation' || !scrollContainerRef.current) {
      return
    }

    const messageDomId = `message-${jumpToMessageRequest.messageId}`
    const targetElement = scrollContainerRef.current.querySelector<HTMLElement>(`[data-chat-message-id="${messageDomId}"]`)

    if (!targetElement) {
      return
    }

    targetElement.scrollIntoView({ behavior: 'smooth', block: 'center' })
    clearJumpHighlightTimer()
    setJumpHighlightMessageId(messageDomId)
    jumpHighlightTimerRef.current = window.setTimeout(() => {
      setJumpHighlightMessageId((current) => (current === messageDomId ? null : current))
      jumpHighlightTimerRef.current = null
    }, 1800)
  }, [jumpToMessageRequest?.requestKey, renderedMessages, state.mode])

  const handleScroll = async () => {
    const currentScrollTop = scrollContainerRef.current?.scrollTop ?? 0

    if (currentScrollTop > TOP_LOAD_REARM_PX) {
      olderLoadArmedRef.current = true
    }

    if (
      state.mode !== 'conversation' ||
      !hasOlderMessages ||
      olderMessagesPending ||
      !onLoadOlderMessages ||
      !scrollContainerRef.current ||
      currentScrollTop > TOP_LOAD_TRIGGER_PX ||
      !olderLoadArmedRef.current
    ) {
      return
    }

    olderLoadArmedRef.current = false
    olderMessageAnchorRef.current = captureFirstVisibleMessageAnchor()
    clearHistoryLoadHintTimer()
    setHistoryLoadHint('loading')

    try {
      await onLoadOlderMessages()
    } catch {
      olderMessageAnchorRef.current = null
      setHistoryLoadHint('hidden')
    }
  }

  const handleSend = () => {
    if (state.mode !== 'conversation' || !inputText.trim()) {
      return
    }
    onSendMessage(inputText)
    setInputText('')
  }

  const handleComposerKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      handleSend()
    }
  }

  const handleRewriteEditorKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (rewriteState?.state !== 'editing') {
      return
    }

    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      onSubmitRewrite?.()
      return
    }

    if (event.key === 'Escape') {
      event.preventDefault()
      onCancelRewrite?.()
    }
  }

  if (state.mode === 'placeholder') {
    return (
      <div className="flex h-full flex-1 items-center justify-center bg-[var(--if-bg-panel)]">
        <div className="flex flex-col items-center gap-4 text-center">
          <MonitorLogo />
          <p className="text-[14px] text-[var(--if-text-tertiary)]">选择一段对话开始聊天</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 min-w-[400px] flex-1 flex-col overflow-hidden bg-[var(--if-bg-panel)]">
      <div className="flex-shrink-0 border-b border-[color:var(--if-divider)] bg-[var(--if-bg-window)]">
        <div className="flex h-14 items-center justify-between px-5">
          <h2 className="text-[16px] font-semibold text-[var(--if-text-primary)]">{state.title}</h2>
          <div className="flex items-center gap-2">
            {showInspectorButton && onToggleInspector ? (
              <button
                type="button"
                className="rounded-[8px] border border-[color:var(--if-divider-strong)] bg-white/72 px-3 py-1.5 text-[13px] text-[var(--if-text-secondary)] transition-colors duration-150 hover:bg-white hover:text-[var(--if-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(7,193,96,0.18)]"
                onClick={onToggleInspector}
              >
                分析
              </button>
            ) : null}
            <button
              type="button"
              className="rounded-[8px] border border-transparent p-1.5 text-[var(--if-text-secondary)] transition-colors duration-150 hover:border-[color:var(--if-divider)] hover:bg-white/72 hover:text-[var(--if-text-primary)]"
              aria-label="更多操作"
            >
              <MoreHorizontal size={18} />
            </button>
          </div>
        </div>
        {analysisProgress ? (
          <HeaderProgressStatus
            progress={analysisProgress}
            onOpenDetails={() => setShowAnalysisProgressDetails(true)}
          />
        ) : null}
        {showStartAnalysisButton && onStartAnalysis ? (
          <div className="border-t border-[color:var(--if-divider)] bg-[var(--if-bg-panel)] px-5 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[13px] font-medium text-[var(--if-text-primary)]">聊天记录已导入</p>
                <p className="mt-1 text-[12px] text-[var(--if-text-secondary)]">开始分析以提取话题、人格特征和关系快照</p>
              </div>
              <button
                type="button"
                className="rounded-[8px] border border-[rgba(7,193,96,0.2)] bg-[var(--if-accent)] px-4 py-2 text-[13px] font-medium text-white transition-colors duration-150 hover:bg-[var(--if-accent-hover)] disabled:cursor-not-allowed disabled:opacity-50"
                onClick={onStartAnalysis}
                disabled={startAnalysisPending}
              >
                {startAnalysisPending ? '启动中…' : '开始分析'}
              </button>
            </div>
          </div>
        ) : null}
        {rewriteState?.state === 'completed' ? (
          <div className="border-t border-[color:var(--if-divider)] bg-[var(--if-accent-softer)] px-5 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[var(--if-accent)]" />
                  <p className="text-[13px] font-medium text-[#245c33]">正在查看推演结果</p>
                </div>
                <p className="mt-1 text-[12px] text-[#5f7a67]">原始历史已保留，可随时切回</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-[8px] border border-[color:var(--if-divider)] bg-white/92 px-3 py-1.5 text-[12px] text-[var(--if-text-secondary)] transition-colors duration-150 hover:bg-white hover:text-[var(--if-text-primary)]"
                  onClick={onResetRewriteView}
                >
                  返回原始历史
                </button>
                <button
                  type="button"
                  className="rounded-[8px] border border-[rgba(7,193,96,0.2)] bg-[var(--if-accent)] px-3 py-1.5 text-[12px] text-white transition-colors duration-150 hover:bg-[var(--if-accent-hover)]"
                  onClick={onContinueRewrite}
                >
                  继续改写
                </button>
              </div>
            </div>
          </div>
        ) : null}
      </div>

      <div className="relative flex-1 min-h-0 overflow-hidden">
        {historyLoadHint !== 'hidden' ? (
          <div className="pointer-events-none absolute inset-x-0 top-3 z-10 flex justify-center">
            <span
              className={`inline-flex items-center gap-2 rounded-full border px-3.5 py-1.5 text-[11px] font-medium tracking-[0.01em] shadow-[0_6px_18px_rgba(0,0,0,0.16)] backdrop-blur-md transition-all duration-300 ${
                historyLoadHint === 'loading'
                  ? 'border-white/10 bg-[rgba(54,49,44,0.88)] text-white'
                  : 'border-white/10 bg-[rgba(72,66,60,0.78)] text-white/92'
              }`}
            >
              {historyLoadHint === 'loading' ? (
                <span className="inline-flex items-center gap-1.5" aria-hidden="true">
                  <span className="h-1.5 w-1.5 rounded-full bg-white/90 animate-pulse" />
                  <span className="h-1.5 w-1.5 rounded-full bg-white/70 animate-pulse [animation-delay:120ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-white/50 animate-pulse [animation-delay:240ms]" />
                </span>
              ) : null}
              <span>{historyHintLabel}</span>
            </span>
          </div>
        ) : null}

        {contextMenu ? (
          <div
            className="fixed z-30 min-w-[112px] rounded-[10px] border border-[color:var(--if-divider-strong)] bg-white/96 p-1 shadow-[var(--if-shadow-popover)] backdrop-blur"
            style={{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }}
          >
            <button
              type="button"
              className="w-full rounded-[8px] px-3 py-2 text-left text-[13px] text-[var(--if-text-primary)] transition-colors duration-150 hover:bg-[var(--if-bg-panel)]"
              onClick={() => {
                onStartRewrite?.(contextMenu.messageId)
                setContextMenu(null)
              }}
            >
              改写
            </button>
          </div>
        ) : null}

        {rewriteState?.state === 'pending' ? (
          <div
            data-testid="rewrite-pending-overlay"
            className="pointer-events-none absolute inset-x-0 bottom-6 z-20 flex justify-center px-6"
          >
            <div className="relative w-full max-w-[320px]">
              <div className="absolute inset-0 rounded-[24px] bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.68),rgba(255,255,255,0.12)_72%,rgba(255,255,255,0))] blur-xl" />
              <div className="relative rounded-[16px] border border-[color:var(--if-divider-strong)] bg-[rgba(255,255,255,0.92)] px-4 py-3 text-center shadow-[0_14px_40px_rgba(0,0,0,0.12)] backdrop-blur-md">
                <div className="mx-auto mb-2 flex w-fit items-center gap-1.5" aria-hidden="true">
                  <span className="h-1.5 w-1.5 rounded-full bg-[var(--if-accent)] animate-pulse" />
                  <span className="h-1.5 w-1.5 rounded-full bg-[rgba(7,193,96,0.78)] animate-pulse [animation-delay:120ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-[rgba(7,193,96,0.56)] animate-pulse [animation-delay:240ms]" />
                </div>
                <p className="text-[14px] font-medium text-[var(--if-text-primary)]">正在推演……</p>
                <p className="mt-1 text-[12px] text-[var(--if-text-secondary)]">{rewriteState.stageLabel ?? '正在等待推演结果返回'}</p>
              </div>
            </div>
          </div>
        ) : null}

        {showCompletionMotion ? (
          <div
            data-testid="rewrite-completion-flash"
            className="pointer-events-none absolute inset-x-6 bottom-4 z-[19] h-28 rounded-[28px] rewrite-completion-flash"
          />
        ) : null}

        <div
          ref={scrollContainerRef}
          data-testid="chat-message-scroll"
          className="h-full min-h-0 space-y-4 overflow-y-auto bg-[var(--if-bg-panel)] p-5 custom-scrollbar"
          onScroll={() => {
            void handleScroll()
          }}
        >
          {renderedMessages.map((message, index) => {
            const showTime = index === 0 || message.timestampLabel !== renderedMessages[index - 1]?.timestampLabel
            const isSelf = message.align === 'right'
            const bubbleTone = message.bubbleTone ?? 'default'
            const isRewriteTarget =
              rewriteState !== null &&
              rewriteState.targetMessageId === message.messageId &&
              (rewriteState.state === 'editing' || rewriteState.state === 'pending' || rewriteState.state === 'completed')
            const bubbleClass =
              bubbleTone === 'rewrite-target'
                ? 'rewrite-target rounded-[10px] border border-[#c9dce8] bg-[linear-gradient(135deg,#f8fbff_0%,#eef6fc_52%,#fcfaf6_100%)] text-[var(--if-text-primary)] shadow-[0_12px_24px_rgba(73,61,49,0.08)]'
                : bubbleTone === 'simulation-self'
                  ? 'rounded-[10px] border border-[#c9deeb] bg-[#d9e9f2] text-[var(--if-text-primary)]'
                  : bubbleTone === 'simulation-other'
                    ? 'rounded-[10px] border border-[#ead1da] bg-[#f3e0e6] text-[var(--if-text-primary)]'
                    : isSelf
                      ? 'rounded-[10px] border border-[#c8deb9] bg-[#d8ebc8] text-[var(--if-text-primary)]'
                      : 'rounded-[10px] border border-[color:var(--if-divider)] bg-white text-[var(--if-text-primary)]'
            const bubbleArrowClass =
              bubbleTone === 'simulation-self'
                  ? 'right-[-12px] border-l-[#d9e9f2]'
                  : bubbleTone === 'simulation-other'
                    ? 'left-[-12px] border-r-[#f3e0e6]'
                    : isSelf
                      ? 'right-[-12px] border-l-[#d8ebc8]'
                      : 'left-[-12px] border-r-white'

            return (
              <div
                key={message.id}
                data-chat-message-id={message.id}
                className={`flex flex-col transition-opacity duration-200 ${
                  message.ghosted ? 'pointer-events-none opacity-28 saturate-0' : ''
                } ${showCompletionMotion && rewriteState?.state === 'completed' && message.source === 'mock' ? 'rewrite-result-enter' : ''} ${
                  jumpHighlightMessageId === message.id ? 'chat-message-jump-highlight' : ''
                }`}
              >
                {showTime ? (
                  <div className="text-center my-2">
                    <span className="text-[12px] text-[var(--if-text-tertiary)]">{message.timestampLabel}</span>
                  </div>
                ) : null}

                <div className={`flex w-full ${isSelf ? 'justify-end' : 'justify-start'}`}>
                  {!isSelf ? (
                    <img src={message.avatarUrl} alt={message.speakerName} className="mr-3 h-9 w-9 flex-shrink-0 rounded-[10px] object-cover ring-1 ring-black/4" />
                  ) : null}

                  <div
                    className={`relative max-w-[70%] ${
                      message.canRewrite && onStartRewrite && !hasActiveRewrite ? 'cursor-pointer' : ''
                    }`}
                    onDoubleClick={() => {
                      if (message.canRewrite && message.messageId !== null && onStartRewrite && !hasActiveRewrite) {
                        onStartRewrite(message.messageId)
                      }
                    }}
                    onContextMenu={(event: ReactMouseEvent<HTMLDivElement>) => {
                      if (message.canRewrite && message.messageId !== null && onStartRewrite && !hasActiveRewrite) {
                        event.preventDefault()
                        setContextMenu({
                          messageId: message.messageId,
                          x: event.clientX,
                          y: event.clientY,
                        })
                      }
                    }}
                  >
                    {isRewriteTarget && rewriteState?.state === 'editing' ? (
                      <div className="rounded-[12px] border border-[rgba(7,193,96,0.28)] bg-white/92 px-3 py-2 shadow-[0_10px_22px_rgba(73,61,49,0.08)]">
                        <textarea
                          ref={inlineEditorRef}
                          value={rewriteState.draftText}
                          onChange={(event) => onChangeRewriteDraft?.(event.target.value)}
                          onBlur={() => {
                            onSubmitRewrite?.()
                          }}
                          onKeyDown={handleRewriteEditorKeyDown}
                          className="min-h-[56px] w-[min(420px,60vw)] resize-none bg-transparent text-[14px] leading-relaxed text-[var(--if-text-primary)] outline-none"
                        />
                        <div className="mt-2 flex items-center justify-between text-[11px] text-[var(--if-text-secondary)]">
                          <span>回车保存并推演 · Esc 取消</span>
                          <span>点击空白处也会保存</span>
                        </div>
                        {rewriteState.errorMessage ? (
                          <p className="mt-2 text-[12px] text-[var(--if-danger)]">{rewriteState.errorMessage}</p>
                        ) : null}
                      </div>
                    ) : (
                      <div
                        data-chat-bubble-tone={bubbleTone}
                        className={`relative break-words px-3 py-2 text-[14px] leading-relaxed shadow-[0_1px_2px_rgba(0,0,0,0.04)] ${bubbleClass}`}
                        style={{ wordBreak: 'break-word' }}
                      >
                        {bubbleTone !== 'rewrite-target' ? (
                          <div
                            className={`absolute top-3 h-0 w-0 border-[8px] border-transparent ${bubbleArrowClass}`}
                          />
                        ) : null}
                        {message.text}
                      </div>
                    )}
                  </div>

                  {isSelf ? (
                    <img src={message.avatarUrl} alt={message.speakerName} className="ml-3 h-9 w-9 flex-shrink-0 rounded-[10px] object-cover ring-1 ring-black/4" />
                  ) : null}
                </div>
              </div>
            )
          })}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="flex h-[164px] flex-shrink-0 flex-col border-t border-[color:var(--if-divider)] bg-[var(--if-bg-window)]">
        <div className="flex h-10 items-center justify-between px-4 text-[var(--if-text-secondary)]">
          <div className="flex items-center gap-4">
            <button
              type="button"
              className="rounded-[8px] p-1 transition-colors duration-150 hover:bg-white/72 hover:text-[var(--if-text-primary)]"
              aria-label="表情"
            >
              <Smile size={20} />
            </button>
            <button
              type="button"
              className="rounded-[8px] p-1 transition-colors duration-150 hover:bg-white/72 hover:text-[var(--if-text-primary)]"
              aria-label="文件"
            >
              <Folder size={20} />
            </button>
            <button
              type="button"
              className="rounded-[8px] p-1 transition-colors duration-150 hover:bg-white/72 hover:text-[var(--if-text-primary)]"
              aria-label="截图"
            >
              <Scissors size={20} />
            </button>
            <button
              type="button"
              className="rounded-[8px] p-1 transition-colors duration-150 hover:bg-white/72 hover:text-[var(--if-text-primary)]"
              aria-label="消息"
            >
              <MessageSquare size={20} />
            </button>
            <button
              type="button"
              className="rounded-[8px] p-1 transition-colors duration-150 hover:bg-white/72 hover:text-[var(--if-text-primary)]"
              aria-label="通话"
            >
              <Phone size={20} />
            </button>
          </div>
          {showChatHistoryButton && onOpenChatHistory ? (
            <button
              type="button"
              className="rounded-[8px] p-1 transition-colors duration-150 hover:bg-white/72 hover:text-[var(--if-text-primary)]"
              aria-label="聊天记录"
              title="聊天记录"
              onClick={onOpenChatHistory}
            >
              <History size={18} />
            </button>
          ) : null}
        </div>

        <div className="flex-1 px-4">
          <textarea
            value={inputText}
            onChange={(event) => setInputText(event.target.value)}
            onKeyDown={handleComposerKeyDown}
            className="h-full w-full resize-none border-none bg-transparent text-[14px] text-[var(--if-text-primary)] outline-none custom-scrollbar placeholder:text-[var(--if-text-tertiary)]"
            placeholder="输入消息…"
          />
        </div>

        <div className="flex justify-end px-4 pb-3">
          <button
            type="button"
            onClick={handleSend}
            className="rounded-[8px] border border-[rgba(7,193,96,0.18)] bg-[var(--if-accent)] px-5 py-1.5 text-[13px] font-medium text-white transition-colors duration-150 hover:bg-[var(--if-accent-hover)]"
          >
            发送(S)
          </button>
        </div>
      </div>
      {analysisProgress && showAnalysisProgressDetails ? (
        <AnalysisProgressDialog
          progress={analysisProgress}
          onClose={() => setShowAnalysisProgressDetails(false)}
        />
      ) : null}
    </div>
  )
}

function HeaderProgressStatus({ progress, onOpenDetails }: { progress: FrontAnalysisProgress; onOpenDetails: () => void }) {
  const textClass = progress.tone === 'failed' ? 'text-[var(--if-danger)]' : 'text-[var(--if-text-secondary)]'

  return (
    <button
      type="button"
      className="front-progress flex w-full cursor-pointer items-center justify-between gap-3 border-t border-[color:var(--if-divider)] bg-[var(--if-bg-panel)] px-5 py-3 text-left transition-colors duration-150 hover:bg-white/72 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-[rgba(7,193,96,0.18)]"
      onClick={onOpenDetails}
      aria-label="查看分析进度详情"
    >
      <span className={`min-w-0 truncate text-[12px] font-medium ${textClass}`}>{progress.label}</span>
      <span className="shrink-0 rounded-[8px] border border-[color:var(--if-divider)] bg-white/72 px-2 py-0.5 text-[11px] text-[var(--if-text-tertiary)]">
        详情
      </span>
    </button>
  )
}

function AnalysisProgressDialog({ progress, onClose }: { progress: FrontAnalysisProgress; onClose: () => void }) {
  const stages = progress.stages?.length ? progress.stages : buildFallbackProgressStages(progress)

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-[rgba(33,33,33,0.28)] p-4 backdrop-blur-[3px]" role="dialog" aria-modal="true" aria-labelledby="analysis-progress-title">
      <button type="button" className="absolute inset-0 cursor-default" aria-label="关闭分析进度详情" onClick={onClose} />
      <section className="relative z-10 flex max-h-[calc(100vh-32px)] w-[min(560px,100%)] flex-col overflow-hidden rounded-[12px] border border-[color:var(--if-divider-strong)] bg-[var(--if-bg-window)] shadow-[var(--if-shadow-dialog)]">
        <header className="flex min-h-14 items-center justify-between border-b border-[color:var(--if-divider)] px-5">
          <div className="min-w-0">
            <h2 id="analysis-progress-title" className="m-0 text-[15px] font-semibold text-[var(--if-text-primary)]">
              分析进度
            </h2>
            <p className="mt-1 text-[12px] text-[var(--if-text-secondary)]">{progress.label}</p>
          </div>
          <button
            type="button"
            className="rounded-[8px] border border-transparent px-2 py-1 text-[13px] text-[var(--if-text-secondary)] transition-colors duration-150 hover:border-[color:var(--if-divider)] hover:bg-white/72 hover:text-[var(--if-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(7,193,96,0.18)]"
            onClick={onClose}
          >
            关闭
          </button>
        </header>
        <div className="custom-scrollbar min-h-0 overflow-y-auto p-5">
          <ol className="grid gap-3">
            {stages.map((stage) => (
              <AnalysisProgressStageRow key={stage.id} stage={stage} />
            ))}
          </ol>
        </div>
      </section>
    </div>
  )
}

function AnalysisProgressStageRow({ stage }: { stage: FrontAnalysisStage }) {
  const statusLabel = resolveStageStatusLabel(stage)
  const statusClass =
    stage.status === 'failed'
      ? 'text-[var(--if-danger)]'
      : stage.status === 'running'
        ? 'text-[var(--if-accent)]'
        : 'text-[var(--if-text-tertiary)]'
  const unitLabel = stage.totalUnits > 0 ? `${stage.completedUnits}/${stage.totalUnits}` : statusLabel

  return (
    <li className="rounded-[8px] border border-[color:var(--if-divider)] bg-white/70 p-3">
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="m-0 truncate text-[13px] font-medium text-[var(--if-text-primary)]">{stage.label}</p>
          <p className={`mt-1 text-[12px] ${statusClass}`}>{statusLabel}</p>
        </div>
        <span className="shrink-0 text-[12px] text-[var(--if-text-secondary)]">{unitLabel}</span>
      </div>
      {stage.status === 'running' ? (
        <div className="mt-3 h-[5px] overflow-hidden rounded-full bg-[rgba(94,84,72,0.14)]">
          <div className="h-full rounded-full bg-[var(--if-accent)] transition-all duration-300" style={{ width: `${stage.percent}%` }} />
        </div>
      ) : null}
    </li>
  )
}

function resolveStageStatusLabel(stage: FrontAnalysisStage): string {
  switch (stage.status) {
    case 'waiting':
      return '等待中'
    case 'running':
      return `进行中 ${stage.percent}%`
    case 'completed':
      return '已完成'
    case 'failed':
      return '失败'
    default: {
      const _exhaustive: never = stage.status
      return _exhaustive
    }
  }
}

function buildFallbackProgressStages(progress: FrontAnalysisProgress): FrontAnalysisStage[] {
  return [
    {
      id: 'current',
      label: progress.label,
      status: progress.tone === 'failed' ? 'failed' : 'running',
      completedUnits: progress.percent,
      totalUnits: 100,
      percent: progress.percent,
    },
  ]
}

function MonitorLogo() {
  return (
    <svg width="120" height="120" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M4 6C4 4.89543 4.89543 4 6 4H18C19.1046 4 20 4.89543 20 6V14C20 15.1046 19.1046 16 18 16H6C4.89543 16 4 15.1046 4 14V6Z"
        stroke="#c6beb5"
        strokeWidth="1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M8 20H16" stroke="#c6beb5" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 16V20" stroke="#c6beb5" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
