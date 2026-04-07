import { apiClient } from '../apiClient'
import type { JobRead } from '../../types/api'

export function listConversationJobs(conversationId: number, limit?: number): Promise<JobRead[]> {
  const query = limit === undefined ? '' : `?limit=${limit}`
  return apiClient.get<JobRead[]>(`/conversations/${conversationId}/jobs${query}`)
}

export function readJob(jobId: number): Promise<JobRead> {
  return apiClient.get<JobRead>(`/jobs/${jobId}`)
}

export function rerunAnalysis(conversationId: number): Promise<JobRead> {
  return apiClient.post<JobRead>(`/conversations/${conversationId}/rerun-analysis`)
}
