import type { ConversationRead, JobRead, MessageRead, SimulationRead } from '../types/api'
import { FRONTUI_PLACEHOLDER_AVATAR, FRONTUI_SELF_AVATAR } from '../frontui/mockState'
import type { FrontChatListItem, FrontChatMessage, FrontChatWindowState } from '../frontui/types'
import { resolveJobProgress, resolveJobStageProgressLabel } from './analysisProgress'

function trimText(value: string | null | undefined): string {
  return value?.trim() ?? ''
}

function splitSimulationMessageText(value: string | null | undefined): string[] {
  const normalized = trimText(value)
  if (!normalized) {
    return []
  }

  const parts = normalized
    .split(/[\r\n]+|[，,。！？!?；;、…]+/u)
    .map((item) => item.trim())
    .filter(Boolean)

  return parts.length > 0 ? parts : [normalized]
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

function startOfDay(value: Date): number {
  return new Date(value.getFullYear(), value.getMonth(), value.getDate()).getTime()
}

export function formatChatTimestampLabel(timestamp: string, nowInput?: string | Date): string {
  const trimmed = trimText(timestamp)
  if (!trimmed) {
    return ''
  }

  const target = new Date(trimmed)
  if (Number.isNaN(target.getTime())) {
    return trimmed
  }

  const now = nowInput ? new Date(nowInput) : new Date()
  const resolvedNow = Number.isNaN(now.getTime()) ? new Date() : now
  const dayDiff = Math.round((startOfDay(resolvedNow) - startOfDay(target)) / 86_400_000)
  const hhmm = `${String(target.getHours()).padStart(2, '0')}:${String(target.getMinutes()).padStart(2, '0')}`

  if (dayDiff === 0) {
    return hhmm
  }

  if (dayDiff === 1) {
    return `昨天 ${hhmm}`
  }

  if (dayDiff === 2) {
    return `前天 ${hhmm}`
  }

  if (target.getFullYear() === resolvedNow.getFullYear()) {
    return `${target.getMonth() + 1}月${target.getDate()}日 ${hhmm}`
  }

  return `${target.getFullYear()}年${target.getMonth() + 1}月${target.getDate()}日 ${hhmm}`
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
  now?: string | Date
}): FrontChatMessage {
  const { message, selfAvatarUrl, otherAvatarUrl, now } = input
  const isSelf = message.speaker_role === 'self'

  return {
    id: `message-${message.id}`,
    messageId: message.id,
    align: isSelf ? 'right' : 'left',
    bubbleTone: 'default',
    speakerName: trimText(message.speaker_name) || (isSelf ? '我' : '对方'),
    avatarUrl: isSelf ? selfAvatarUrl || FRONTUI_SELF_AVATAR : otherAvatarUrl || FRONTUI_PLACEHOLDER_AVATAR,
    text: message.content_text,
    timestampLabel: formatChatTimestampLabel(message.timestamp, now),
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
  now?: string | Date
}): FrontChatWindowState {
  const { selectedConversation, selfAvatarUrl, otherAvatarUrl, messages, now } = input

  if (!selectedConversation) {
    return { mode: 'placeholder' }
  }

  return {
    mode: 'conversation',
    title: resolveConversationDisplayName(selectedConversation),
    messages: messages.map((message) => buildFrontChatMessage({ message, selfAvatarUrl, otherAvatarUrl, now })),
  }
}

export function buildFrontChatMessagesFromSimulation(input: {
  simulation: SimulationRead
  selfDisplayName?: string
  otherDisplayName?: string
  selfAvatarUrl?: string
  otherAvatarUrl?: string
  timestampRaw: string
  now?: string | Date
}): FrontChatMessage[] {
  const {
    simulation,
    selfDisplayName = '我',
    otherDisplayName = '对方',
    selfAvatarUrl,
    otherAvatarUrl,
    timestampRaw,
    now,
  } = input
  const normalizedTimestamp = trimText(timestampRaw) || new Date().toISOString()

  if (simulation.simulated_turns.length > 0) {
    return simulation.simulated_turns.flatMap((turn, index) => {
      const isSelf = turn.speaker_role === 'self'
      return splitSimulationMessageText(turn.message_text).map((text, partIndex) => ({
        id: `simulation-${simulation.id}-turn-${turn.turn_index}-${index}-part-${partIndex}`,
        messageId: null,
        align: isSelf ? 'right' : 'left',
        bubbleTone: isSelf ? 'simulation-self' : 'simulation-other',
        speakerName: isSelf ? selfDisplayName : otherDisplayName,
        avatarUrl: isSelf ? selfAvatarUrl || FRONTUI_SELF_AVATAR : otherAvatarUrl || FRONTUI_PLACEHOLDER_AVATAR,
        text,
        timestampLabel: formatChatTimestampLabel(normalizedTimestamp, now),
        timestampRaw: normalizedTimestamp,
        canRewrite: false,
        source: 'mock',
      }))
    })
  }

  if (trimText(simulation.first_reply_text)) {
    return splitSimulationMessageText(simulation.first_reply_text).map((text, partIndex) => ({
      id: `simulation-${simulation.id}-first-reply-part-${partIndex}`,
      messageId: null,
      align: 'left',
      bubbleTone: 'simulation-other',
      speakerName: otherDisplayName,
      avatarUrl: otherAvatarUrl || FRONTUI_PLACEHOLDER_AVATAR,
      text,
      timestampLabel: formatChatTimestampLabel(normalizedTimestamp, now),
      timestampRaw: normalizedTimestamp,
      canRewrite: false,
      source: 'mock',
    }))
  }

  return []
}
