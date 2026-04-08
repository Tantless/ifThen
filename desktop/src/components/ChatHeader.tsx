import type { ReactNode } from 'react'
import { AnalysisStatusBadge } from './AnalysisStatusBadge'

type ChatHeaderProps = {
  title: string
  subtitle: string
  status?: string | null
  progressPercent?: number | null
  actions?: ReactNode
}

export function ChatHeader({ title, subtitle, status, progressPercent, actions }: ChatHeaderProps) {
  return (
    <header className="chat-header">
      <div>
        <p className="chat-header__eyebrow">当前会话</p>
        <h2>{title}</h2>
        <p className="chat-header__subtitle">{subtitle}</p>
      </div>
      <div className="chat-header__meta">
        {actions}
        <AnalysisStatusBadge status={status} progressPercent={progressPercent} />
      </div>
    </header>
  )
}
