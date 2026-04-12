import { useEffect, useState } from 'react'

import { openImportFileDialog } from '../lib/desktop'
import { AvatarPicker } from './AvatarPicker'
import { DEFAULT_OTHER_AVATAR_URL } from '../lib/avatarPresets'

type ImportDialogSubmitPayload = {
  filePath: string
  selfDisplayName: string
  autoAnalyze: boolean
  otherAvatarUrl: string
}

type ImportDialogProps = {
  open: boolean
  pending?: boolean
  errorMessage?: string | null
  onClose: () => void
  onSubmit: (payload: ImportDialogSubmitPayload) => Promise<void> | void
}

export function ImportDialog({
  open,
  pending = false,
  errorMessage,
  onClose,
  onSubmit,
}: ImportDialogProps) {
  const [selectedPath, setSelectedPath] = useState<string>('')
  const [selfDisplayName, setSelfDisplayName] = useState('')
  const [importMode, setImportMode] = useState<'import_only' | 'import_and_analyze'>('import_only')
  const [otherAvatarUrl, setOtherAvatarUrl] = useState(DEFAULT_OTHER_AVATAR_URL)

  useEffect(() => {
    if (open) {
      setSelectedPath('')
      setSelfDisplayName('')
      setImportMode('import_only')
      setOtherAvatarUrl(DEFAULT_OTHER_AVATAR_URL)
    }
  }, [open])

  if (!open) {
    return null
  }

  return (
    <div className="desktop-modal" role="dialog" aria-modal="true" aria-labelledby="import-dialog-title">
      <section className="desktop-modal__panel desktop-modal__panel--import">
        <header className="desktop-modal__header desktop-modal__header--split">
          <div>
            <p className="desktop-modal__eyebrow">导入</p>
            <h2 id="import-dialog-title" className="desktop-modal__title">
              导入 QQ 聊天导出
            </h2>
          </div>
          <button type="button" className="desktop-modal__button" onClick={onClose}>
            关闭
          </button>
        </header>

        <form
          className="desktop-modal__form"
          onSubmit={async (event) => {
            event.preventDefault()
            if (!selectedPath.trim() || !selfDisplayName.trim()) {
              return
            }

            await onSubmit({
              filePath: selectedPath.trim(),
              selfDisplayName: selfDisplayName.trim(),
              autoAnalyze: importMode === 'import_and_analyze',
              otherAvatarUrl,
            })
          }}
        >
          <div className="desktop-modal__field">
            <span className="desktop-modal__label">导出文件</span>
            <div className="desktop-modal__path-row">
              <button
                type="button"
                className="desktop-modal__button"
                onClick={async () => {
                  const nextPath = await openImportFileDialog()
                  setSelectedPath(nextPath ?? '')
                }}
              >
                选择文件
              </button>
              <code className="desktop-modal__code">
                {selectedPath || '尚未选择文件'}
              </code>
            </div>
          </div>

          <label className="desktop-modal__field">
            <span className="desktop-modal__label">你的显示名</span>
            <input
              className="desktop-modal__input"
              type="text"
              value={selfDisplayName}
              placeholder="例如：我"
              onChange={(event) => setSelfDisplayName(event.target.value)}
            />
          </label>

          <AvatarPicker title="对方头像" selectedAvatarUrl={otherAvatarUrl} onChange={setOtherAvatarUrl} />

          <label className="desktop-modal__field">
            <span className="desktop-modal__label">导入模式</span>
            <select
              className="desktop-modal__input"
              value={importMode}
              onChange={(event) => setImportMode(event.target.value as 'import_only' | 'import_and_analyze')}
            >
              <option value="import_only">只导入</option>
              <option value="import_and_analyze">导入并分析</option>
            </select>
          </label>

          <p className="desktop-modal__body desktop-modal__body--muted">
            {importMode === 'import_and_analyze'
              ? '导入后将自动进行分段、话题提取、人格分析等操作。'
              : '导入后仅展示聊天记录，你可以稍后手动触发分析。'}
          </p>

          {errorMessage ? (
            <p role="alert" className="desktop-modal__error">
              {errorMessage}
            </p>
          ) : null}

          <button
            type="submit"
            className="desktop-modal__button desktop-modal__button--primary"
            disabled={pending || !selectedPath.trim() || !selfDisplayName.trim()}
          >
            {pending ? '导入中…' : '提交导入'}
          </button>
        </form>
      </section>
    </div>
  )
}
