import type { JobRead } from '../types/api'
import type { FrontAnalysisProgress } from '../frontui/types'

function trimText(value: string | null | undefined): string {
  return value?.trim() ?? ''
}

function resolveCompositeStageLabel(statusMessage: string | null): string {
  const normalized = trimText(statusMessage).toLowerCase()

  if (normalized.includes('topic resolution') || normalized.includes('topic merge review')) {
    return '话题整理'
  }

  if (normalized.includes('persona ')) {
    return '人设归纳'
  }

  if (normalized.includes('snapshot')) {
    return '关系快照'
  }

  return '主题分析'
}

export function resolveJobStageLabel(job: JobRead | null | undefined): string {
  if (!job) {
    return ''
  }

  if (job.status === 'queued') {
    return '等待启动'
  }

  if (job.status === 'completed') {
    return '已分析'
  }

  if (job.status === 'failed') {
    return '失败'
  }

  switch (job.current_stage) {
    case 'created':
      return '等待启动'
    case 'parsing':
      return '数据清洗'
    case 'segmenting':
      return '对话分段'
    case 'summarizing':
      return '摘要生成'
    case 'topic_persona_snapshot':
      return resolveCompositeStageLabel(job.status_message)
    case 'completed':
      return '已分析'
    case 'failed':
      return '失败'
    default:
      return '分析中'
  }
}

export function resolveJobStageProgressLabel(job: JobRead | null | undefined): string {
  if (!job) {
    return ''
  }

  if (job.status === 'completed' || job.status === 'failed') {
    return resolveJobStageLabel(job)
  }

  const percent = Number.isFinite(job.current_stage_percent) ? Math.max(0, Math.round(job.current_stage_percent)) : 0
  return `${resolveJobStageLabel(job)} ${percent}%`
}

export function resolveJobProgress(job: JobRead | null | undefined): FrontAnalysisProgress | null {
  if (!job) {
    return null
  }

  if (job.status === 'completed') {
    return null
  }

  if (job.status === 'failed') {
    return {
      label: '失败',
      percent: 100,
      tone: 'failed',
    }
  }

  const percent = Number.isFinite(job.current_stage_percent) ? Math.max(0, Math.min(100, Math.round(job.current_stage_percent))) : 0

  return {
    label: resolveJobStageProgressLabel(job),
    percent,
    tone: 'running',
  }
}
