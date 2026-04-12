import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { ChatHistoryDialog } from '../src/components/ChatHistoryDialog'
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
        initialState={{
          baseUrl: '',
          apiKey: '',
          chatModel: '',
          simulationBaseUrl: '',
          simulationApiKey: '',
          simulationModel: '',
          simulationMode: 'single_reply',
          simulationTurnCount: 1,
          selfAvatarUrl: 'data:image/svg+xml;base64,self-avatar',
        }}
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

  it('renders the chat-history search modal inside the shared desktop modal shell', () => {
    const html = renderToStaticMarkup(
      <ChatHistoryDialog
        open
        conversationTitle="阿青"
        keyword="电影"
        dateValue="2026-04-01"
        availableDates={[
          { date: '2026-04-01', message_count: 2 },
          { date: '2026-04-03', message_count: 1 },
        ]}
        results={[
          {
            id: 12,
            sequence_no: 12,
            speaker_name: '阿青',
            speaker_role: 'other',
            timestamp: '2026-04-01T20:18:03',
            content_text: '今晚一起看电影吗',
            message_type: 'text',
            resource_items: null,
          },
        ]}
        loading={false}
        errorMessage={null}
        hasMore
        activeTab="date"
        locatePendingMessageId={null}
        onClose={() => undefined}
        onTabChange={() => undefined}
        onKeywordChange={() => undefined}
        onDateChange={() => undefined}
        onLoadMore={() => undefined}
        onLocate={() => undefined}
      />,
    )

    expect(html).toContain('desktop-modal__panel')
    expect(html).toContain('聊天记录 - 阿青')
    expect(html).toContain('placeholder="搜索"')
    expect(html).toContain('全部')
    expect(html).toContain('文件')
    expect(html).toContain('日期')
    expect(html).not.toContain('默认按时间倒序展示')
    expect(html).not.toContain('type="date"')
    expect(html).toContain('data-chat-history-date="2026-04-01"')
    expect(html).toContain('data-chat-history-date="2026-04-02"')
    expect(html).toContain('chat-history-modal__calendar-day--disabled')
    expect(html).toContain('定位到此位置')
  })
})
