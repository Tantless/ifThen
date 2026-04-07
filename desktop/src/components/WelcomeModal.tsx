type WelcomeModalProps = {
  open: boolean
  onConfigureModel: () => void
  onImportConversation: () => void
  onClose: () => void
}

const overlayStyle = {
  position: 'fixed',
  inset: 0,
  backgroundColor: 'rgba(15, 23, 42, 0.4)',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  padding: '24px',
  zIndex: 20,
} as const

const panelStyle = {
  width: 'min(480px, 100%)',
  backgroundColor: '#fff',
  borderRadius: '16px',
  padding: '24px',
  boxShadow: '0 24px 48px rgba(15, 23, 42, 0.18)',
} as const

export function WelcomeModal({ open, onConfigureModel, onImportConversation, onClose }: WelcomeModalProps) {
  if (!open) {
    return null
  }

  return (
    <div role="dialog" aria-modal="true" aria-labelledby="welcome-modal-title" style={overlayStyle}>
      <section style={panelStyle}>
        <header style={{ marginBottom: '16px' }}>
          <p style={{ margin: 0, color: '#475569', fontSize: '14px' }}>首次启动</p>
          <h2 id="welcome-modal-title" style={{ margin: '8px 0 0', fontSize: '24px' }}>
            欢迎使用桌面壳层
          </h2>
        </header>
        <p style={{ marginTop: 0, color: '#334155', lineHeight: 1.6 }}>
          当前桌面端已经具备启动、读取设置与会话基础能力。接下来请先配置模型，或导入一份会话开始分析。
        </p>
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap', marginTop: '20px' }}>
          <button type="button" onClick={onConfigureModel}>
            配置模型
          </button>
          <button type="button" onClick={onImportConversation}>
            导入会话
          </button>
          <button type="button" onClick={onClose}>
            稍后再说
          </button>
        </div>
      </section>
    </div>
  )
}
