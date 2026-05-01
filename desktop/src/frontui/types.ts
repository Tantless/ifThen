export type FrontSidebarTab = 'chat' | 'contacts' | 'files'

export type FrontAnalysisStage = {
  id: string
  label: string
  status: 'waiting' | 'running' | 'completed' | 'failed'
  completedUnits: number
  totalUnits: number
  percent: number
}

export type FrontAnalysisProgress = {
  label: string
  percent: number
  tone: 'running' | 'failed'
  stages?: FrontAnalysisStage[]
}

export type FrontChatListItem = {
  id: string
  conversationId: number | null
  displayName: string
  avatarUrl: string
  previewText: string
  timestampLabel: string
  progress: FrontAnalysisProgress | null
  unreadCount: number
  active: boolean
  source: 'real' | 'mock'
}

export type FrontChatMessage = {
  id: string
  messageId: number | null
  align: 'left' | 'right'
  bubbleTone?: 'default' | 'simulation-self' | 'simulation-other' | 'rewrite-target'
  speakerName: string
  avatarUrl: string
  text: string
  timestampLabel: string
  timestampRaw: string
  canRewrite: boolean
  source: 'real' | 'mock'
  ghosted?: boolean
}

export type FrontChatWindowState =
  | { mode: 'placeholder' }
  | {
      mode: 'conversation'
      title: string
      messages: FrontChatMessage[]
    }
