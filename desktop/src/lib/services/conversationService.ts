import type {
  ConversationRead,
  JobRead,
  ImportConversationRequest,
  ImportResponse,
  ListMessagesInput,
  MessageContextRead,
  MessageDayRead,
  MessageRead,
  PersonaProfileRead,
  ReadMessageContextInput,
  ReadSnapshotInput,
  SnapshotRead,
  TopicRead,
} from '../../types/api'
import { requireDesktopBridge } from '../desktop'

type ListMessagesOptions = Omit<ListMessagesInput, 'conversationId'>

type ImportConversationInput = ImportConversationRequest

export function listConversations(): Promise<ConversationRead[]> {
  return requireDesktopBridge().conversations.list()
}

export function deleteConversation(conversationId: number): Promise<void> {
  return requireDesktopBridge().conversations.delete(conversationId)
}

export function listMessages(conversationId: number, options: ListMessagesOptions = {}): Promise<MessageRead[]> {
  return requireDesktopBridge().conversations.listMessages({
    conversationId,
    ...options,
  })
}

export function listMessageDays(conversationId: number): Promise<MessageDayRead[]> {
  return requireDesktopBridge().conversations.listMessageDays(conversationId)
}

export function readMessageContext(messageId: number, radius?: number): Promise<MessageContextRead> {
  const payload: ReadMessageContextInput = { messageId, radius }
  return requireDesktopBridge().conversations.readMessageContext(payload)
}

export function listTopics(conversationId: number): Promise<TopicRead[]> {
  return requireDesktopBridge().conversations.listTopics(conversationId)
}

export function readProfile(conversationId: number): Promise<PersonaProfileRead[]> {
  return requireDesktopBridge().conversations.readProfile(conversationId)
}

export function readSnapshot(conversationId: number, at?: string): Promise<SnapshotRead> {
  const payload: ReadSnapshotInput = { conversationId, at }
  return requireDesktopBridge().conversations.readSnapshot(payload)
}

export function importConversation(input: ImportConversationInput): Promise<ImportResponse> {
  return requireDesktopBridge().conversations.import(input)
}

export function startAnalysis(conversationId: number): Promise<JobRead> {
  return requireDesktopBridge().conversations.startAnalysis(conversationId)
}
