import type { ConversationRead, JobRead, MessageRead, SimulationRead } from '../types/api'
import { FRONTUI_PLACEHOLDER_AVATAR, FRONTUI_SELF_AVATAR } from '../frontui/mockState'
import type { FrontChatListItem, FrontChatMessage, FrontChatWindowState } from '../frontui/types'
import { resolveJobProgress, resolveJobStageProgressLabel } from './analysisProgress'

function trimText(value: string | null | undefined): string {
  return value?.trim() ?? ''
}

function resolveConversationDisplayName(conversation: ConversationRead): string {
  const title = trimText(conversation.title)
  if (title) {
    return title
  }

  const otherName = trimText(conversation.other_display_name)
  if (otherName) {
    return otherName
  }

  const selfName = trimText(conversation.self_display_name)
  if (selfName) {
    return selfName
  }

  return `会话 ${conversation.id}`
}

function resolveConversationPreviewText(conversation: ConversationRead): string {
  const participants = [trimText(conversation.self_display_name), trimText(conversation.other_display_name)].filter(Boolean)
  const sourceLabel = trimText(conversation.source_format).replaceAll('_', ' ')

  if (participants.length > 0 && sourceLabel) {
    return `${participants.join(' / ')} · ${sourceLabel}`
  }

  if (participants.length > 0) {
    return participants.join(' / ')
  }

  return sourceLabel ? `来源：${sourceLabel}` : '等待会话元数据'
}

function resolveJobTimestampLabel(job: JobRead | null | undefined): string {
  return resolveJobStageProgressLabel(job)
}

function resolveTimestampLabel(timestamp: string): string {
  const trimmed = trimText(timestamp)
  if (!trimmed) {
    return ''
  }

  const timeMatch = trimmed.match(/(?:T|\s)(\d{2}:\d{2})(?::\d{2}(?:\.\d+)?)?/)
  if (timeMatch?.[1]) {
    return timeMatch[1]
  }

  const hhmmMatch = trimmed.match(/\b\d{2}:\d{2}\b/)
  if (hhmmMatch) {
    return hhmmMatch[0]
  }

  return trimmed
}

function resolveMessageAvatar(message: MessageRead): string {
  return message.speaker_role === 'self' ? FRONTUI_SELF_AVATAR : FRONTUI_PLACEHOLDER_AVATAR
}

export function buildFrontChatItem(input: {
  conversation: ConversationRead
  otherAvatarUrl?: string
  latestJob?: JobRead | null
  isActive: boolean
}): FrontChatListItem {
  const { conversation, otherAvatarUrl, latestJob, isActive } = input

  return {
    id: `conversation-${conversation.id}`,
    conversationId: conversation.id,
    displayName: resolveConversationDisplayName(conversation),
    avatarUrl: otherAvatarUrl || FRONTUI_PLACEHOLDER_AVATAR,
    previewText: resolveConversationPreviewText(conversation),
    timestampLabel: resolveJobTimestampLabel(latestJob),
    progress: resolveJobProgress(latestJob),
    unreadCount: 0,
    active: isActive,
    source: 'real',
  }
}

export function buildFrontChatMessage(input: {
  message: MessageRead
  selfAvatarUrl?: string
  otherAvatarUrl?: string
}): FrontChatMessage {
  const { message, selfAvatarUrl, otherAvatarUrl } = input
  const isSelf = message.speaker_role === 'self'

  return {
    id: `message-${message.id}`,
    messageId: message.id,
    align: isSelf ? 'right' : 'left',
    bubbleTone: 'default',
    speakerName: trimText(message.speaker_name) || (isSelf ? '我' : '对方'),
    avatarUrl: isSelf ? selfAvatarUrl || FRONTUI_SELF_AVATAR : otherAvatarUrl || FRONTUI_PLACEHOLDER_AVATAR,
    text: message.content_text,
    timestampLabel: resolveTimestampLabel(message.timestamp),
    timestampRaw: message.timestamp,
    canRewrite: isSelf && message.message_type === 'text',
    source: 'real',
  }
}

export function buildFrontChatWindowState(input: {
  selectedConversation: ConversationRead | null
  selfAvatarUrl?: string
  otherAvatarUrl?: string
  messages: MessageRead[]
}): FrontChatWindowState {
  const { selectedConversation, selfAvatarUrl, otherAvatarUrl, messages } = input

  if (!selectedConversation) {
    return { mode: 'placeholder' }
  }

  return {
    mode: 'conversation',
    title: resolveConversationDisplayName(selectedConversation),
    messages: messages.map((message) => buildFrontChatMessage({ message, selfAvatarUrl, otherAvatarUrl })),
  }
}

export function buildFrontChatMessagesFromSimulation(input: {
  simulation: SimulationRead
  selfDisplayName?: string
  otherDisplayName?: string
  selfAvatarUrl?: string
  otherAvatarUrl?: string
  timestampRaw: string
}): FrontChatMessage[] {
  const {
    simulation,
    selfDisplayName = '我',
    otherDisplayName = '对方',
    selfAvatarUrl,
    otherAvatarUrl,
    timestampRaw,
  } = input
  const normalizedTimestamp = trimText(timestampRaw) || new Date().toISOString()

  if (simulation.simulated_turns.length > 0) {
    return simulation.simulated_turns.map((turn, index) => {
      const isSelf = turn.speaker_role === 'self'
      return {
        id: `simulation-${simulation.id}-turn-${turn.turn_index}-${index}`,
        messageId: null,
        align: isSelf ? 'right' : 'left',
        bubbleTone: isSelf ? 'simulation-self' : 'simulation-other',
        speakerName: isSelf ? selfDisplayName : otherDisplayName,
        avatarUrl: isSelf ? selfAvatarUrl || FRONTUI_SELF_AVATAR : otherAvatarUrl || FRONTUI_PLACEHOLDER_AVATAR,
        text: turn.message_text,
        timestampLabel: resolveTimestampLabel(normalizedTimestamp),
        timestampRaw: normalizedTimestamp,
        canRewrite: false,
        source: 'mock',
      }
    })
  }

  if (trimText(simulation.first_reply_text)) {
    return [
      {
        id: `simulation-${simulation.id}-first-reply`,
        messageId: null,
        align: 'left',
        bubbleTone: 'simulation-other',
        speakerName: otherDisplayName,
        avatarUrl: otherAvatarUrl || FRONTUI_PLACEHOLDER_AVATAR,
        text: simulation.first_reply_text ?? '',
        timestampLabel: resolveTimestampLabel(normalizedTimestamp),
        timestampRaw: normalizedTimestamp,
        canRewrite: false,
        source: 'mock',
      },
    ]
  }

  return []
}
