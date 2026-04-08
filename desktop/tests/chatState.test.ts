import React from 'react'
import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'

import { AnalysisInspector } from '../src/components/AnalysisInspector'
import { BranchView } from '../src/components/BranchView'
import { MessageBubble } from '../src/components/MessageBubble'
import { RewritePanel } from '../src/components/RewritePanel'
import {
  enterBranchView,
  exitBranchView,
  isRewriteRequestCurrent,
  resolveInspectorSnapshotAt,
  shouldStartLatestJobLoad,
  type ChatViewState,
} from '../src/lib/chatState'
import type { PersonaProfileRead, SimulationRead, SnapshotRead, TopicRead } from '../src/types/api'

const simulation: SimulationRead = {
  id: 8,
  mode: 'short_thread',
  replacement_content: '换一种更柔和的说法',
  first_reply_text: '那我们再试一次吧。',
  impact_summary: '对方情绪明显缓和。',
  simulated_turns: [
    {
      turn_index: 1,
      speaker_role: 'other',
      message_text: '那我们再试一次吧。',
      strategy_used: 'de-escalate',
      state_after_turn: {},
      generation_notes: null,
    },
    {
      turn_index: 2,
      speaker_role: 'self',
      message_text: '谢谢你愿意继续聊。',
      strategy_used: 'repair',
      state_after_turn: {},
      generation_notes: null,
    },
  ],
}

describe('chatState', () => {
  it('switches from history to branch', () => {
    expect(
      enterBranchView(
        { mode: 'history' },
        {
          targetMessageId: 12,
          replacementContent: '换个说法',
          simulation,
          targetMessageTimestamp: '2026-04-07T12:00:00Z',
        },
      ),
    ).toMatchObject({
      mode: 'branch',
      targetMessageId: 12,
      replacementContent: '换个说法',
      simulation,
      targetMessageTimestamp: '2026-04-07T12:00:00Z',
    })
  })

  it('returns from branch to history', () => {
    expect(
      exitBranchView({
        mode: 'branch',
        targetMessageId: 12,
        replacementContent: '换个说法',
        simulation,
        targetMessageTimestamp: '2026-04-07T12:00:00Z',
      }),
    ).toEqual({ mode: 'history' })
  })

  it('prefers the branch target timestamp for inspector snapshots', () => {
    const state: ChatViewState = {
      mode: 'branch',
      targetMessageId: 12,
      replacementContent: '换个说法',
      simulation,
      targetMessageTimestamp: '2026-04-07T12:00:00Z',
    }

    expect(
      resolveInspectorSnapshotAt(state, [
        { id: 11, timestamp: '2026-04-07T11:00:00Z' },
        { id: 12, timestamp: '2026-04-07T12:30:00Z' },
      ]),
    ).toBe('2026-04-07T12:00:00Z')
  })

  it('falls back to the latest visible message timestamp in history mode', () => {
    expect(
      resolveInspectorSnapshotAt(
        { mode: 'history' },
        [
          { id: 1, timestamp: '2026-04-07T08:00:00Z' },
          { id: 2, timestamp: '2026-04-07T09:00:00Z' },
        ],
      ),
    ).toBe('2026-04-07T09:00:00Z')
  })

  it('invalidates stale rewrite requests when the active draft changes', () => {
    expect(
      isRewriteRequestCurrent({
        activeRequest: {
          requestId: 3,
          conversationId: 21,
          targetMessageId: 9,
          targetMessageTimestamp: '2026-04-07T12:00:00Z',
        },
        requestId: 3,
        conversationId: 21,
        draft: {
          targetMessageId: 9,
          targetMessageTimestamp: '2026-04-07T12:01:00Z',
        },
      }),
    ).toBe(false)
  })

  it('retries latest-job loading after the retry window elapses', () => {
    expect(shouldStartLatestJobLoad({ status: 'retry_wait', retryAt: 2000 }, 1500)).toBe(false)
    expect(shouldStartLatestJobLoad({ status: 'retry_wait', retryAt: 2000 }, 2000)).toBe(true)
    expect(shouldStartLatestJobLoad({ status: 'loaded' }, 3000)).toBe(false)
  })
})

describe('Task 5 desktop components', () => {
  it('renders the rewrite panel controls', () => {
    const html = renderToStaticMarkup(
      React.createElement(RewritePanel, {
        originalMessage: '今天先到这里吧',
        targetMessageTimestamp: '2026-04-07T12:00:00Z',
        replacementContent: '我想先整理一下，晚点继续聊可以吗？',
        mode: 'short_thread',
        turnCount: 3,
        pending: false,
        onReplacementContentChange: () => undefined,
        onModeChange: () => undefined,
        onTurnCountChange: () => undefined,
        onSubmit: () => undefined,
        onCancel: () => undefined,
      }),
    )

    expect(html).toContain('改写并推演')
    expect(html).toContain('今天先到这里吧')
    expect(html).toContain('发送时间')
    expect(html).toContain('2026')
    expect(html).toContain('晚点继续聊可以吗')
    expect(html).toContain('短链推演')
  })

  it('renders the branch view summary and simulated turns', () => {
    const html = renderToStaticMarkup(
      React.createElement(BranchView, {
        originalMessage: '今天先到这里吧',
        branchState: {
          mode: 'branch',
          targetMessageId: 12,
          replacementContent: '我想先整理一下，晚点继续聊可以吗？',
          simulation,
          targetMessageTimestamp: '2026-04-07T12:00:00Z',
        },
        onBack: () => undefined,
      }),
    )

    expect(html).toContain('返回原始历史')
    expect(html).toContain('改写内容')
    expect(html).toContain('那我们再试一次吧')
    expect(html).toContain('谢谢你愿意继续聊')
  })

  it('renders analysis inspector topics, persona, and snapshot', () => {
    const topics: TopicRead[] = [
      { id: 1, topic_name: '工作安排', topic_summary: '反复确认时间和优先级', topic_status: 'active' },
    ]
    const profile: PersonaProfileRead[] = [
      {
        subject_role: 'self',
        global_persona_summary: '沟通直接但会主动修复关系。',
        style_traits: ['直接'],
        conflict_traits: ['回避升级'],
        relationship_specific_patterns: ['冲突后会解释'],
        confidence: 0.82,
      },
    ]
    const snapshot: SnapshotRead = {
      id: 3,
      as_of_message_id: 12,
      as_of_time: '2026-04-07T12:00:00Z',
      relationship_temperature: 'warm',
      tension_level: 'medium',
      openness_level: 'high',
      initiative_balance: 'balanced',
      defensiveness_level: 'low',
      unresolved_conflict_flags: ['deadline'],
      relationship_phase: 'repair',
      snapshot_summary: '双方处于修复沟通阶段。',
    }

    const html = renderToStaticMarkup(
      React.createElement(AnalysisInspector, {
        open: true,
        currentTab: 'profile',
        loadingByTab: {
          topics: false,
          profile: false,
          snapshot: false,
        },
        errorMessage: null,
        topics,
        profile,
        snapshot,
        onTabChange: () => undefined,
        onClose: () => undefined,
      }),
    )

    expect(html).toContain('分析侧栏')
    expect(html).toContain('Topics')
    expect(html).toContain('Persona')
    expect(html).toContain('Snapshot')
    expect(html).toContain('沟通直接但会主动修复关系')
    expect(html).not.toContain('工作安排')
    expect(html).not.toContain('双方处于修复沟通阶段')
  })

  it('renders rewrite action with hover-reveal hook only when enabled', () => {
    const enabledHtml = renderToStaticMarkup(
      React.createElement(MessageBubble, {
        message: {
          id: 1,
          sequenceNo: 1,
          align: 'right',
          speakerName: '我',
          timestamp: '2026-04-07T12:00:00Z',
          text: '先这样',
          canRewrite: true,
        },
        onRewrite: () => undefined,
      }),
    )

    const disabledHtml = renderToStaticMarkup(
      React.createElement(MessageBubble, {
        message: {
          id: 2,
          sequenceNo: 2,
          align: 'right',
          speakerName: '我',
          timestamp: '2026-04-07T12:00:00Z',
          text: '先这样',
          canRewrite: true,
        },
      }),
    )

    expect(enabledHtml).toContain('message-bubble__avatar-slot')
    expect(enabledHtml).toContain('message-bubble__stack')
    expect(enabledHtml).toContain('message-bubble__actions--hover')
    expect(enabledHtml).toContain('改写并推演')
    expect(disabledHtml).not.toContain('改写并推演')
  })
})
