import type { MessageBubbleModel } from '../lib/adapters'

type MessageBubbleProps = {
  message: MessageBubbleModel
}

export function MessageBubble({ message }: MessageBubbleProps) {
  return (
    <article className={`message-bubble message-bubble--${message.align}`}>
      <div className="message-bubble__card">
        <div className="message-bubble__meta">
          <strong>{message.speakerName}</strong>
          <span>{new Date(message.timestamp).toLocaleString('zh-CN')}</span>
        </div>
        <p>{message.text || '（空消息）'}</p>
        {message.canRewrite ? (
          <span className="message-bubble__rewrite-hint">可在后续任务中改写推演</span>
        ) : null}
      </div>
    </article>
  )
}
