import type { ReactNode } from 'react'

type AppShellProps = {
  sidebar: ReactNode
  listPane: ReactNode
  chatPane: ReactNode
}

export function AppShell({ sidebar, listPane, chatPane }: AppShellProps) {
  return (
    <main className="desktop-window">
      <aside className="desktop-window__sidebar">{sidebar}</aside>
      <section className="desktop-window__list">{listPane}</section>
      <section className="desktop-window__chat">{chatPane}</section>
    </main>
  )
}
