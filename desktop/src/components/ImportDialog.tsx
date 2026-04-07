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

const overlayStyle = {
  position: 'fixed',
  inset: 0,
  backgroundColor: 'rgba(15, 23, 42, 0.4)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '24px',
  zIndex: 25,
} as const

const panelStyle = {
  width: 'min(520px, 100%)',
  backgroundColor: '#fff',
  borderRadius: '16px',
  padding: '24px',
  boxShadow: '0 24px 48px rgba(15, 23, 42, 0.18)',
} as const

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
    <div role="dialog" aria-modal="true" aria-labelledby="import-dialog-title" style={overlayStyle}>
      <section style={panelStyle}>
        <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
          <div>
            <p style={{ margin: 0, color: '#475569', fontSize: '14px' }}>导入</p>
            <h2 id="import-dialog-title" style={{ margin: '8px 0 0' }}>
              导入 QQ 聊天导出
            </h2>
          </div>
          <button type="button" onClick={onClose}>
            关闭
          </button>
        </header>

        <form
          style={{ display: 'grid', gap: '16px', marginTop: '24px' }}
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
          <div style={{ display: 'grid', gap: '8px' }}>
            <span>导出文件</span>
            <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
              <button
                type="button"
                onClick={async () => {
                  const nextPath = await openImportFileDialog()
                  setSelectedPath(nextPath ?? '')
                }}
              >
                选择文件
              </button>
              <code style={{ whiteSpace: 'pre-wrap', wordBreak: 'break-all' }}>
                {selectedPath || '尚未选择文件'}
              </code>
            </div>
          </div>

          <label style={{ display: 'grid', gap: '8px' }}>
            <span>你的显示名</span>
            <input
              type="text"
              value={selfDisplayName}
              placeholder="例如：我"
              onChange={(event) => setSelfDisplayName(event.target.value)}
            />
          </label>

          <p style={{ margin: 0, color: '#475569', lineHeight: 1.5 }}>
            选择本地 QQ 导出文本后，桌面壳会读取 UTF-8 内容并提交到现有导入接口。
          </p>

          {errorMessage ? (
            <p role="alert" style={{ margin: 0, color: '#b91c1c' }}>
              {errorMessage}
            </p>
          ) : null}

          <button type="submit" disabled={pending || !selectedPath.trim() || !selfDisplayName.trim()}>
            {pending ? '导入中…' : '提交导入'}
          </button>
        </form>
      </section>
    </div>
  )
}
