import { readFileSync } from 'node:fs'

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
    expect(importDialog).toContain('desktop-modal__panel--import')
  })

  it('keeps shared modals viewport-bound and gives import dialog more horizontal room', () => {
    const stylesheet = readFileSync(new URL('../src/styles.css', import.meta.url), 'utf8')

    expect(stylesheet).toMatch(/\.desktop-modal\s*\{[^}]*padding:\s*clamp\(12px,\s*3vw,\s*24px\);/s)
    expect(stylesheet).toMatch(/\.desktop-modal\s*\{[^}]*overflow-y:\s*auto;/s)
    expect(stylesheet).toMatch(/\.desktop-modal__panel\s*\{[^}]*width:\s*min\(640px,\s*100%\);/s)
    expect(stylesheet).toMatch(/\.desktop-modal__panel\s*\{[^}]*max-height:\s*calc\(100dvh - 24px\);/s)
    expect(stylesheet).toMatch(/\.desktop-modal__panel\s*\{[^}]*overflow-y:\s*auto;/s)
    expect(stylesheet).toMatch(/\.desktop-modal__panel--import\s*\{[^}]*width:\s*min\(860px,\s*100%\);/s)
  })

  it('renders avatar choices as filled square image buttons', () => {
    const stylesheet = readFileSync(new URL('../src/styles.css', import.meta.url), 'utf8')

    expect(stylesheet).toMatch(/\.avatar-picker__grid\s*\{[^}]*grid-template-columns:\s*repeat\(auto-fill,\s*minmax\(58px,\s*1fr\)\);/s)
    expect(stylesheet).toMatch(/\.avatar-picker__option\s*\{[^}]*aspect-ratio:\s*1;/s)
    expect(stylesheet).toMatch(/\.avatar-picker__option\s*\{[^}]*padding:\s*0;/s)
    expect(stylesheet).toMatch(/\.avatar-picker__option\s*\{[^}]*overflow:\s*hidden;/s)
    expect(stylesheet).toMatch(/\.avatar-picker__option-image\s*\{[^}]*width:\s*100%;/s)
    expect(stylesheet).toMatch(/\.avatar-picker__option-image\s*\{[^}]*height:\s*100%;/s)
  })

  it('keeps import-only as the only actionable mode until analysis model settings are configured', () => {
    const html = renderToStaticMarkup(
      <ImportDialog open canAutoAnalyze={false} onClose={() => undefined} onSubmit={() => undefined} />,
    )

    expect(html).toContain('value="import_only"')
    expect(html).toContain('value="import_and_analyze" disabled=""')
    expect(html).toContain('请先在设置中完成分析模型配置')
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

    expect(html).toContain('desktop-drawer-shell')
    expect(html).toContain('desktop-drawer')
    expect(html).toContain('desktop-drawer__header')
    expect(html).toContain('>保存<')
    expect(html).not.toContain('>关闭<')
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
        activeTab="all"
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
    expect(html).not.toContain('>文件<')
    expect(html).not.toContain('>日期<')
    expect(html).not.toContain('默认按时间倒序展示')
    expect(html).toContain('打开聊天记录日期选择')
    expect(html).not.toContain('data-chat-history-date="2026-04-01"')
    expect(html).toContain('定位到此位置')
  })

  it('keeps chat-history grouping on the raw calendar day even when timestamps carry a UTC suffix', () => {
    const html = renderToStaticMarkup(
      <ChatHistoryDialog
        open
        conversationTitle="阿青"
        keyword=""
        dateValue="2026-03-02"
        availableDates={[{ date: '2026-03-02', message_count: 1 }]}
        results={[
          {
            id: 99,
            sequence_no: 99,
            speaker_name: '阿青',
            speaker_role: 'other',
            timestamp: '2026-03-02T20:18:03Z',
            content_text: '这条消息的日期不能跳到 3 月 3 日',
            message_type: 'text',
            resource_items: null,
          },
        ]}
        loading={false}
        errorMessage={null}
        hasMore={false}
        activeTab="all"
        locatePendingMessageId={null}
        onClose={() => undefined}
        onTabChange={() => undefined}
        onKeywordChange={() => undefined}
        onDateChange={() => undefined}
        onLoadMore={() => undefined}
        onLocate={() => undefined}
      />,
    )

    expect(html).toContain('3月2日')
    expect(html).toContain('20:18')
    expect(html).not.toContain('3月3日')
    expect(html).not.toContain('04:18')
  })

  it('groups imported space-separated timestamps by day instead of treating each raw timestamp as a unique label', () => {
    const html = renderToStaticMarkup(
      <ChatHistoryDialog
        open
        conversationTitle="阿青"
        keyword=""
        dateValue=""
        availableDates={[{ date: '2025-03-02', message_count: 2 }]}
        results={[
          {
            id: 1,
            sequence_no: 1,
            speaker_name: '阿青',
            speaker_role: 'other',
            timestamp: '2025-03-02 20:18:03',
            content_text: '第一条',
            message_type: 'text',
            resource_items: null,
          },
          {
            id: 2,
            sequence_no: 2,
            speaker_name: '我',
            speaker_role: 'self',
            timestamp: '2025-03-02 20:19:03',
            content_text: '第二条',
            message_type: 'text',
            resource_items: null,
          },
        ]}
        loading={false}
        errorMessage={null}
        hasMore={false}
        activeTab="all"
        locatePendingMessageId={null}
        onClose={() => undefined}
        onTabChange={() => undefined}
        onKeywordChange={() => undefined}
        onDateChange={() => undefined}
        onLoadMore={() => undefined}
        onLocate={() => undefined}
      />,
    )

    expect(html).toContain('3月2日')
    expect(html).toContain('20:18')
    expect(html).toContain('20:19')
    expect(html).not.toContain('2025-03-02 20:18:03')
    expect(html).not.toContain('2025-03-02 20:19:03')
  })

  it('keeps the sticky day separator aligned with its resting position instead of jumping upward on scroll', () => {
    const stylesheet = readFileSync(new URL('../src/styles.css', import.meta.url), 'utf8')

    expect(stylesheet).toMatch(/\.chat-history-modal__results\s*\{[^}]*padding:\s*0 20px 20px;/s)
    expect(stylesheet).toMatch(/\.chat-history-modal__group-label\s*\{[^}]*top:\s*0;/s)
  })
})
