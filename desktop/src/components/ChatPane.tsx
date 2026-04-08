import type { ReactNode } from 'react'
import type { MessageBubbleModel } from '../lib/adapters'
import { ChatHeader } from './ChatHeader'
import { ConversationEmptyState } from './ConversationEmptyState'
import { MessageTimeline } from './MessageTimeline'

type ChatPaneProps = {
  title?: string
  subtitle?: string
  status?: string | null
  progressPercent?: number | null
  messages: MessageBubbleModel[]
  loading?: boolean
  error?: boolean
  emptyVariant?: 'empty' | 'welcome'
  headerActions?: ReactNode
  detailPanel?: ReactNode
  children?: ReactNode
  onRewriteMessage?: (message: MessageBubbleModel) => void
}

export function ChatPane({
  title,
  subtitle,
  status,
  progressPercent,
  messages,
  loading = false,
  error = false,
  emptyVariant = 'empty',
  headerActions,
  detailPanel,
  children,
  onRewriteMessage,
}: ChatPaneProps) {
  if (loading) {
    return <ConversationEmptyState variant="loading" />
  }

  if (error) {
    return <ConversationEmptyState variant="error" />
  }

  if (!title) {
    return <ConversationEmptyState variant={emptyVariant} />
  }

  return (
    <section className="chat-pane">
      <div className="chat-pane__surface">
        <ChatHeader
          title={title}
          subtitle={subtitle ?? ''}
          status={status}
          progressPercent={progressPercent}
          actions={headerActions}
        />
        <div className={`chat-pane__body${detailPanel ? ' chat-pane__body--split' : ''}`}>
          <div className="chat-pane__main">
            {children ?? (
              messages.length === 0 ? (
                <div className="chat-pane__empty">
                  <p>当前会话还没有可显示的历史消息。</p>
                </div>
              ) : (
                <MessageTimeline messages={messages} onRewriteMessage={onRewriteMessage} />
              )
            )}
          </div>
          {detailPanel}
        </div>
      </div>
    </section>
  )
}
