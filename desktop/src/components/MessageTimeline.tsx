import type { MessageBubbleModel } from '../lib/adapters'
import { MessageBubble } from './MessageBubble'

type MessageTimelineProps = {
  messages: MessageBubbleModel[]
  onRewriteMessage?: (message: MessageBubbleModel) => void
}

export function MessageTimeline({ messages, onRewriteMessage }: MessageTimelineProps) {
  return (
    <section className="message-timeline" aria-label="消息时间线">
      <div className="message-timeline__items">
        {messages.map((message) => (
          <MessageBubble key={message.id} message={message} onRewrite={onRewriteMessage} />
        ))}
      </div>
    </section>
  )
}
