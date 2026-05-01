import type { JobRead } from '../types/api'
import type { FrontAnalysisProgress, FrontAnalysisStage } from '../frontui/types'

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

function normalizeStageStatus(status: string): FrontAnalysisStage['status'] {
  if (status === 'running' || status === 'completed' || status === 'failed') {
    return status
  }
  return 'waiting'
}

function calculateStagePercent(completedUnits: number, totalUnits: number): number {
  if (totalUnits <= 0) {
    return 0
  }
  return Math.max(0, Math.min(100, Math.round((completedUnits * 100) / totalUnits)))
}

export function resolveJobStages(job: JobRead | null | undefined): FrontAnalysisStage[] {
  if (!job?.stages?.length) {
    return []
  }

  return job.stages.map((stage) => {
    const completedUnits = Number.isFinite(stage.completed_units) ? Math.max(0, Math.round(stage.completed_units)) : 0
    const totalUnits = Number.isFinite(stage.total_units) ? Math.max(0, Math.round(stage.total_units)) : 0

    return {
      id: stage.id,
      label: stage.label,
      status: normalizeStageStatus(stage.status),
      completedUnits,
      totalUnits,
      percent: calculateStagePercent(completedUnits, totalUnits),
    }
  })
}

function formatStageLabel(stage: FrontAnalysisStage): string {
  const unitPart = stage.totalUnits > 0 ? ` ${stage.completedUnits}/${stage.totalUnits}` : ''
  return `${stage.label}${unitPart} · ${stage.percent}%`
}

function resolveStructuredStageProgressLabel(stages: FrontAnalysisStage[]): string | null {
  const runningStages = stages.filter((stage) => stage.status === 'running')

  if (runningStages.length === 0) {
    return null
  }

  if (runningStages.length === 1) {
    return formatStageLabel(runningStages[0])
  }

  const labels = runningStages.map((stage) => stage.label).join(' / ')
  const percent = Math.min(...runningStages.map((stage) => stage.percent))
  return `${labels} · ${percent}%`
}

function resolveStructuredStagePercent(stages: FrontAnalysisStage[]): number | null {
  const runningStages = stages.filter((stage) => stage.status === 'running')
  if (runningStages.length === 0) {
    return null
  }
  return Math.min(...runningStages.map((stage) => stage.percent))
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

  const structuredLabel = resolveStructuredStageProgressLabel(resolveJobStages(job))
  if (structuredLabel) {
    return structuredLabel
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

  const stages = resolveJobStages(job)

  if (job.status === 'failed') {
    return {
      label: '失败',
      percent: 100,
      tone: 'failed',
      ...(stages.length > 0 ? { stages } : {}),
    }
  }

  const structuredPercent = resolveStructuredStagePercent(stages)
  const percent =
    structuredPercent ?? (Number.isFinite(job.current_stage_percent) ? Math.max(0, Math.min(100, Math.round(job.current_stage_percent))) : 0)

  return {
    label: resolveJobStageProgressLabel(job),
    percent,
    tone: 'running',
    ...(stages.length > 0 ? { stages } : {}),
  }
}
