import { describe, expect, it } from 'vitest'

import { FRONTUI_PLACEHOLDER_AVATAR, FRONTUI_SELF_AVATAR } from '../src/frontui/mockState'
import {
  buildFrontChatItem,
  buildFrontChatMessage,
  buildFrontChatMessagesFromSimulation,
  buildFrontChatWindowState,
} from '../src/lib/frontUiAdapters'

describe('buildFrontChatItem', () => {
  it('maps real conversations into frontUI list rows', () => {
    expect(
      buildFrontChatItem({
        conversation: {
          id: 7,
          title: '和小李的聊天',
          chat_type: 'private',
          self_display_name: '我',
          other_display_name: '小李',
          source_format: 'qq_export_v5',
          status: 'imported',
        },
        otherAvatarUrl: 'data:image/svg+xml;base64,other-avatar',
        latestJob: {
          id: 12,
          status: 'running',
          current_stage: 'summarizing',
          progress_percent: 42,
          current_stage_percent: 84,
          current_stage_total_units: 100,
          current_stage_completed_units: 84,
          overall_total_units: 100,
          overall_completed_units: 42,
          status_message: null,
        },
        isActive: true,
      }),
    ).toEqual({
      id: 'conversation-7',
      conversationId: 7,
      displayName: '和小李的聊天',
      avatarUrl: 'data:image/svg+xml;base64,other-avatar',
      previewText: '我 / 小李 · qq export v5',
      timestampLabel: '摘要生成 84%',
      progress: {
        label: '摘要生成 84%',
        percent: 84,
        tone: 'running',
      },
      unreadCount: 0,
      active: true,
      source: 'real',
    })
  })

  it('falls back to participant names when a conversation title is blank', () => {
    expect(
      buildFrontChatItem({
        conversation: {
          id: 8,
          title: '   ',
          chat_type: 'private',
          self_display_name: '我',
          other_display_name: '阿青',
          source_format: 'wechat_backup',
          status: 'imported',
        },
        latestJob: null,
        isActive: false,
      }),
    ).toMatchObject({
      displayName: '阿青',
      previewText: '我 / 阿青 · wechat backup',
      timestampLabel: '',
      progress: null,
      active: false,
    })
  })

  it('maps topic/persona/snapshot subtasks into user-facing stage labels', () => {
    expect(
      buildFrontChatItem({
        conversation: {
          id: 9,
          title: '和阿青的聊天',
          chat_type: 'private',
          self_display_name: '我',
          other_display_name: '阿青',
          source_format: 'qq_export_v5',
          status: 'analyzing',
        },
        latestJob: {
          id: 13,
          status: 'running',
          current_stage: 'topic_persona_snapshot',
          progress_percent: 97,
          current_stage_percent: 50,
          current_stage_total_units: 20,
          current_stage_completed_units: 10,
          overall_total_units: 100,
          overall_completed_units: 97,
          status_message: 'topic_persona_snapshot 10/20 tasks (snapshots 7/14)',
        },
        isActive: false,
      }),
    ).toMatchObject({
      timestampLabel: '关系快照 50%',
      progress: {
        label: '关系快照 50%',
        percent: 50,
        tone: 'running',
      },
    })
  })

  it('maps failed jobs into a red progress indicator for the list', () => {
    expect(
      buildFrontChatItem({
        conversation: {
          id: 10,
          title: '失败会话',
          chat_type: 'private',
          self_display_name: '我',
          other_display_name: '阿青',
          source_format: 'qq_export_v5',
          status: 'failed',
        },
        latestJob: {
          id: 14,
          status: 'failed',
          current_stage: 'summarizing',
          progress_percent: 95,
          current_stage_percent: 28,
          current_stage_total_units: 14,
          current_stage_completed_units: 4,
          overall_total_units: 1059,
          overall_completed_units: 1018,
          status_message: 'failed summarizing 4/14 summaries',
        },
        isActive: false,
      }),
    ).toMatchObject({
      progress: {
        label: '失败',
        percent: 100,
        tone: 'failed',
      },
    })
  })
})

describe('buildFrontChatMessage', () => {
  it('maps self text messages into rewriteable right-aligned rows', () => {
    expect(
      buildFrontChatMessage({
        message: {
          id: 21,
          sequence_no: 3,
          speaker_name: '我',
          speaker_role: 'self',
          timestamp: '2026-04-07T10:00:00.000Z',
          content_text: '那我们先这样吧',
          message_type: 'text',
          resource_items: null,
        },
        selfAvatarUrl: 'data:image/svg+xml;base64,self-avatar',
      }),
    ).toEqual({
      id: 'message-21',
      messageId: 21,
      align: 'right',
      speakerName: '我',
      avatarUrl: 'data:image/svg+xml;base64,self-avatar',
      text: '那我们先这样吧',
      timestampLabel: '10:00',
      timestampRaw: '2026-04-07T10:00:00.000Z',
      canRewrite: true,
      source: 'real',
    })
  })
})

describe('buildFrontChatWindowState', () => {
  it('falls back to the frontUI placeholder state when no conversation is selected', () => {
    expect(buildFrontChatWindowState({ selectedConversation: null, messages: [] })).toEqual({ mode: 'placeholder' })
  })

  it('maps a selected conversation and message history into a frontUI window state', () => {
    expect(
      buildFrontChatWindowState({
        selectedConversation: {
          id: 9,
          title: '',
          chat_type: 'private',
          self_display_name: '我',
          other_display_name: '老王',
          source_format: 'qq_text',
          status: 'imported',
        },
        selfAvatarUrl: 'data:image/svg+xml;base64,self-avatar',
        otherAvatarUrl: 'data:image/svg+xml;base64,other-avatar',
        messages: [
          {
            id: 101,
            sequence_no: 1,
            speaker_name: '老王',
            speaker_role: 'other',
            timestamp: '2026-04-07T10:01:00.000Z',
            content_text: '收到，稍后回你',
            message_type: 'text',
            resource_items: null,
          },
        ],
      }),
    ).toEqual({
      mode: 'conversation',
      title: '老王',
      messages: [
        {
          id: 'message-101',
          messageId: 101,
          align: 'left',
          speakerName: '老王',
          avatarUrl: 'data:image/svg+xml;base64,other-avatar',
          text: '收到，稍后回你',
          timestampLabel: '10:01',
          timestampRaw: '2026-04-07T10:01:00.000Z',
          canRewrite: false,
          source: 'real',
        },
      ],
    })
  })
})

describe('buildFrontChatMessagesFromSimulation', () => {
  it('maps simulated turns into left/right chat rows without duplicating the first reply', () => {
    expect(
      buildFrontChatMessagesFromSimulation({
        simulation: {
          id: 88,
          mode: 'short_thread',
          replacement_content: '我想先冷静一下，晚点继续聊可以吗？',
          first_reply_text: '好，那你先休息。',
          impact_summary: '冲突被降温。',
          simulated_turns: [
            {
              turn_index: 1,
              speaker_role: 'other',
              message_text: '好，那你先休息。',
              strategy_used: 'de-escalate',
              state_after_turn: {},
              generation_notes: null,
            },
            {
              turn_index: 2,
              speaker_role: 'self',
              message_text: '谢谢理解，我们晚点再聊。',
              strategy_used: 'repair',
              state_after_turn: {},
              generation_notes: null,
            },
          ],
        },
        selfDisplayName: '我',
        otherDisplayName: '小李',
        selfAvatarUrl: 'data:image/svg+xml;base64,self-avatar',
        otherAvatarUrl: 'data:image/svg+xml;base64,other-avatar',
        timestampRaw: '2026-04-08T10:02:00',
      }),
    ).toEqual([
      {
        id: 'simulation-88-turn-1-0',
        messageId: null,
        align: 'left',
        speakerName: '小李',
        avatarUrl: 'data:image/svg+xml;base64,other-avatar',
        text: '好，那你先休息。',
        timestampLabel: '10:02',
        timestampRaw: '2026-04-08T10:02:00',
        canRewrite: false,
        source: 'mock',
      },
      {
        id: 'simulation-88-turn-2-1',
        messageId: null,
        align: 'right',
        speakerName: '我',
        avatarUrl: 'data:image/svg+xml;base64,self-avatar',
        text: '谢谢理解，我们晚点再聊。',
        timestampLabel: '10:02',
        timestampRaw: '2026-04-08T10:02:00',
        canRewrite: false,
        source: 'mock',
      },
    ])
  })
})
