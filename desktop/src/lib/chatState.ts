import type { SimulationRead } from '../types/api'

export type HistoryChatViewState = {
  mode: 'history'
  messageWindowMode: 'latest' | 'anchored'
  anchorMessageId: number | null
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

export type RewriteRequestSnapshot = {
  requestId: number
  conversationId: number
  targetMessageId: number
  targetMessageTimestamp: string
}

type RewriteDraftPointer = {
  targetMessageId: number
  targetMessageTimestamp: string
} | null

export type LatestJobLoadState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'loaded' }
  | { status: 'retry_wait'; retryAt: number }

export type MessageLoadState =
  | { status: 'idle' }
  | { status: 'loading'; startedAt: number }
  | { status: 'retry_wait'; startedAt: number; retryAt: number }
  | { status: 'loaded' }
  | { status: 'failed' }

export function createLatestHistoryView(): HistoryChatViewState {
  return {
    mode: 'history',
    messageWindowMode: 'latest',
    anchorMessageId: null,
  }
}

export function createAnchoredHistoryView(anchorMessageId: number): HistoryChatViewState {
  return {
    mode: 'history',
    messageWindowMode: 'anchored',
    anchorMessageId,
  }
}

export function enterBranchView(_state: HistoryChatViewState, input: EnterBranchViewInput): BranchChatViewState {
  return {
    mode: 'branch',
    ...input,
  }
}

export function exitBranchView(_state: BranchChatViewState): HistoryChatViewState {
  return createLatestHistoryView()
}

export function resolveInspectorSnapshotAt(state: ChatViewState, _messages: TimestampMessage[]): string | null {
  if (state.mode === 'branch') {
    return state.targetMessageTimestamp
  }

  return null
}

export function isRewriteRequestCurrent(input: {
  activeRequest: RewriteRequestSnapshot | null
  requestId: number
  conversationId: number | null
  draft: RewriteDraftPointer
}): boolean {
  return (
    input.activeRequest !== null &&
    input.activeRequest.requestId === input.requestId &&
    input.activeRequest.conversationId === input.conversationId &&
    input.activeRequest.targetMessageId === input.draft?.targetMessageId &&
    input.activeRequest.targetMessageTimestamp === input.draft?.targetMessageTimestamp
  )
}

export function shouldStartLatestJobLoad(state: LatestJobLoadState | undefined, now: number): boolean {
  if (!state || state.status === 'idle') {
    return true
  }

  if (state.status === 'retry_wait') {
    return state.retryAt <= now
  }

  return false
}
