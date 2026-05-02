import type {
  BranchMessageCreate,
  BranchMessageRead,
  BranchReplyJobRead,
  BranchSessionCreate,
  BranchSessionRead,
} from '../../types/api'
import { requireDesktopBridge } from '../desktop'

export function createBranchSession(payload: BranchSessionCreate): Promise<BranchSessionRead> {
  return requireDesktopBridge().branchSessions.create(payload)
}

export function readBranchSession(branchSessionId: number): Promise<BranchSessionRead> {
  return requireDesktopBridge().branchSessions.read(branchSessionId)
}

export function appendBranchMessage(
  branchSessionId: number,
  payload: BranchMessageCreate,
): Promise<BranchMessageRead> {
  return requireDesktopBridge().branchSessions.appendMessage(branchSessionId, payload)
}

export function createBranchReplyJob(branchSessionId: number): Promise<BranchReplyJobRead> {
  return requireDesktopBridge().branchSessions.createReplyJob(branchSessionId)
}

export function listBranchReplyJobs(branchSessionId: number, limit?: number): Promise<BranchReplyJobRead[]> {
  return requireDesktopBridge().branchSessions.listReplyJobs({ branchSessionId, limit })
}
