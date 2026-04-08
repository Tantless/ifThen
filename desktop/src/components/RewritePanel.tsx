import type { ChangeEvent } from 'react'

type RewriteMode = 'single_reply' | 'short_thread'

type RewritePanelProps = {
  originalMessage: string
  targetMessageTimestamp: string
  replacementContent: string
  mode: RewriteMode
  turnCount: number
  pending?: boolean
  errorMessage?: string | null
  onReplacementContentChange: (value: string) => void
  onModeChange: (value: RewriteMode) => void
  onTurnCountChange: (value: number) => void
  onSubmit: () => void
  onCancel: () => void
}

export function RewritePanel({
  originalMessage,
  targetMessageTimestamp,
  replacementContent,
  mode,
  turnCount,
  pending = false,
  errorMessage = null,
  onReplacementContentChange,
  onModeChange,
  onTurnCountChange,
  onSubmit,
  onCancel,
}: RewritePanelProps) {
  const handleReplacementChange = (event: ChangeEvent<HTMLTextAreaElement>) => {
    onReplacementContentChange((event.currentTarget as HTMLTextAreaElement).value)
  }

  const handleModeChange = (event: ChangeEvent<HTMLSelectElement>) => {
    onModeChange((event.currentTarget as HTMLSelectElement).value as RewriteMode)
  }

  const handleTurnCountChange = (event: ChangeEvent<HTMLInputElement>) => {
    onTurnCountChange(Number((event.currentTarget as HTMLInputElement).value))
  }

  return (
    <section className="rewrite-panel">
      <div className="rewrite-panel__header">
        <div>
          <p className="rewrite-panel__eyebrow">改写并推演</p>
          <h3>重写当前消息并生成分支</h3>
        </div>
        <button type="button" disabled={pending} onClick={onCancel}>
          取消
        </button>
      </div>

      <div className="rewrite-panel__section">
        <span className="rewrite-panel__label">原消息</span>
        <p className="rewrite-panel__quote">{originalMessage || '（空消息）'}</p>
      </div>

      <div className="rewrite-panel__section">
        <span className="rewrite-panel__label">发送时间</span>
        <p className="rewrite-panel__quote">{new Date(targetMessageTimestamp).toLocaleString('zh-CN')}</p>
      </div>

      <label className="rewrite-panel__section">
        <span className="rewrite-panel__label">改写内容</span>
        <textarea
          rows={4}
          disabled={pending}
          value={replacementContent}
          onChange={handleReplacementChange}
        />
      </label>

      <div className="rewrite-panel__controls">
        <label>
          <span className="rewrite-panel__label">推演模式</span>
          <select disabled={pending} value={mode} onChange={handleModeChange}>
            <option value="single_reply">单轮回复</option>
            <option value="short_thread">短链推演</option>
          </select>
        </label>

        <label>
          <span className="rewrite-panel__label">推演轮数</span>
          <input
            type="number"
            min={1}
            max={6}
            disabled={pending}
            value={turnCount}
            onChange={handleTurnCountChange}
          />
        </label>
      </div>

      {errorMessage ? (
        <p className="rewrite-panel__error" role="alert">
          {errorMessage}
        </p>
      ) : null}

      <div className="rewrite-panel__footer">
        <button type="button" disabled={pending || replacementContent.trim().length === 0} onClick={onSubmit}>
          {pending ? '推演中…' : '开始推演'}
        </button>
      </div>
    </section>
  )
}
