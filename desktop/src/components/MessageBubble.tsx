import type { MessageBubbleModel } from '../lib/adapters'

type MessageBubbleProps = {
  message: MessageBubbleModel
  onRewrite?: (message: MessageBubbleModel) => void
}

export function MessageBubble({ message, onRewrite }: MessageBubbleProps) {
  return (
    <article className={`message-bubble message-bubble--${message.align}`}>
      <div className="message-bubble__card">
        <div className="message-bubble__meta">
          <strong>{message.speakerName}</strong>
          <span>{new Date(message.timestamp).toLocaleString('zh-CN')}</span>
        </div>
        <p>{message.text || '（空消息）'}</p>
        {message.canRewrite && onRewrite ? (
          <div className="message-bubble__actions message-bubble__actions--hover">
            <button
              type="button"
              className="message-bubble__rewrite-button"
              onClick={() => onRewrite(message)}
            >
              改写并推演
            </button>
          </div>
        ) : null}
      </div>
    </article>
  )
}
