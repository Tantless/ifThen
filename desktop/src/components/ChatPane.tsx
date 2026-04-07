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
      <ChatHeader
        title={title}
        subtitle={subtitle ?? ''}
        status={status}
        progressPercent={progressPercent}
      />
      {messages.length === 0 ? (
        <div className="chat-pane__empty">
          <p>当前会话还没有可显示的历史消息。</p>
        </div>
      ) : (
        <MessageTimeline messages={messages} />
      )}
    </section>
  )
}
