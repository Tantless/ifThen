import type { ReactNode } from 'react'

type FrontAppShellProps = {
  titleBar?: ReactNode
  sidebar: ReactNode
  list: ReactNode
  window: ReactNode
  aside?: ReactNode
}

export function FrontAppShell({ titleBar, sidebar, list, window, aside }: FrontAppShellProps) {
  return (
    <div className="desktop-shell-root h-screen w-screen overflow-hidden bg-[var(--if-bg-app)]">
      <div className="desktop-shell-main flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden bg-[var(--if-bg-window)] text-[var(--if-text-primary)]">
        {titleBar ? <div className="desktop-shell-titlebar">{titleBar}</div> : null}
        <div className="flex min-h-0 min-w-0 flex-1 overflow-hidden">
          {sidebar}
          {list}
          {window}
          {aside}
        </div>
      </div>
    </div>
  )
}
