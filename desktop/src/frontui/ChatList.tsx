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
    <div className="flex h-full w-[280px] flex-shrink-0 flex-col border-r border-[color:var(--if-divider)] bg-[var(--if-bg-secondary)] select-none">
      <div className="flex h-14 shrink-0 items-center gap-2 border-b border-[color:var(--if-divider)] bg-[var(--if-bg-panel)] px-3">
        <div className="flex h-8 flex-1 items-center rounded-[8px] border border-[color:var(--if-divider)] bg-white/72 px-2 text-[var(--if-text-secondary)]">
          <Search size={14} className="mr-1 text-[var(--if-text-tertiary)]" />
          <input
            type="text"
            placeholder="搜索"
            className="w-full border-none bg-transparent text-[13px] text-[var(--if-text-primary)] outline-none placeholder:text-[var(--if-text-tertiary)]"
            value={searchQuery}
            onChange={(event) => onSearchChange(event.target.value)}
          />
        </div>
        <button
          type="button"
          className="flex h-8 w-8 items-center justify-center rounded-[8px] border border-[color:var(--if-divider)] bg-white/72 text-[var(--if-text-secondary)] transition-colors duration-150 hover:bg-white hover:text-[var(--if-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(7,193,96,0.18)]"
          onClick={onOpenImport}
          aria-label="导入聊天记录"
        >
          <Plus size={16} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto custom-scrollbar">
        {contextMenu ? (
          <div
            className="fixed z-30 min-w-[132px] rounded-[10px] border border-[color:var(--if-divider-strong)] bg-white/96 p-1 shadow-[var(--if-shadow-popover)] backdrop-blur"
            style={{ left: `${contextMenu.x}px`, top: `${contextMenu.y}px` }}
          >
            <button
              type="button"
              className="w-full rounded-[8px] px-3 py-2 text-left text-[13px] text-[var(--if-danger)] transition-colors duration-150 hover:bg-[var(--if-danger-soft)] disabled:cursor-not-allowed disabled:opacity-60"
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
              className={`flex w-full items-center border-l-2 px-3 py-3 text-left transition-colors duration-150 cursor-pointer ${
                isActive
                  ? 'border-l-[var(--if-accent)] bg-white/60'
                  : 'border-l-transparent border-b border-[color:rgba(94,84,72,0.06)] hover:bg-white/36'
              }`}
            >
              <div className="relative">
                <img src={item.avatarUrl} alt={item.displayName} className="h-10 w-10 rounded-[10px] object-cover ring-1 ring-black/4" />
                {item.unreadCount > 0 ? (
                  <div className="absolute -right-1.5 -top-1.5 flex h-[18px] w-[18px] items-center justify-center rounded-full bg-[#d04b57] text-[10px] font-semibold text-white">
                    {item.unreadCount}
                  </div>
                ) : null}
              </div>
              <div className="ml-3 flex-1 min-w-0">
                <div className="flex justify-between items-baseline mb-1">
                  <h3 className="truncate text-[14px] font-medium text-[var(--if-text-primary)]">{item.displayName}</h3>
                  <span className="ml-2 whitespace-nowrap text-[11px] text-[var(--if-text-tertiary)]">{item.timestampLabel}</span>
                </div>
                <p className="w-full truncate text-[12px] text-[var(--if-text-secondary)]">{item.previewText}</p>
                {item.progress ? <ProgressStatus progress={item.progress} compact /> : null}
              </div>
            </button>
          )
        })}
      </div>
    </div>
  )
}

function ProgressStatus({ progress, compact = false }: { progress: FrontAnalysisProgress; compact?: boolean }) {
  const trackClass = compact ? 'mt-2' : 'mt-3'
  const textClass = progress.tone === 'failed' ? 'text-[var(--if-danger)]' : 'text-[var(--if-text-secondary)]'

  return (
    <div className={`front-progress ${trackClass} flex items-center justify-between gap-2 text-[11px] ${textClass}`}>
      <span className="truncate">{progress.label}</span>
      <span className="shrink-0 text-[var(--if-text-tertiary)]">{progress.tone === 'failed' ? '失败' : '分析中'}</span>
    </div>
  )
}
