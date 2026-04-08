import type { SimulationRead } from '../types/api'

export type HistoryChatViewState = {
  mode: 'history'
}

export type BranchChatViewState = {
  mode: 'branch'
  targetMessageId: number
  replacementContent: string
  simulation: SimulationRead
  targetMessageTimestamp: string
}

export type ChatViewState = HistoryChatViewState | BranchChatViewState

type EnterBranchViewInput = Omit<BranchChatViewState, 'mode'>

type TimestampMessage = {
  id: number
  timestamp: string
}

export function enterBranchView(_state: HistoryChatViewState, input: EnterBranchViewInput): BranchChatViewState {
  return {
    mode: 'branch',
    ...input,
  }
}

export function exitBranchView(_state: BranchChatViewState): HistoryChatViewState {
  return { mode: 'history' }
}

export function resolveInspectorSnapshotAt(state: ChatViewState, messages: TimestampMessage[]): string | null {
  if (state.mode === 'branch') {
    return state.targetMessageTimestamp
  }

  return messages.at(-1)?.timestamp ?? null
}
