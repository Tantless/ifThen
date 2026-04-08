import React from 'react'
import { readFileSync } from 'node:fs'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { AppShell } from '../src/components/AppShell'
import { BootScreen } from '../src/components/BootScreen'
import { SidebarNav } from '../src/components/SidebarNav'

describe('desktop shell chrome', () => {
  it('renders dedicated window, nav, list, and chat surface wrappers', () => {
    const html = renderToStaticMarkup(
      <AppShell sidebar={<SidebarNav />} listPane={<div>list</div>} chatPane={<div>chat</div>} />,
    )

    expect(html).toContain('desktop-window')
    expect(html).toContain('desktop-window__sidebar')
    expect(html).toContain('desktop-window__list')
    expect(html).toContain('desktop-window__chat')
  })

  it('keeps sidebar brand and settings affordance for desktop-app framing', () => {
    const html = renderToStaticMarkup(<SidebarNav />)

    expect(html).toContain('sidebar-nav__brand')
    expect(html).toContain('sidebar-nav__footer')
  })

  it('keeps boot chrome safe from desktop-window global side effects', () => {
    const html = renderToStaticMarkup(<BootScreen label="加载中" detail="准备启动" />)
    const styles = readFileSync(new URL('../src/styles.css', import.meta.url), 'utf8')

    expect(html).toContain('boot-screen')
    expect(html).toContain('boot-card')
    expect(styles).not.toMatch(/#root\s*\{[^}]*padding\s*:/s)
    expect(styles).toMatch(/\.boot-card(?:\s+h1)?\s*\{[^}]*color\s*:/s)
  })
})
