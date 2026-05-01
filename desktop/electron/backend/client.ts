import { readFile } from 'node:fs/promises'
import path from 'node:path'

import type {
  ConversationRead,
  ImportConversationRequest,
  ImportResponse,
  JobRead,
  ListConversationJobsInput,
  ListConversationSimulationJobsInput,
  ListMessagesInput,
  MessageContextRead,
  MessageDayRead,
  MessageRead,
  PersonaProfileRead,
  ReadMessageContextInput,
  ReadSnapshotInput,
  SettingRead,
  SettingWrite,
  SimulationCreate,
  SimulationJobRead,
  SimulationRead,
  SnapshotRead,
  TopicRead,
} from '../../src/types/api.js'

const DESKTOP_API_AUTH_HEADER = 'x-if-then-desktop-token'

type DesktopBackendClientOptions = {
  apiOrigin: string
  apiAuthToken?: string
}

type ImportConversationFromFileInput = ImportConversationRequest & {
  filePath: string
}

function withQuery(pathname: string, query: Record<string, string | number | undefined>): string {
  const params = new URLSearchParams()

  for (const [key, value] of Object.entries(query)) {
    if (value !== undefined) {
      params.set(key, String(value))
    }
  }

  const search = params.toString()
  return search ? `${pathname}?${search}` : pathname
}

export class DesktopBackendClient {
  constructor(private readonly options: DesktopBackendClientOptions) {}

  async readSettings(): Promise<SettingRead[]> {
    return this.getJson<SettingRead[]>('/settings')
  }

  async writeSetting(payload: SettingWrite): Promise<SettingRead> {
    return this.sendJson<SettingRead>('/settings', 'PUT', payload)
  }

  async listConversations(): Promise<ConversationRead[]> {
    return this.getJson<ConversationRead[]>('/conversations')
  }

  async deleteConversation(conversationId: number): Promise<void> {
    await this.request(`/conversations/${conversationId}`, { method: 'DELETE' })
  }

  async listMessages(payload: ListMessagesInput): Promise<MessageRead[]> {
    return this.getJson<MessageRead[]>(
      withQuery(`/conversations/${payload.conversationId}/messages`, {
        limit: payload.limit,
        before: payload.before,
        after: payload.after,
        keyword: payload.keyword,
        date: payload.date,
        order: payload.order,
      }),
    )
  }

  async listMessageDays(conversationId: number): Promise<MessageDayRead[]> {
    return this.getJson<MessageDayRead[]>(`/conversations/${conversationId}/message-days`)
  }

  async readMessageContext(payload: ReadMessageContextInput): Promise<MessageContextRead> {
    return this.getJson<MessageContextRead>(
      withQuery(`/messages/${payload.messageId}/context`, {
        radius: payload.radius,
      }),
    )
  }

  async listTopics(conversationId: number): Promise<TopicRead[]> {
    return this.getJson<TopicRead[]>(`/conversations/${conversationId}/topics`)
  }

  async readProfile(conversationId: number): Promise<PersonaProfileRead[]> {
    return this.getJson<PersonaProfileRead[]>(`/conversations/${conversationId}/profile`)
  }

  async readSnapshot(payload: ReadSnapshotInput): Promise<SnapshotRead> {
    return this.getJson<SnapshotRead>(
      withQuery(`/conversations/${payload.conversationId}/timeline-state`, {
        at: payload.at,
      }),
    )
  }

  async importConversation(payload: ImportConversationFromFileInput): Promise<ImportResponse> {
    const bytes = await readFile(payload.filePath)
    const formData = new FormData()

    formData.append(
      'file',
      new Blob([bytes], { type: 'text/plain;charset=utf-8' }),
      path.basename(payload.filePath),
    )
    formData.append('self_display_name', payload.selfDisplayName)

    if (payload.autoAnalyze !== undefined) {
      formData.append('auto_analyze', String(payload.autoAnalyze))
    }

    return this.requestJson<ImportResponse>('/imports/qq-text', {
      method: 'POST',
      body: formData,
    })
  }

  async startAnalysis(conversationId: number): Promise<JobRead> {
    return this.sendJson<JobRead>(`/conversations/${conversationId}/start-analysis`, 'POST', {})
  }

  async listConversationJobs(payload: ListConversationJobsInput): Promise<JobRead[]> {
    return this.getJson<JobRead[]>(
      withQuery(`/conversations/${payload.conversationId}/jobs`, {
        limit: payload.limit,
      }),
    )
  }

  async readJob(jobId: number): Promise<JobRead> {
    return this.getJson<JobRead>(`/jobs/${jobId}`)
  }

  async rerunAnalysis(conversationId: number): Promise<JobRead> {
    return this.sendJson<JobRead>(`/conversations/${conversationId}/rerun-analysis`, 'POST', {})
  }

  async createSimulation(payload: SimulationCreate): Promise<SimulationJobRead> {
    return this.sendJson<SimulationJobRead>('/simulations', 'POST', payload)
  }

  async listConversationSimulationJobs(payload: ListConversationSimulationJobsInput): Promise<SimulationJobRead[]> {
    return this.getJson<SimulationJobRead[]>(
      withQuery(`/conversations/${payload.conversationId}/simulation-jobs`, {
        limit: payload.limit,
      }),
    )
  }

  async readSimulation(simulationId: number): Promise<SimulationRead> {
    return this.getJson<SimulationRead>(`/simulations/${simulationId}`)
  }

  private async getJson<T>(pathname: string): Promise<T> {
    return this.requestJson<T>(pathname, { method: 'GET' })
  }

  private async sendJson<T>(pathname: string, method: 'POST' | 'PUT', payload: Record<string, unknown>): Promise<T> {
    const headers = new Headers()
    headers.set('Content-Type', 'application/json')

    return this.requestJson<T>(pathname, {
      method,
      headers,
      body: JSON.stringify(payload),
    })
  }

  private async requestJson<T>(pathname: string, init: RequestInit): Promise<T> {
    const response = await this.request(pathname, init)

    if (response.status === 204) {
      return undefined as T
    }

    return (await response.json()) as T
  }

  private async request(pathname: string, init: RequestInit): Promise<Response> {
    const headers = new Headers(init.headers)

    if (this.options.apiAuthToken) {
      headers.set(DESKTOP_API_AUTH_HEADER, this.options.apiAuthToken)
    }

    const response = await fetch(`${this.options.apiOrigin}${pathname}`, {
      ...init,
      headers,
    })

    if (!response.ok) {
      const detail = (await response.text()).trim()
      throw new Error(`API request failed: ${response.status}${detail ? ` ${detail}` : ''}`)
    }

    return response
  }
}

export function createDesktopBackendClient(options: DesktopBackendClientOptions): DesktopBackendClient {
  return new DesktopBackendClient(options)
}
