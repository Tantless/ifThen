import type { MessageBubbleModel } from '../lib/adapters'
import { MessageBubble } from './MessageBubble'

type MessageTimelineProps = {
  messages: MessageBubbleModel[]
  onRewriteMessage?: (message: MessageBubbleModel) => void
}

export function MessageTimeline({ messages, onRewriteMessage }: MessageTimelineProps) {
  return (
    <div className="message-timeline">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} onRewrite={onRewriteMessage} />
      ))}
    </div>
  )
}
