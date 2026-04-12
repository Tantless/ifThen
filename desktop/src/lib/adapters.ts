import type { ConversationRead, JobRead, MessageRead, SettingRead } from '../types/api'
import { DEFAULT_SELF_AVATAR_URL } from './avatarPresets'

export type SettingsFormState = {
  baseUrl: string
  apiKey: string
  chatModel: string
  simulationBaseUrl: string
  simulationApiKey: string
  simulationModel: string
  simulationMode: 'single_reply' | 'short_thread'
  simulationTurnCount: number
  selfAvatarUrl: string
}

export type ConversationListItem = {
  id: number
  title: string
  statusLabel: string
  secondaryText: string
}

export type MessageBubbleModel = {
  id: number
  sequenceNo: number
  align: 'left' | 'right'
  speakerName: string
  timestamp: string
  text: string
  canRewrite: boolean
}

function trimSettingValue(value: string | undefined): string {
  return value?.trim() ?? ''
}

function resolveJobStatusLabel(job: JobRead | null | undefined): string {
  if (!job) {
    return '待分析'
  }

  if (job.status === 'running' || job.status === 'queued') {
    const progress = Number.isFinite(job.progress_percent) ? Math.max(0, Math.round(job.progress_percent)) : 0
    return `分析中 ${progress}%`
  }

  if (job.status === 'completed') {
    return '分析完成'
  }

  if (job.status === 'failed') {
    return '分析失败'
  }

  return job.status
}

export function buildSettingsFormState(entries: SettingRead[]): SettingsFormState {
  const byKey = new Map(entries.map((entry) => [entry.setting_key, trimSettingValue(entry.setting_value)]))

  return {
    baseUrl: byKey.get('llm.base_url') ?? '',
    apiKey: byKey.get('llm.api_key') ?? '',
    chatModel: byKey.get('llm.chat_model') ?? '',
    simulationBaseUrl: byKey.get('llm.simulation_base_url') ?? '',
    simulationApiKey: byKey.get('llm.simulation_api_key') ?? '',
    simulationModel: byKey.get('llm.simulation_model') ?? '',
    simulationMode: byKey.get('simulation.default_mode') === 'short_thread' ? 'short_thread' : 'single_reply',
    simulationTurnCount: Math.min(6, Math.max(1, Number.parseInt(byKey.get('simulation.default_turn_count') ?? '1', 10) || 1)),
    selfAvatarUrl: byKey.get('profile.self_avatar_url') ?? DEFAULT_SELF_AVATAR_URL,
  }
}

export function buildConversationListItem(input: {
  conversation: ConversationRead
  latestJob?: JobRead | null
}): ConversationListItem {
  const { conversation, latestJob } = input
  const participants = [conversation.self_display_name, conversation.other_display_name].filter((value) => value.trim().length > 0)
  const sourceLabel = conversation.source_format.replaceAll('_', ' ')

  return {
    id: conversation.id,
    title: conversation.title,
    statusLabel: resolveJobStatusLabel(latestJob),
    secondaryText:
      participants.length > 0 ? `${participants.join(' / ')} · ${sourceLabel}` : `来源：${sourceLabel}`,
  }
}

export function buildMessageBubbleModel(message: MessageRead): MessageBubbleModel {
  const isSelf = message.speaker_role === 'self'

  return {
    id: message.id,
    sequenceNo: message.sequence_no,
    align: isSelf ? 'right' : 'left',
    speakerName: message.speaker_name,
    timestamp: message.timestamp,
    text: message.content_text,
    canRewrite: isSelf && message.message_type === 'text',
  }
}
