import { useEffect, useState } from 'react'

import { AvatarPicker } from './AvatarPicker'

type SelfAvatarDialogProps = {
  open: boolean
  initialAvatarUrl: string
  pending?: boolean
  errorMessage?: string | null
  onClose: () => void
  onSave: (avatarUrl: string) => Promise<void> | void
}

export function SelfAvatarDialog({
  open,
  initialAvatarUrl,
  pending = false,
  errorMessage,
  onClose,
  onSave,
}: SelfAvatarDialogProps) {
  const [selectedAvatarUrl, setSelectedAvatarUrl] = useState(initialAvatarUrl)

  useEffect(() => {
    if (open) {
      setSelectedAvatarUrl(initialAvatarUrl)
    }
  }, [initialAvatarUrl, open])

  if (!open) {
    return null
  }

  return (
    <div className="desktop-modal" role="dialog" aria-modal="true" aria-labelledby="self-avatar-dialog-title">
      <section className="desktop-modal__panel">
        <header className="desktop-modal__header desktop-modal__header--split">
          <div>
            <p className="desktop-modal__eyebrow">头像</p>
            <h2 id="self-avatar-dialog-title" className="desktop-modal__title">
              更换头像
            </h2>
          </div>
          <button type="button" className="desktop-modal__button" onClick={onClose}>
            关闭
          </button>
        </header>

        <AvatarPicker title="我的头像" selectedAvatarUrl={selectedAvatarUrl} onChange={setSelectedAvatarUrl} />

        {errorMessage ? (
          <p role="alert" className="desktop-modal__error">
            {errorMessage}
          </p>
        ) : null}

        <div className="desktop-modal__actions">
          <button
            type="button"
            className="desktop-modal__button desktop-modal__button--primary"
            disabled={pending}
            onClick={() => {
              void onSave(selectedAvatarUrl)
            }}
          >
            {pending ? '保存中…' : '保存头像'}
          </button>
          <button type="button" className="desktop-modal__button" onClick={onClose} disabled={pending}>
            取消
          </button>
        </div>
      </section>
    </div>
  )
}
