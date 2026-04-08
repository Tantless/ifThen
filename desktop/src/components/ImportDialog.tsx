import { useEffect, useState } from 'react'

import { openImportFileDialog } from '../lib/desktop'

type ImportDialogSubmitPayload = {
  filePath: string
  selfDisplayName: string
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

  useEffect(() => {
    if (open) {
      setSelectedPath('')
      setSelfDisplayName('')
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

          <p className="desktop-modal__body desktop-modal__body--muted">
            选择本地 QQ 导出文本后，桌面壳会读取 UTF-8 内容并提交到现有导入接口。
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
