import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { ImportDialog } from '../src/components/ImportDialog'
import { SettingsDrawer } from '../src/components/SettingsDrawer'
import { WelcomeModal } from '../src/components/WelcomeModal'

describe('desktop modal chrome', () => {
  it('renders welcome and import surfaces with shared desktop modal wrappers', () => {
    const welcome = renderToStaticMarkup(
      <WelcomeModal
        open
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
        initialState={{ baseUrl: '', apiKey: '', chatModel: '' }}
        onClose={() => undefined}
        onSave={() => undefined}
      />,
    )

    expect(html).toContain('desktop-drawer')
    expect(html).toContain('desktop-drawer__header')
  })
})
