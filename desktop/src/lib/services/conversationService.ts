import { apiClient } from '../apiClient'
import type {
  ConversationRead,
  ImportResponse,
  JobRead,
  MessageRead,
  PersonaProfileRead,
  SnapshotRead,
  TopicRead,
} from '../../types/api'

type ListMessagesOptions = {
  limit?: number
  before?: number
  after?: number
  keyword?: string
  date?: string
  order?: 'asc' | 'desc'
}

type ImportConversationInput = {
  file: Blob
  fileName?: string
  selfDisplayName: string
  autoAnalyze?: boolean
}

function withQuery(path: string, entries: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams()

  for (const [key, value] of Object.entries(entries)) {
    if (value !== undefined) {
      params.set(key, String(value))
    }
  }

  const query = params.toString()
  return query ? `${path}?${query}` : path
}

export function listConversations(): Promise<ConversationRead[]> {
  return apiClient.get<ConversationRead[]>('/conversations')
}

export function deleteConversation(conversationId: number): Promise<void> {
  return apiClient.delete(`/conversations/${conversationId}`)
}

export function listMessages(conversationId: number, options: ListMessagesOptions = {}): Promise<MessageRead[]> {
  return apiClient.get<MessageRead[]>(
    withQuery(`/conversations/${conversationId}/messages`, {
      limit: options.limit,
      before: options.before,
      after: options.after,
      keyword: options.keyword,
      date: options.date,
      order: options.order,
    }),
  )
}

export function listTopics(conversationId: number): Promise<TopicRead[]> {
  return apiClient.get<TopicRead[]>(`/conversations/${conversationId}/topics`)
}

export function readProfile(conversationId: number): Promise<PersonaProfileRead[]> {
  return apiClient.get<PersonaProfileRead[]>(`/conversations/${conversationId}/profile`)
}

export function readSnapshot(conversationId: number, at?: string): Promise<SnapshotRead> {
  return apiClient.get<SnapshotRead>(withQuery(`/conversations/${conversationId}/timeline-state`, { at }))
}

export function importConversation(input: ImportConversationInput): Promise<ImportResponse> {
  const formData = new FormData()
  const fileName =
    input.fileName ?? (typeof File !== 'undefined' && input.file instanceof File ? input.file.name : 'qq_export.txt')

  formData.append('file', input.file, fileName)
  formData.append('self_display_name', input.selfDisplayName)

  if (input.autoAnalyze !== undefined) {
    formData.append('auto_analyze', String(input.autoAnalyze))
  }

  return apiClient.post<ImportResponse>('/imports/qq-text', formData)
}

export function startAnalysis(conversationId: number): Promise<JobRead> {
  return apiClient.post<JobRead>(`/conversations/${conversationId}/start-analysis`, {})
}
