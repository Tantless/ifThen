import type { ConversationListItem as ConversationListItemModel } from '../lib/adapters'

type ConversationListItemProps = {
  item: ConversationListItemModel
  active?: boolean
  onSelect: (conversationId: number) => void
}

export function ConversationListItem({ item, active = false, onSelect }: ConversationListItemProps) {
  return (
    <button
      type="button"
      className={`conversation-list-item${active ? ' conversation-list-item--active' : ''}`}
      onClick={() => onSelect(item.id)}
    >
      <div className="conversation-list-item__top">
        <strong>{item.title}</strong>
        <span className="conversation-list-item__status">{item.statusLabel}</span>
      </div>
      <span className="conversation-list-item__meta">{item.secondaryText}</span>
    </button>
  )
}
