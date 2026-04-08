type WelcomeModalProps = {
  open: boolean
  onConfigureModel: () => void
  onImportConversation: () => void
  onClose: () => void
}

export function WelcomeModal({ open, onConfigureModel, onImportConversation, onClose }: WelcomeModalProps) {
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
          当前桌面端已经具备启动、读取设置与会话基础能力。接下来请先配置模型，或导入一份会话开始分析。
        </p>
        <div className="desktop-modal__actions">
          <button type="button" className="desktop-modal__button desktop-modal__button--primary" onClick={onConfigureModel}>
            配置模型
          </button>
          <button type="button" className="desktop-modal__button" onClick={onImportConversation}>
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
