import type { ConversationListItem as ConversationListItemModel } from '../lib/adapters'
import { ConversationListItem } from './ConversationListItem'

type ConversationListPaneProps = {
  items: ConversationListItemModel[]
  selectedConversationId: number | null
  searchValue: string
  emptyMessage: string
  onSearchChange: (value: string) => void
  onImportConversation: () => void
  onOpenSettings: () => void
  onSelectConversation: (conversationId: number) => void
}

export function ConversationListPane({
  items,
  selectedConversationId,
  searchValue,
  emptyMessage,
  onSearchChange,
  onImportConversation,
  onOpenSettings,
  onSelectConversation,
}: ConversationListPaneProps) {
  return (
    <section className="conversation-list-pane">
      <header className="conversation-list-pane__toolbar">
        <div className="conversation-list-pane__title-group">
          <p className="conversation-list-pane__eyebrow">会话</p>
          <h2>历史聊天</h2>
        </div>
        <div className="conversation-list-pane__toolbar-actions">
          <button type="button" onClick={onOpenSettings}>
            设置
          </button>
          <button type="button" onClick={onImportConversation}>
            导入
          </button>
        </div>
      </header>

      <label className="conversation-list-pane__search-shell">
        <span className="conversation-list-pane__search-icon" aria-hidden="true">
          ⌕
        </span>
        <input
          type="search"
          value={searchValue}
          aria-label="搜索会话"
          placeholder="按标题或联系人筛选"
          onChange={(event) => onSearchChange(event.target.value)}
        />
      </label>

      <div className="conversation-list-pane__body">
        {items.length === 0 ? (
          <p className="conversation-list-pane__empty">{emptyMessage}</p>
        ) : (
          items.map((item) => (
            <ConversationListItem
              key={item.id}
              item={item}
              active={item.id === selectedConversationId}
              onSelect={onSelectConversation}
            />
          ))
        )}
      </div>
    </section>
  )
}
