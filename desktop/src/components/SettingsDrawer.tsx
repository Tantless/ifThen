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
    <aside className="desktop-drawer" aria-label="模型设置">
      <header className="desktop-drawer__header">
        <div>
          <p className="desktop-drawer__eyebrow">设置</p>
          <h2 className="desktop-drawer__title">模型配置</h2>
        </div>
        <button type="button" className="desktop-drawer__button" onClick={onClose}>
          关闭
        </button>
      </header>

      <form
        className="desktop-drawer__form"
        onSubmit={async (event) => {
          event.preventDefault()
          await onSave(formState)
        }}
      >
        <label className="desktop-drawer__field">
          <span className="desktop-drawer__label">Base URL</span>
          <input
            className="desktop-drawer__input"
            type="url"
            value={formState.baseUrl}
            placeholder="https://api.openai.com/v1"
            onChange={(event) => setFormState((current) => ({ ...current, baseUrl: event.target.value }))}
          />
        </label>

        <label className="desktop-drawer__field">
          <span className="desktop-drawer__label">API Key</span>
          <input
            className="desktop-drawer__input"
            type="password"
            value={formState.apiKey}
            placeholder="sk-..."
            onChange={(event) => setFormState((current) => ({ ...current, apiKey: event.target.value }))}
          />
        </label>

        <label className="desktop-drawer__field">
          <span className="desktop-drawer__label">Chat Model</span>
          <input
            className="desktop-drawer__input"
            type="text"
            value={formState.chatModel}
            placeholder="gpt-5.4"
            onChange={(event) => setFormState((current) => ({ ...current, chatModel: event.target.value }))}
          />
        </label>

        {errorMessage ? (
          <p role="alert" className="desktop-drawer__error">
            {errorMessage}
          </p>
        ) : null}

        <button type="submit" className="desktop-drawer__button desktop-drawer__button--primary" disabled={pending}>
          {pending ? '保存中…' : '保存'}
        </button>
      </form>
    </aside>
  )
}
