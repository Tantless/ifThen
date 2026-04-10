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
    <div className="desktop-shell-root desktop-shell-root--windows-modern h-screen w-screen overflow-hidden bg-[#f5f5f5]">
      <div className="desktop-shell-main desktop-shell-main--windowed flex h-full w-full min-h-0 min-w-0 flex-col overflow-hidden bg-white">
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
