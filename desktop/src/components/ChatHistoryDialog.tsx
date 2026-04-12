import { Calendar, FileText, Search, X } from 'lucide-react'
import { useMemo, useRef, type UIEvent } from 'react'

import { FRONTUI_PLACEHOLDER_AVATAR, FRONTUI_SELF_AVATAR } from '../frontui/mockState'
import type { MessageRead } from '../types/api'

const LOAD_MORE_TRIGGER_PX = 24
const LOAD_MORE_REARM_PX = 72

export type ChatHistoryTab = 'all' | 'files' | 'date'

type ChatHistoryDialogProps = {
  open: boolean
  conversationTitle: string
  activeTab: ChatHistoryTab
  keyword: string
  dateValue: string
  results: MessageRead[]
  loading: boolean
  loadingMore?: boolean
  errorMessage: string | null
  hasMore: boolean
  locatePendingMessageId: number | null
  selfAvatarUrl?: string
  otherAvatarUrl?: string
  onClose: () => void
  onTabChange: (tab: ChatHistoryTab) => void
  onKeywordChange: (value: string) => void
  onDateChange: (value: string) => void
  onLoadMore: () => Promise<void> | void
  onLocate: (message: MessageRead) => Promise<void> | void
}

function parseTimestamp(timestamp: string): Date | null {
  const parsed = new Date(timestamp)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

function formatHistoryGroupLabel(timestamp: string): string {
  const parsed = parseTimestamp(timestamp)

  if (!parsed) {
    return timestamp
  }

  const now = new Date()
  const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate()).getTime()
  const startOfTarget = new Date(parsed.getFullYear(), parsed.getMonth(), parsed.getDate()).getTime()
  const dayDiff = Math.round((startOfToday - startOfTarget) / 86_400_000)

  if (dayDiff === 0) {
    return '今天'
  }

  if (dayDiff === 1) {
    return '昨天'
  }

  if (dayDiff === 2) {
    return '前天'
  }

  if (parsed.getFullYear() === now.getFullYear()) {
    return `${parsed.getMonth() + 1}月${parsed.getDate()}日`
  }

  return `${parsed.getFullYear()}年${parsed.getMonth() + 1}月${parsed.getDate()}日`
}

function formatHistoryTimeLabel(timestamp: string): string {
  const parsed = parseTimestamp(timestamp)

  if (!parsed) {
    return timestamp
  }

  return `${String(parsed.getHours()).padStart(2, '0')}:${String(parsed.getMinutes()).padStart(2, '0')}`
}

function resolveSpeakerLabel(message: MessageRead): string {
  return message.speaker_role === 'self' ? '我' : message.speaker_name.trim() || '对方'
}

function resolveMessageAvatar(message: MessageRead, selfAvatarUrl?: string, otherAvatarUrl?: string): string {
  return message.speaker_role === 'self'
    ? selfAvatarUrl || FRONTUI_SELF_AVATAR
    : otherAvatarUrl || FRONTUI_PLACEHOLDER_AVATAR
}

function buildMessageGroups(results: MessageRead[]): Array<{ label: string; messages: MessageRead[] }> {
  const groups: Array<{ label: string; messages: MessageRead[] }> = []

  for (const message of results) {
    const label = formatHistoryGroupLabel(message.timestamp)
    const previousGroup = groups[groups.length - 1]

    if (!previousGroup || previousGroup.label !== label) {
      groups.push({ label, messages: [message] })
      continue
    }

    previousGroup.messages.push(message)
  }

  return groups
}

export function ChatHistoryDialog({
  open,
  conversationTitle,
  activeTab,
  keyword,
  dateValue,
  results,
  loading,
  loadingMore = false,
  errorMessage,
  hasMore,
  locatePendingMessageId,
  selfAvatarUrl,
  otherAvatarUrl,
  onClose,
  onTabChange,
  onKeywordChange,
  onDateChange,
  onLoadMore,
  onLocate,
}: ChatHistoryDialogProps) {
  const loadMoreArmedRef = useRef(true)
  const groupedResults = useMemo(() => buildMessageGroups(results), [results])

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
    <div className="desktop-modal chat-history-modal__overlay" role="dialog" aria-modal="true" aria-labelledby="chat-history-dialog-title">
      <section className="desktop-modal__panel chat-history-modal__panel">
        <header className="chat-history-modal__header">
          <h2 id="chat-history-dialog-title" className="chat-history-modal__title">
            聊天记录 - {conversationTitle}
          </h2>
          <button type="button" className="chat-history-modal__close" aria-label="关闭聊天记录" onClick={onClose}>
            <X size={18} />
          </button>
        </header>

        <div className="chat-history-modal__body">
          <div className="chat-history-modal__main">
            <div className="chat-history-modal__toolbar">
              <label className="chat-history-modal__search" aria-label="搜索聊天记录">
                <Search size={14} className="text-[#8c8c8c]" />
                <input
                  type="text"
                  className="chat-history-modal__search-input"
                  value={keyword}
                  placeholder="搜索"
                  onChange={(event) => onKeywordChange(event.target.value)}
                />
              </label>

              <div className="chat-history-modal__tabs" role="tablist" aria-label="聊天记录筛选">
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === 'all'}
                  className={`chat-history-modal__tab${activeTab === 'all' ? ' chat-history-modal__tab--active' : ''}`}
                  onClick={() => onTabChange('all')}
                >
                  全部
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === 'files'}
                  className={`chat-history-modal__tab${activeTab === 'files' ? ' chat-history-modal__tab--active' : ''}`}
                  onClick={() => onTabChange('files')}
                >
                  文件
                </button>
                <button
                  type="button"
                  role="tab"
                  aria-selected={activeTab === 'date'}
                  className={`chat-history-modal__tab${activeTab === 'date' ? ' chat-history-modal__tab--active' : ''}`}
                  onClick={() => onTabChange('date')}
                >
                  日期
                </button>
              </div>
            </div>

            <div className="chat-history-modal__results custom-scrollbar" data-testid="chat-history-results" onScroll={(event) => void handleResultsScroll(event)}>
              {activeTab === 'date' ? (
                <div className="chat-history-modal__date-picker">
                  <Calendar size={16} className="text-[#8c8c8c]" />
                  <input
                    type="date"
                    className="chat-history-modal__date-input"
                    value={dateValue}
                    onChange={(event) => onDateChange(event.target.value)}
                  />
                </div>
              ) : null}

              {loading ? <p className="chat-history-modal__state">正在加载聊天记录…</p> : null}
              {errorMessage ? (
                <p className="chat-history-modal__state chat-history-modal__state--error" role="alert">
                  {errorMessage}
                </p>
              ) : null}

              {!loading && !errorMessage && activeTab === 'files' ? (
                <div className="chat-history-modal__empty">
                  <FileText size={18} />
                  <span>文件聊天记录暂未接入</span>
                </div>
              ) : null}

              {!loading && !errorMessage && activeTab !== 'files' && activeTab === 'date' && !dateValue && results.length === 0 ? (
                <div className="chat-history-modal__empty">
                  <Calendar size={18} />
                  <span>选择日期后查看当天聊天记录</span>
                </div>
              ) : null}

              {!loading && !errorMessage && activeTab !== 'files' && !(activeTab === 'date' && !dateValue && results.length === 0) ? (
                groupedResults.length === 0 ? (
                  <div className="chat-history-modal__empty">
                    <span>没有找到相关消息</span>
                  </div>
                ) : (
                  <>
                    {groupedResults.map((group) => (
                      <div key={group.label} className="chat-history-modal__group">
                        <div className="chat-history-modal__group-label">
                          <span>{group.label}</span>
                        </div>
                        {group.messages.map((message) => {
                          const locatePending = locatePendingMessageId === message.id
                          return (
                            <div key={message.id} className="chat-history-modal__row" data-chat-history-message-id={`history-message-${message.id}`}>
                              <img
                                src={resolveMessageAvatar(message, selfAvatarUrl, otherAvatarUrl)}
                                alt={resolveSpeakerLabel(message)}
                                className="chat-history-modal__avatar"
                              />
                              <div className="chat-history-modal__message">
                                <div className="chat-history-modal__meta">
                                  <span className="chat-history-modal__sender">{resolveSpeakerLabel(message)}</span>
                                  <span className="chat-history-modal__time">{formatHistoryTimeLabel(message.timestamp)}</span>
                                </div>
                                <div className="chat-history-modal__text">{message.content_text}</div>
                                <div className="chat-history-modal__actions">
                                  <button
                                    type="button"
                                    className="chat-history-modal__locate"
                                    onClick={() => {
                                      void onLocate(message)
                                    }}
                                    disabled={locatePending}
                                  >
                                    {locatePending ? '定位中…' : '定位到此位置'}
                                  </button>
                                </div>
                              </div>
                            </div>
                          )
                        })}
                      </div>
                    ))}

                    <div className="chat-history-modal__load-state">
                      {loadingMore ? '正在加载更多…' : hasMore ? '下滑到底部继续加载 10 条' : '没有更多消息了'}
                    </div>
                  </>
                )
              ) : null}
            </div>
          </div>
        </div>
      </section>
    </div>
  )
}
