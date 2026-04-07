import { useEffect, useState } from 'react'

import type { SettingsFormState } from '../lib/adapters'

type SettingsDrawerProps = {
  open: boolean
  initialState: SettingsFormState
  pending?: boolean
  errorMessage?: string | null
  onClose: () => void
  onSave: (state: SettingsFormState) => Promise<void> | void
}

const drawerStyle = {
  position: 'fixed',
  top: 0,
  right: 0,
  bottom: 0,
  width: 'min(420px, 100%)',
  backgroundColor: '#fff',
  boxShadow: '-12px 0 32px rgba(15, 23, 42, 0.18)',
  padding: '24px',
  zIndex: 30,
  overflowY: 'auto',
} as const

export function SettingsDrawer({
  open,
  initialState,
  pending = false,
  errorMessage,
  onClose,
  onSave,
}: SettingsDrawerProps) {
  const [formState, setFormState] = useState<SettingsFormState>(initialState)

  useEffect(() => {
    if (open) {
      setFormState(initialState)
    }
  }, [initialState, open])

  if (!open) {
    return null
  }

  return (
    <aside aria-label="模型设置" style={drawerStyle}>
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '12px' }}>
        <div>
          <p style={{ margin: 0, color: '#475569', fontSize: '14px' }}>设置</p>
          <h2 style={{ margin: '8px 0 0' }}>模型配置</h2>
        </div>
        <button type="button" onClick={onClose}>
          关闭
        </button>
      </header>

      <form
        style={{ display: 'grid', gap: '16px', marginTop: '24px' }}
        onSubmit={async (event) => {
          event.preventDefault()
          await onSave(formState)
        }}
      >
        <label style={{ display: 'grid', gap: '8px' }}>
          <span>Base URL</span>
          <input
            type="url"
            value={formState.baseUrl}
            placeholder="https://api.openai.com/v1"
            onChange={(event) => setFormState((current) => ({ ...current, baseUrl: event.target.value }))}
          />
        </label>

        <label style={{ display: 'grid', gap: '8px' }}>
          <span>API Key</span>
          <input
            type="password"
            value={formState.apiKey}
            placeholder="sk-..."
            onChange={(event) => setFormState((current) => ({ ...current, apiKey: event.target.value }))}
          />
        </label>

        <label style={{ display: 'grid', gap: '8px' }}>
          <span>Chat Model</span>
          <input
            type="text"
            value={formState.chatModel}
            placeholder="gpt-5.4"
            onChange={(event) => setFormState((current) => ({ ...current, chatModel: event.target.value }))}
          />
        </label>

        {errorMessage ? (
          <p role="alert" style={{ margin: 0, color: '#b91c1c' }}>
            {errorMessage}
          </p>
        ) : null}

        <button type="submit" disabled={pending}>
          {pending ? '保存中…' : '保存'}
        </button>
      </form>
    </aside>
  )
}
