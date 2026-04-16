import type { JobRead } from '../../types/api'
import { requireDesktopBridge } from '../desktop'

export function listConversationJobs(conversationId: number, limit?: number): Promise<JobRead[]> {
  return requireDesktopBridge().jobs.listConversationJobs({ conversationId, limit })
}

export function readJob(jobId: number): Promise<JobRead> {
  return requireDesktopBridge().jobs.readJob(jobId)
}

export function rerunAnalysis(conversationId: number): Promise<JobRead> {
  return requireDesktopBridge().jobs.rerunAnalysis(conversationId)
}
