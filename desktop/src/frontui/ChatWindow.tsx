import {
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent as ReactMouseEvent,
} from 'react'
import { Folder, MessageSquare, MoreHorizontal, Phone, Scissors, Smile } from 'lucide-react'

import type { FrontAnalysisProgress, FrontChatMessage, FrontChatWindowState } from './types'

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
}

export function FrontChatWindow({
  state,
  analysisProgress = null,
  onSendMessage,
  conversationKey,
  showInspectorButton = false,
  onToggleInspector,
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
}: FrontChatWindowProps) {
  const [inputText, setInputText] = useState('')
  const [historyLoadHint, setHistoryLoadHint] = useState<'hidden' | 'loading' | 'loaded'>('hidden')
  const [contextMenu, setContextMenu] = useState<{ messageId: number; x: number; y: number } | null>(null)
  const [showCompletionMotion, setShowCompletionMotion] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const scrollContainerRef = useRef<HTMLDivElement>(null)
  const inlineEditorRef = useRef<HTMLTextAreaElement>(null)
  const completionMotionTimerRef = useRef<number | null>(null)
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
    }
  }, [])

  useEffect(() => {
    clearHistoryLoadHintTimer()
    setHistoryLoadHint('hidden')
    previousOlderMessagesPendingRef.current = false
    olderMessageAnchorRef.current = null
    olderLoadArmedRef.current = true
    setContextMenu(null)
    setShowCompletionMotion(false)
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
    } else if (conversationChanged || appendedNewMessage || (previous.count === 0 && renderedMessages.length > 0)) {
      messagesEndRef.current?.scrollIntoView({ behavior: conversationChanged ? 'auto' : 'smooth' })
    }

    previousMessageStateRef.current = {
      conversationKey,
      firstMessageId,
      lastMessageId,
      count: renderedMessages.length,
    }
  }, [conversationKey, renderedMessages, state.mode])

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
      <div className="flex-1 h-full bg-[#f5f5f5] flex items-center justify-center">
        <div className="flex flex-col items-center gap-4 text-center">
          <MonitorLogo />
          <p className="text-[#b4b4b4] text-[14px]">选择一段对话开始聊天</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-0 min-w-[400px] flex-1 flex-col overflow-hidden bg-[#f5f5f5]">
      <div className="border-b border-[#e5e5e5] flex-shrink-0 bg-[#f5f5f5]">
        <div className="h-[60px] px-5 flex items-center justify-between">
          <h2 className="text-[20px] font-medium text-[#111]">{state.title}</h2>
          <div className="flex items-center gap-2">
            {showInspectorButton && onToggleInspector ? (
              <button
                type="button"
                className="rounded bg-white px-3 py-1.5 text-[13px] text-[#555] shadow-sm hover:bg-[#ececec]"
                onClick={onToggleInspector}
              >
                分析
              </button>
            ) : null}
            <button type="button" className="p-1 hover:bg-[#e5e5e5] rounded" aria-label="更多操作">
              <MoreHorizontal size={20} className="text-[#666]" />
            </button>
          </div>
        </div>
        {analysisProgress ? <HeaderProgressBar progress={analysisProgress} /> : null}
        {showStartAnalysisButton && onStartAnalysis ? (
          <div className="border-t border-[#ebebeb] bg-[#f7f9fa] px-5 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <p className="text-[13px] font-medium text-[#333]">聊天记录已导入</p>
                <p className="mt-1 text-[12px] text-[#888]">开始分析以提取话题、人格特征和关系快照</p>
              </div>
              <button
                type="button"
                className="rounded-md bg-[#07c160] px-4 py-2 text-[13px] font-medium text-white transition-colors hover:bg-[#06ad56] disabled:opacity-50 disabled:cursor-not-allowed"
                onClick={onStartAnalysis}
                disabled={startAnalysisPending}
              >
                {startAnalysisPending ? '启动中…' : '开始分析'}
              </button>
            </div>
          </div>
        ) : null}
        {rewriteState?.state === 'completed' ? (
          <div className="border-t border-[#ebebeb] bg-[#f2f9f0] px-5 py-3">
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="flex items-center gap-2">
                  <span className="h-2 w-2 rounded-full bg-[#07c160]" />
                  <p className="text-[13px] font-medium text-[#245c33]">正在查看推演结果</p>
                </div>
                <p className="mt-1 text-[12px] text-[#5f7a67]">原始历史已保留，可随时切回</p>
              </div>
              <div className="flex items-center gap-2">
                <button
                  type="button"
                  className="rounded-md border border-[#cfe6d4] bg-white px-3 py-1.5 text-[12px] text-[#355e45] transition-colors hover:bg-[#f7fbf7]"
                  onClick={onResetRewriteView}
                >
                  返回原始历史
                </button>
                <button
                  type="button"
                  className="rounded-md border border-[#b7ddc1] bg-[#e6f5e9] px-3 py-1.5 text-[12px] text-[#245c33] transition-colors hover:bg-[#dbf0df]"
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
                  ? 'border-white/12 bg-[rgba(36,36,36,0.78)] text-white'
                  : 'border-black/6 bg-[rgba(44,44,44,0.68)] text-white/92'
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
            className="fixed z-30 min-w-[112px] rounded-xl border border-black/8 bg-white/96 p-1 shadow-[0_10px_28px_rgba(0,0,0,0.18)] backdrop-blur"
            style={{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }}
          >
            <button
              type="button"
              className="w-full rounded-lg px-3 py-2 text-left text-[13px] text-[#222] hover:bg-[#f0f0f0]"
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
              <div className="absolute inset-0 rounded-3xl bg-[radial-gradient(circle_at_center,rgba(255,255,255,0.82),rgba(255,255,255,0.18)_72%,rgba(255,255,255,0))] blur-xl" />
              <div className="relative rounded-2xl border border-white/55 bg-[rgba(255,255,255,0.88)] px-4 py-3 text-center shadow-[0_14px_40px_rgba(0,0,0,0.12)] backdrop-blur-md">
                <div className="mx-auto mb-2 flex w-fit items-center gap-1.5" aria-hidden="true">
                  <span className="h-1.5 w-1.5 rounded-full bg-[#07c160] animate-pulse" />
                  <span className="h-1.5 w-1.5 rounded-full bg-[#07c160]/75 animate-pulse [animation-delay:120ms]" />
                  <span className="h-1.5 w-1.5 rounded-full bg-[#07c160]/55 animate-pulse [animation-delay:240ms]" />
                </div>
                <p className="text-[14px] font-medium text-[#2a2a2a]">正在推演……</p>
                <p className="mt-1 text-[12px] text-[#6f6f6f]">{rewriteState.stageLabel ?? '正在等待推演结果返回'}</p>
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
          className="h-full min-h-0 overflow-y-auto p-5 space-y-4 custom-scrollbar"
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
                ? 'rewrite-target rounded-[18px] bg-[linear-gradient(135deg,#dff6ff_0%,#eef4ff_48%,#fdfcff_100%)] text-black ring-1 ring-[#8fd3ff]/80 shadow-[0_10px_28px_rgba(92,173,255,0.22)]'
                : bubbleTone === 'simulation-self'
                  ? 'rounded-[18px] bg-[#d9ecff] text-black'
                  : bubbleTone === 'simulation-other'
                    ? 'rounded-[18px] bg-[#f8dce6] text-black'
                    : isSelf
                      ? 'rounded-[18px] bg-[#95ec69] text-black'
                      : 'rounded-[18px] bg-white text-black'
            const bubbleArrowClass =
              bubbleTone === 'rewrite-target'
                ? 'right-[-10px] border-l-[#eef4ff]'
                : bubbleTone === 'simulation-self'
                  ? 'right-[-10px] border-l-[#d9ecff]'
                  : bubbleTone === 'simulation-other'
                    ? 'left-[-10px] border-r-[#f8dce6]'
                    : isSelf
                      ? 'right-[-10px] border-l-[#95ec69]'
                      : 'left-[-10px] border-r-white'

            return (
              <div
                key={message.id}
                data-chat-message-id={message.id}
                className={`flex flex-col transition-opacity duration-200 ${
                  message.ghosted ? 'pointer-events-none opacity-28 saturate-0' : ''
                } ${showCompletionMotion && rewriteState?.state === 'completed' && message.source === 'mock' ? 'rewrite-result-enter' : ''}`}
              >
                {showTime ? (
                  <div className="text-center my-2">
                    <span className="text-[12px] text-[#b4b4b4]">{message.timestampLabel}</span>
                  </div>
                ) : null}

                <div className={`flex w-full ${isSelf ? 'justify-end' : 'justify-start'}`}>
                  {!isSelf ? (
                    <img src={message.avatarUrl} alt={message.speakerName} className="mr-3 h-9 w-9 flex-shrink-0 rounded-md object-cover" />
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
                      <div className="rounded-xl rounded-tr-none border border-[#83d95b] bg-[#f7fff1] px-3 py-2 shadow-sm">
                        <textarea
                          ref={inlineEditorRef}
                          value={rewriteState.draftText}
                          onChange={(event) => onChangeRewriteDraft?.(event.target.value)}
                          onBlur={() => {
                            onSubmitRewrite?.()
                          }}
                          onKeyDown={handleRewriteEditorKeyDown}
                          className="min-h-[56px] w-[min(420px,60vw)] resize-none bg-transparent text-[14px] leading-relaxed text-[#111] outline-none"
                        />
                        <div className="mt-2 flex items-center justify-between text-[11px] text-[#6a6a6a]">
                          <span>回车保存并推演 · Esc 取消</span>
                          <span>点击空白处也会保存</span>
                        </div>
                        {rewriteState.errorMessage ? (
                          <p className="mt-2 text-[12px] text-[#d04b57]">{rewriteState.errorMessage}</p>
                        ) : null}
                      </div>
                    ) : (
                      <div
                        data-chat-bubble-tone={bubbleTone}
                        className={`relative break-words px-3 py-2 text-[14px] leading-relaxed shadow-sm ${bubbleClass}`}
                        style={{ wordBreak: 'break-word' }}
                      >
                        <div
                          className={`absolute top-3 h-0 w-0 border-[6px] border-transparent ${bubbleArrowClass}`}
                        />
                        {message.text}
                      </div>
                    )}
                  </div>

                  {isSelf ? (
                    <img src={message.avatarUrl} alt={message.speakerName} className="ml-3 h-9 w-9 flex-shrink-0 rounded-md object-cover" />
                  ) : null}
                </div>
              </div>
            )
          })}

          <div ref={messagesEndRef} />
        </div>
      </div>

      <div className="h-[160px] border-t border-[#e5e5e5] bg-[#f5f5f5] flex flex-col flex-shrink-0">
        <div className="h-10 px-4 flex items-center gap-4 text-[#666]">
          <button type="button" className="hover:text-[#333] transition-colors" aria-label="表情">
            <Smile size={20} />
          </button>
          <button type="button" className="hover:text-[#333] transition-colors" aria-label="文件">
            <Folder size={20} />
          </button>
          <button type="button" className="hover:text-[#333] transition-colors" aria-label="截图">
            <Scissors size={20} />
          </button>
          <button type="button" className="hover:text-[#333] transition-colors" aria-label="消息">
            <MessageSquare size={20} />
          </button>
          <button type="button" className="hover:text-[#333] transition-colors" aria-label="通话">
            <Phone size={20} />
          </button>
        </div>

        <div className="flex-1 px-4">
          <textarea
            value={inputText}
            onChange={(event) => setInputText(event.target.value)}
            onKeyDown={handleComposerKeyDown}
            className="w-full h-full bg-transparent border-none outline-none resize-none text-[14px] text-[#333] custom-scrollbar"
            placeholder="输入消息…"
          />
        </div>

        <div className="px-4 pb-3 flex justify-end">
          <button
            type="button"
            onClick={handleSend}
            className="bg-[#e9e9e9] hover:bg-[#d2d2d2] text-[#07c160] px-6 py-1.5 rounded text-[14px] transition-colors font-medium"
          >
            发送(S)
          </button>
        </div>
      </div>
    </div>
  )
}

function HeaderProgressBar({ progress }: { progress: FrontAnalysisProgress }) {
  const fillClass = progress.tone === 'failed' ? 'bg-[#e34d59]' : 'bg-[#07c160]'
  const textClass = progress.tone === 'failed' ? 'text-[#c1535d]' : 'text-[#5f6b66]'

  return (
    <div className="front-progress border-t border-[#ebebeb] px-5 py-3">
      <div className={`front-progress__meta mb-2 flex items-center justify-between text-[12px] ${textClass}`}>
        <span className="truncate font-medium">{progress.label}</span>
        <span className="ml-3 whitespace-nowrap">{progress.percent}%</span>
      </div>
      <div className="front-progress__track h-[6px] overflow-hidden rounded-full bg-[#dfdfdf]">
        <div
          className={`front-progress__fill h-full rounded-full transition-all duration-300 ${fillClass}`}
          style={{ width: `${progress.percent}%` }}
        />
      </div>
    </div>
  )
}

function MonitorLogo() {
  return (
    <svg width="120" height="120" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
      <path
        d="M4 6C4 4.89543 4.89543 4 6 4H18C19.1046 4 20 4.89543 20 6V14C20 15.1046 19.1046 16 18 16H6C4.89543 16 4 15.1046 4 14V6Z"
        stroke="#e0e0e0"
        strokeWidth="1"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <path d="M8 20H16" stroke="#e0e0e0" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
      <path d="M12 16V20" stroke="#e0e0e0" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" />
    </svg>
  )
}
