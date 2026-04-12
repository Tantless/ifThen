import { useEffect, useState } from 'react'

import { AvatarPicker } from './AvatarPicker'

type WelcomeModalProps = {
  open: boolean
  initialSelfAvatarUrl: string
  onConfigureModel: (avatarUrl: string) => Promise<void> | void
  onImportConversation: (avatarUrl: string) => Promise<void> | void
  onClose: () => void
}

export function WelcomeModal({
  open,
  initialSelfAvatarUrl,
  onConfigureModel,
  onImportConversation,
  onClose,
}: WelcomeModalProps) {
  const [selectedAvatarUrl, setSelectedAvatarUrl] = useState(initialSelfAvatarUrl)

  useEffect(() => {
    if (open) {
      setSelectedAvatarUrl(initialSelfAvatarUrl)
    }
  }, [initialSelfAvatarUrl, open])

  if (!open) {
    return null
  }

  return (
    <div className="desktop-modal" role="dialog" aria-modal="true" aria-labelledby="welcome-modal-title">
      <section className="desktop-modal__panel desktop-modal__panel--welcome">
        <header className="desktop-modal__header">
          <p className="desktop-modal__eyebrow">首次启动</p>
          <h2 id="welcome-modal-title" className="desktop-modal__title">
            欢迎使用桌面壳层
          </h2>
        </header>
        <p className="desktop-modal__body">
          当前桌面端已经具备启动、读取设置与会话基础能力。先选一个你自己的头像，之后它会用于聊天界面里的“我”。
        </p>
        <AvatarPicker title="我的头像" selectedAvatarUrl={selectedAvatarUrl} onChange={setSelectedAvatarUrl} />
        <div className="desktop-modal__actions">
          <button
            type="button"
            className="desktop-modal__button desktop-modal__button--primary"
            onClick={() => {
              void onConfigureModel(selectedAvatarUrl)
            }}
          >
            配置模型
          </button>
          <button
            type="button"
            className="desktop-modal__button"
            onClick={() => {
              void onImportConversation(selectedAvatarUrl)
            }}
          >
            导入会话
          </button>
          <button type="button" className="desktop-modal__button" onClick={onClose}>
            稍后再说
          </button>
        </div>
      </section>
    </div>
  )
}
