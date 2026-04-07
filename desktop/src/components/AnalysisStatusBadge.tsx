type AnalysisStatusBadgeProps = {
  status: string | null | undefined
  progressPercent?: number | null
}

function resolveStatusLabel(status: string | null | undefined, progressPercent?: number | null): string {
  if (status === 'running' || status === 'queued') {
    const progress = Math.max(0, Math.round(progressPercent ?? 0))
    return progress > 0 ? `分析中 ${progress}%` : '排队分析中'
  }

  if (status === 'completed') {
    return '分析完成'
  }

  if (status === 'failed') {
    return '分析失败'
  }

  return '待分析'
}

export function AnalysisStatusBadge({ status, progressPercent }: AnalysisStatusBadgeProps) {
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
      {resolveStatusLabel(status, progressPercent)}
    </span>
  )
}
