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
      <div className="flex flex-col items-center justify-center h-full text-[#999]">
        <Users size={64} className="mb-4 opacity-30" />
        <p className="text-sm">暂无联系人</p>
        <p className="text-xs mt-2">导入聊天记录后会自动生成联系人列表</p>
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
          className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[#f5f5f5] transition-colors cursor-pointer border-b border-[#e5e5e5]"
          disabled={!contact.conversationId}
        >
          <img src={contact.avatarUrl} alt={contact.name} className="w-10 h-10 rounded-md object-cover flex-shrink-0" />
          <div className="flex-1 min-w-0 text-left">
            <div className="text-sm font-medium text-[#333] truncate">{contact.name}</div>
            {contact.lastMessageTime && (
              <div className="text-xs text-[#999] mt-1">最后聊天: {contact.lastMessageTime}</div>
            )}
          </div>
        </button>
      ))}
    </div>
  )
}
