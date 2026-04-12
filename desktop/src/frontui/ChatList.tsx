import { useEffect, useState } from 'react'
import { Plus, Search } from 'lucide-react'

import type { FrontAnalysisProgress, FrontChatListItem } from './types'

type FrontChatListProps = {
  items: FrontChatListItem[]
  activeChatId: number | null
  searchQuery: string
  onSearchChange: (value: string) => void
  onSelectChat: (conversationId: number) => void
  onDeleteChat: (conversationId: number) => Promise<void> | void
  onOpenImport: () => void
}

export function FrontChatList({
  items,
  activeChatId,
  searchQuery,
  onSearchChange,
  onSelectChat,
  onDeleteChat,
  onOpenImport,
}: FrontChatListProps) {
  const filteredItems = items.filter((item) => item.displayName.toLowerCase().includes(searchQuery.toLowerCase()))
  const [contextMenu, setContextMenu] = useState<{ conversationId: number; x: number; y: number } | null>(null)
  const [deletingConversationId, setDeletingConversationId] = useState<number | null>(null)

  useEffect(() => {
    if (!contextMenu) {
      return
    }

    const dismiss = () => setContextMenu(null)
    window.addEventListener('click', dismiss)
    window.addEventListener('scroll', dismiss, true)

    return () => {
      window.removeEventListener('click', dismiss)
      window.removeEventListener('scroll', dismiss, true)
    }
  }, [contextMenu])

  return (
    <div className="w-[280px] h-full bg-[#e6e5e5] border-r border-[#d6d6d6] flex flex-col flex-shrink-0 select-none">
      <div className="h-[60px] px-3 flex items-center gap-2 pt-2 bg-[#f7f7f7] border-b border-[#e5e5e5] shrink-0">
        <div className="flex-1 h-8 bg-[#e2e2e2] rounded flex items-center px-2">
          <Search size={14} className="text-[#8c8c8c] mr-1" />
          <input
            type="text"
            placeholder="搜索"
            className="bg-transparent border-none outline-none text-sm w-full placeholder:text-[#8c8c8c] text-[#333]"
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </div>
        <button
          type="button"
          className="w-8 h-8 bg-[#e2e2e2] rounded flex items-center justify-center hover:bg-[#d1d1d1] transition-colors"
          onClick={onOpenImport}
          aria-label="导入聊天记录"
        >
          <Plus size={18} className="text-[#666]" />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {contextMenu ? (
          <div
            className="fixed z-30 min-w-[120px] rounded-xl border border-black/8 bg-white/96 p-1 shadow-[0_10px_28px_rgba(0,0,0,0.18)] backdrop-blur"
            style={{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }}
          >
            <button
              type="button"
              className="w-full rounded-lg px-3 py-2 text-left text-[13px] text-[#b42318] hover:bg-[#fef3f2] disabled:cursor-not-allowed disabled:opacity-60"
              disabled={deletingConversationId === contextMenu.conversationId}
              onClick={async () => {
                setDeletingConversationId(contextMenu.conversationId)
                try {
                  await onDeleteChat(contextMenu.conversationId)
                  setContextMenu(null)
                } finally {
                  setDeletingConversationId((current) => (current === contextMenu.conversationId ? null : current))
                }
              }}
            >
              {deletingConversationId === contextMenu.conversationId ? '删除中…' : '删除会话'}
            </button>
          </div>
        ) : null}

        {filteredItems.map((item) => {
          const isActive = item.conversationId !== null && activeChatId === item.conversationId
          return (
            <button
              key={item.id}
              type="button"
              onClick={() => {
                setContextMenu(null)
                item.conversationId !== null && onSelectChat(item.conversationId)
              }}
              onContextMenu={(event) => {
                if (item.conversationId === null) {
                  return
                }

                event.preventDefault()
                setContextMenu({
                  conversationId: item.conversationId,
                  x: event.clientX,
                  y: event.clientY,
                })
              }}
              className={`w-full text-left flex items-center p-3 cursor-pointer ${
                isActive ? 'bg-[#c6c5c4]' : 'hover:bg-[#d8d8d8]'
              }`}
            >
              <div className="relative">
                <img src={item.avatarUrl} alt={item.displayName} className="w-10 h-10 rounded-md object-cover" />
                {item.unreadCount > 0 ? (
                  <div className="absolute -top-1.5 -right-1.5 bg-[#f43530] text-white text-[10px] w-[18px] h-[18px] rounded-full flex items-center justify-center font-semibold">
                    {item.unreadCount}
                  </div>
                ) : null}
              </div>
              <div className="ml-3 flex-1 min-w-0">
                <div className="flex justify-between items-baseline mb-1">
                  <h3 className="text-[14px] text-[#111] font-normal truncate">{item.displayName}</h3>
                  <span className="text-[12px] text-[#999] whitespace-nowrap ml-2">{item.timestampLabel}</span>
                </div>
                <p className="text-[12px] text-[#999] truncate w-full">{item.previewText}</p>
                {item.progress ? <ProgressBar progress={item.progress} compact /> : null}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function ProgressBar({ progress, compact = false }: { progress: FrontAnalysisProgress; compact?: boolean }) {
  const trackClass = compact ? 'mt-2' : 'mt-3'
  const fillClass = progress.tone === 'failed' ? 'bg-[#e34d59]' : 'bg-[#07c160]'
  const textClass = progress.tone === 'failed' ? 'text-[#c1535d]' : 'text-[#5f6b66]'

  return (
    <div className={`front-progress ${trackClass}`}>
      <div className={`front-progress__meta mb-1 flex items-center justify-between text-[11px] ${textClass}`}>
        <span className="truncate">{progress.label}</span>
        <span className="ml-2 whitespace-nowrap">{progress.percent}%</span>
      </div>
      <div className="front-progress__track h-[3px] overflow-hidden rounded-full bg-[#d8d8d8]">
        <div
          className={`front-progress__fill h-full rounded-full transition-all duration-300 ${fillClass}`}
          style={{ width: `${progress.percent}%` }}
        />
      </div>
    </div>
  )
}
