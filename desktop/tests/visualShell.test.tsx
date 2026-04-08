import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { AppShell } from '../src/components/AppShell'
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
})
