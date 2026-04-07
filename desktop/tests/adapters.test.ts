import { describe, expect, it } from 'vitest'

import { buildConversationListItem, buildSettingsFormState } from '../src/lib/adapters'

describe('buildSettingsFormState', () => {
  it('maps persisted llm settings into the form state', () => {
    expect(
      buildSettingsFormState([
        { setting_key: 'llm.base_url', setting_value: 'https://example.test/v1', is_secret: false },
        { setting_key: 'llm.api_key', setting_value: 'secret-key', is_secret: true },
        { setting_key: 'llm.chat_model', setting_value: 'gpt-5.4', is_secret: false },
      ]),
    ).toEqual({
      baseUrl: 'https://example.test/v1',
      apiKey: 'secret-key',
      chatModel: 'gpt-5.4',
    })
  })
})

describe('buildConversationListItem', () => {
  it('shows running analysis progress in the status label', () => {
    expect(
      buildConversationListItem({
        conversation: {
          id: 7,
          title: '和小李的聊天',
          chat_type: 'direct',
          self_display_name: '我',
          other_display_name: '小李',
          source_format: 'qq_text',
          status: 'imported',
        },
        latestJob: {
          id: 11,
          status: 'running',
          current_stage: 'embedding',
          progress_percent: 42,
          current_stage_percent: 84,
          current_stage_total_units: 100,
          current_stage_completed_units: 84,
          overall_total_units: 100,
          overall_completed_units: 42,
          status_message: null,
        },
      }),
    ).toMatchObject({
      id: 7,
      title: '和小李的聊天',
      statusLabel: '分析中 42%',
    })
  })
})
