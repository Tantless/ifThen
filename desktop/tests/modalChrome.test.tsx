import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { ImportDialog } from '../src/components/ImportDialog'
import { SelfAvatarDialog } from '../src/components/SelfAvatarDialog'
import { SettingsDrawer } from '../src/components/SettingsDrawer'
import { WelcomeModal } from '../src/components/WelcomeModal'

describe('desktop modal chrome', () => {
  it('renders welcome and import surfaces with shared desktop modal wrappers', () => {
    const welcome = renderToStaticMarkup(
      <WelcomeModal
        open
        initialSelfAvatarUrl="data:image/svg+xml;base64,welcome-avatar"
        onConfigureModel={() => undefined}
        onImportConversation={() => undefined}
        onClose={() => undefined}
      />,
    )
    const importDialog = renderToStaticMarkup(
      <ImportDialog open onClose={() => undefined} onSubmit={() => undefined} />,
    )

    expect(welcome).toContain('desktop-modal__panel')
    expect(importDialog).toContain('desktop-modal__panel')
  })

  it('renders settings inside a dedicated desktop drawer shell', () => {
    const html = renderToStaticMarkup(
      <SettingsDrawer
        open
        initialState={{ baseUrl: '', apiKey: '', chatModel: '', simulationModel: '', simulationMode: 'single_reply', simulationTurnCount: 1, selfAvatarUrl: 'data:image/svg+xml;base64,self-avatar' }}
        onClose={() => undefined}
        onSave={() => undefined}
      />,
    )

    expect(html).toContain('desktop-drawer')
    expect(html).toContain('desktop-drawer__header')
    expect(html).not.toContain('我的头像')
  })

  it('renders the self-avatar picker inside a shared desktop modal shell', () => {
    const html = renderToStaticMarkup(
      <SelfAvatarDialog
        open
        initialAvatarUrl="data:image/svg+xml;base64,self-avatar"
        onClose={() => undefined}
        onSave={() => undefined}
      />,
    )

    expect(html).toContain('desktop-modal__panel')
    expect(html).toContain('更换头像')
    expect(html).toContain('我的头像')
  })
})
