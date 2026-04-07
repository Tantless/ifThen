import type { MessageBubbleModel } from '../lib/adapters'
import { MessageBubble } from './MessageBubble'

type MessageTimelineProps = {
  messages: MessageBubbleModel[]
}

export function MessageTimeline({ messages }: MessageTimelineProps) {
  return (
    <div className="message-timeline">
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
    </div>
  )
}
