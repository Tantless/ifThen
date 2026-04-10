import { Folder, MessageSquare, MonitorPlay, Settings, Smartphone, Users } from 'lucide-react'

import { FRONTUI_SELF_AVATAR } from './mockState'
import type { FrontSidebarTab } from './types'

type FrontSidebarProps = {
  activeTab: FrontSidebarTab
  onTabChange: (tab: FrontSidebarTab) => void
  onOpenSettings: () => void
  onOpenImport: () => void
}

export function FrontSidebar({ activeTab, onTabChange, onOpenSettings, onOpenImport }: FrontSidebarProps) {
  return (
    <div className="w-[60px] h-full bg-[#2e2e2e] flex flex-col items-center py-6 select-none flex-shrink-0">
      <button type="button" className="mb-6 cursor-pointer" onClick={() => onTabChange('chat')} aria-label="返回聊天列表">
        <img src={FRONTUI_SELF_AVATAR} alt="当前用户头像" className="w-10 h-10 rounded-md object-cover" />
      </button>

      <div className="flex flex-col gap-6 flex-1 w-full items-center mt-2">
        <button type="button" onClick={() => onTabChange('chat')} className="p-2 relative outline-none" aria-label="聊天">
          <MessageSquare
            size={26}
            className={activeTab === 'chat' ? 'text-[#07c160] fill-[#07c160]' : 'text-[#8c8c8c] hover:text-[#b0b0b0]'}
          />
        </button>
        <button type="button" onClick={() => onTabChange('contacts')} className="p-2 relative outline-none" aria-label="联系人">
          <Users
            size={26}
            className={activeTab === 'contacts' ? 'text-[#07c160] fill-[#07c160]' : 'text-[#8c8c8c] hover:text-[#b0b0b0]'}
          />
        </button>
        <button type="button" onClick={() => onTabChange('files')} className="p-2 relative outline-none" aria-label="文件">
          <Folder
            size={26}
            className={activeTab === 'files' ? 'text-[#07c160] fill-[#07c160]' : 'text-[#8c8c8c] hover:text-[#b0b0b0]'}
          />
        </button>
      </div>

      <div className="flex flex-col gap-4 items-center">
        <button type="button" className="p-2 outline-none group" onClick={onOpenImport} aria-label="导入聊天记录">
          <MonitorPlay size={22} className="text-[#8c8c8c] group-hover:text-[#b0b0b0]" />
        </button>
        <button type="button" className="p-2 outline-none group" aria-label="移动端同步（待实现）">
          <Smartphone size={22} className="text-[#8c8c8c] group-hover:text-[#b0b0b0]" />
        </button>
        <button type="button" className="p-2 outline-none group" onClick={onOpenSettings} aria-label="设置">
          <Settings size={22} className="text-[#8c8c8c] group-hover:text-[#b0b0b0]" />
        </button>
      </div>
    </div>
  )
}
