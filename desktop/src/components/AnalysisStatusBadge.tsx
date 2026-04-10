import type { JobRead } from '../types/api'
import { resolveJobStageProgressLabel } from '../lib/analysisProgress'

type AnalysisStatusBadgeProps = {
  status: string | null | undefined
  progressPercent?: number | null
  currentStage?: string | null
  currentStagePercent?: number | null
  statusMessage?: string | null
}

function resolveStatusLabel(props: AnalysisStatusBadgeProps): string {
  if (!props.status) {
    return '待分析'
  }

  const pseudoJob: JobRead = {
    id: -1,
    status: props.status,
    current_stage: props.currentStage ?? '',
    progress_percent: Math.round(props.progressPercent ?? 0),
    current_stage_percent: Math.round(props.currentStagePercent ?? props.progressPercent ?? 0),
    current_stage_total_units: 0,
    current_stage_completed_units: 0,
    overall_total_units: 0,
    overall_completed_units: 0,
    status_message: props.statusMessage ?? null,
  }

  return resolveJobStageProgressLabel(pseudoJob) || '待分析'
}

export function AnalysisStatusBadge(props: AnalysisStatusBadgeProps) {
  return (
    <span
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        padding: '4px 10px',
        borderRadius: '999px',
        backgroundColor: '#e2e8f0',
        color: '#0f172a',
        fontSize: '12px',
        fontWeight: 600,
      }}
    >
      {resolveStatusLabel(props)}
    </span>
  )
}
