import { Users } from 'lucide-react'

type Contact = {
  id: string
  name: string
  avatarUrl: string
  conversationId: number | null
  lastMessageTime?: string
}

type ContactsListProps = {
  contacts: Contact[]
  onSelectContact: (conversationId: number) => void
}

export function ContactsList({ contacts, onSelectContact }: ContactsListProps) {
  if (contacts.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-[var(--if-text-tertiary)]">
        <Users size={64} className="mb-4 opacity-30" />
        <p className="text-sm">暂无联系人</p>
        <p className="mt-2 text-xs">导入聊天记录后会自动生成联系人列表</p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      {contacts.map((contact) => (
        <button
          key={contact.id}
          type="button"
          onClick={() => contact.conversationId && onSelectContact(contact.conversationId)}
          className="flex w-full cursor-pointer items-center gap-3 border-b border-[color:var(--if-divider)] px-4 py-3 text-left transition-colors duration-150 hover:bg-white/36"
          disabled={!contact.conversationId}
        >
          <img src={contact.avatarUrl} alt={contact.name} className="h-10 w-10 flex-shrink-0 rounded-[10px] object-cover ring-1 ring-black/4" />
          <div className="flex-1 min-w-0 text-left">
            <div className="truncate text-sm font-medium text-[var(--if-text-primary)]">{contact.name}</div>
            {contact.lastMessageTime && (
              <div className="mt-1 text-xs text-[var(--if-text-secondary)]">最后聊天: {contact.lastMessageTime}</div>
            )}
          </div>
        </button>
      ))}
    </div>
  )
}
