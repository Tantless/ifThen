import type { ConversationListItem as ConversationListItemModel } from '../lib/adapters'

type ConversationListItemProps = {
  item: ConversationListItemModel
  active?: boolean
  onSelect: (conversationId: number) => void
}

export function ConversationListItem({ item, active = false, onSelect }: ConversationListItemProps) {
  const avatarLabel = item.title.trim().charAt(0) || '聊'

  return (
    <button
      type="button"
      className={`conversation-list-item${active ? ' conversation-list-item--active' : ''}`}
      onClick={() => onSelect(item.id)}
    >
      <span className="conversation-list-item__avatar" aria-hidden="true">
        {avatarLabel}
      </span>
      <div className="conversation-list-item__content">
        <div className="conversation-list-item__top">
          <strong>{item.title}</strong>
          <span className="conversation-list-item__status">{item.statusLabel}</span>
        </div>
        <span className="conversation-list-item__meta">{item.secondaryText}</span>
      </div>
    </button>
  )
}
