import type { ReactNode } from 'react'

type AppShellProps = {
  sidebar: ReactNode
  listPane: ReactNode
  chatPane: ReactNode
}

export function AppShell({ sidebar, listPane, chatPane }: AppShellProps) {
  return (
    <main className="desktop-shell">
      <aside className="desktop-shell__nav">{sidebar}</aside>
      <section className="desktop-shell__list">{listPane}</section>
      <section className="desktop-shell__chat">{chatPane}</section>
    </main>
  )
}
