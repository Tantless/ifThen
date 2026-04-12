import { useRef, type UIEvent } from 'react'

import { formatChatTimestampLabel } from '../lib/frontUiAdapters'
import type { MessageRead } from '../types/api'

const LOAD_MORE_TRIGGER_PX = 24
const LOAD_MORE_REARM_PX = 72

type ChatHistoryDialogProps = {
  open: boolean
  conversationTitle: string
  keyword: string
  dateValue: string
  results: MessageRead[]
  loading: boolean
  loadingMore?: boolean
  errorMessage: string | null
  hasMore: boolean
  locatePendingMessageId: number | null
  onClose: () => void
  onKeywordChange: (value: string) => void
  onDateChange: (value: string) => void
  onLoadMore: () => Promise<void> | void
  onLocate: (message: MessageRead) => Promise<void> | void
}

function formatResultTimestamp(timestamp: string): string {
  const parsed = new Date(timestamp)

  if (Number.isNaN(parsed.getTime())) {
    return timestamp
  }

  const hhmm = `${String(parsed.getHours()).padStart(2, '0')}:${String(parsed.getMinutes()).padStart(2, '0')}`
  return `${parsed.getFullYear()}年${parsed.getMonth() + 1}月${parsed.getDate()}日 ${hhmm}`
}

function resolveSpeakerLabel(message: MessageRead): string {
  return message.speaker_role === 'self' ? '我' : message.speaker_name.trim() || '对方'
}

export function ChatHistoryDialog({
  open,
  conversationTitle,
  keyword,
  dateValue,
  results,
  loading,
  loadingMore = false,
  errorMessage,
  hasMore,
  locatePendingMessageId,
  onClose,
  onKeywordChange,
  onDateChange,
  onLoadMore,
  onLocate,
}: ChatHistoryDialogProps) {
  const loadMoreArmedRef = useRef(true)

  if (!open) {
    return null
  }

  const handleResultsScroll = async (event: UIEvent<HTMLDivElement>) => {
    const container = event.currentTarget
    const distanceToBottom = container.scrollHeight - (container.scrollTop + container.clientHeight)

    if (distanceToBottom > LOAD_MORE_REARM_PX) {
      loadMoreArmedRef.current = true
    }

    if (!hasMore || loading || loadingMore || distanceToBottom > LOAD_MORE_TRIGGER_PX || !loadMoreArmedRef.current) {
      return
    }

    loadMoreArmedRef.current = false
    await onLoadMore()
  }

  return (
    <div className="desktop-modal" role="dialog" aria-modal="true" aria-labelledby="chat-history-dialog-title">
      <section className="desktop-modal__panel desktop-modal__panel--history">
        <header className="desktop-modal__header desktop-modal__header--split">
          <div>
            <p className="desktop-modal__eyebrow">聊天记录</p>
            <h2 id="chat-history-dialog-title" className="desktop-modal__title">
              {conversationTitle}
            </h2>
            <p className="desktop-modal__body desktop-modal__body--muted">
              默认按时间倒序展示；使用关键词或日期筛选后，会自动切换为正序结果。
            </p>
          </div>
          <button type="button" className="desktop-modal__button" onClick={onClose}>
            关闭
          </button>
        </header>

        <div className="chat-history__toolbar">
          <label className="desktop-modal__field chat-history__field">
            <span className="desktop-modal__label">关键词</span>
            <input
              type="search"
              className="desktop-modal__input"
              value={keyword}
              placeholder="搜索聊天记录"
              onChange={(event) => onKeywordChange(event.target.value)}
            />
          </label>
          <label className="desktop-modal__field chat-history__field">
            <span className="desktop-modal__label">日期</span>
            <input
              type="date"
              className="desktop-modal__input"
              value={dateValue}
              onChange={(event) => onDateChange(event.target.value)}
            />
          </label>
        </div>

        <div className="desktop-modal__content chat-history__content">
          {loading ? <p className="desktop-modal__state">正在加载聊天记录…</p> : null}
          {errorMessage ? (
            <p className="desktop-modal__state desktop-modal__state--error" role="alert">
              {errorMessage}
            </p>
          ) : null}

          {!loading && !errorMessage ? (
            results.length === 0 ? (
              <p className="desktop-modal__empty">没有匹配到聊天记录</p>
            ) : (
              <div className="chat-history__results" data-testid="chat-history-results" onScroll={(event) => void handleResultsScroll(event)}>
                {results.map((message) => {
                  const locatePending = locatePendingMessageId === message.id
                  return (
                    <article key={message.id} className="chat-history__item" data-chat-history-message-id={`history-message-${message.id}`}>
                      <div className="chat-history__meta">
                        <strong>{resolveSpeakerLabel(message)}</strong>
                        <span>{formatResultTimestamp(message.timestamp)}</span>
                      </div>
                      <p className="chat-history__text">{message.content_text}</p>
                      <div className="chat-history__footer">
                        <span className="chat-history__relative-time">{formatChatTimestampLabel(message.timestamp)}</span>
                        <button
                          type="button"
                          className="desktop-modal__button desktop-modal__button--primary"
                          onClick={() => {
                            void onLocate(message)
                          }}
                          disabled={locatePending}
                        >
                          {locatePending ? '定位中…' : '定位到此位置'}
                        </button>
                      </div>
                    </article>
                  )
                })}
                <div className="chat-history__load-state">
                  {loadingMore ? '正在加载更多…' : hasMore ? '下滑到底部继续加载 10 条' : '已展示全部匹配结果'}
                </div>
              </div>
            )
          ) : null}
        </div>
      </section>
    </div>
  )
}
