import type { ConversationRead, SettingRead } from '../types/api'
import type { BootState } from './desktop'

type DecideAppShellStateInput = {
  bootPhase: BootState['phase']
  settings: SettingRead[]
  conversations: ConversationRead[]
}

export type AppShellState = {
  ready: boolean
  showWelcome: boolean
  hasModelSettings: boolean
  hasConversations: boolean
}

export type ShellHydrationStatus = 'loading' | 'ready' | 'error'

const REQUIRED_MODEL_SETTINGS = ['llm.base_url', 'llm.api_key', 'llm.chat_model'] as const

export function hasModelSettings(settings: SettingRead[]): boolean {
  const populatedKeys = new Set(
    settings
      .filter((setting) => setting.setting_value.trim().length > 0)
      .map((setting) => setting.setting_key),
  )

  return REQUIRED_MODEL_SETTINGS.every((key) => populatedKeys.has(key))
}

export function decideAppShellState(input: DecideAppShellStateInput): AppShellState {
  const ready = input.bootPhase === 'ready'
  const modelSettingsReady = hasModelSettings(input.settings)
  const hasConversations = input.conversations.length > 0

  return {
    ready,
    showWelcome: ready && (!modelSettingsReady || !hasConversations),
    hasModelSettings: modelSettingsReady,
    hasConversations,
  }
}

export function resolveShellHydrationStatus(input: {
  settings: SettingRead[] | null
  conversations: ConversationRead[] | null
  hasLoadError?: boolean
}): ShellHydrationStatus {
  if (input.hasLoadError) {
    return 'error'
  }

  if (input.settings === null || input.conversations === null) {
    return 'loading'
  }

  return 'ready'
}
