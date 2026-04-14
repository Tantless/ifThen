import { MessageSquare, Settings } from 'lucide-react'

import type { FrontSidebarTab } from './types'

type FrontSidebarProps = {
  activeTab: FrontSidebarTab
  selfAvatarUrl: string
  onOpenAvatarDialog: () => void
  onTabChange: (tab: FrontSidebarTab) => void
  onOpenSettings: () => void
}

export function FrontSidebar({ activeTab, selfAvatarUrl, onOpenAvatarDialog, onTabChange, onOpenSettings }: FrontSidebarProps) {
  return (
    <div className="flex h-full w-[64px] flex-shrink-0 flex-col items-center border-r border-white/6 bg-[var(--if-bg-sidebar)] py-5 select-none">
      <button
        type="button"
        className="mb-5 rounded-xl p-1 transition-colors duration-150 hover:bg-white/8 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(7,193,96,0.28)]"
        onClick={onOpenAvatarDialog}
        aria-label="打开头像设置"
      >
        <img src={selfAvatarUrl} alt="当前用户头像" className="h-10 w-10 rounded-xl object-cover ring-1 ring-white/10" />
      </button>

      <div className="mt-2 flex w-full flex-1 flex-col items-center gap-4">
        <button
          type="button"
          onClick={() => onTabChange('chat')}
          className={`relative rounded-xl p-2.5 transition-colors duration-150 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(7,193,96,0.28)] ${
            activeTab === 'chat' ? 'bg-white/10' : 'hover:bg-white/6'
          }`}
          aria-label="聊天"
        >
          <MessageSquare
            size={26}
            className={
              activeTab === 'chat'
                ? 'fill-[var(--if-accent)] text-[var(--if-accent)]'
                : 'text-[#9e968d] hover:text-[#d6cfc6]'
            }
          />
        </button>
      </div>

      <div className="flex flex-col items-center gap-4">
        <button
          type="button"
          className="group rounded-xl p-2.5 outline-none transition-colors duration-150 hover:bg-white/6 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(7,193,96,0.28)]"
          onClick={onOpenSettings}
          aria-label="设置"
        >
          <Settings size={22} className="text-[#9e968d] transition-colors duration-150 group-hover:text-[#d6cfc6]" />
        </button>
      </div>
    </div>
  )
}
