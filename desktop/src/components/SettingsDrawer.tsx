import { useEffect, useState } from 'react'

import type { SettingsFormState } from '../lib/adapters'

const DRAWER_TRANSITION_MS = 220

function scheduleEnterTransition(callback: () => void): () => void {
  if (typeof window === 'undefined') {
    callback()
    return () => undefined
  }

  let cancelled = false
  let firstFrameId: number | null = null
  let secondFrameId: number | null = null
  const requestFrame =
    typeof window.requestAnimationFrame === 'function'
      ? window.requestAnimationFrame.bind(window)
      : (frameCallback: FrameRequestCallback) => window.setTimeout(() => frameCallback(performance.now()), 16)
  const cancelFrame =
    typeof window.cancelAnimationFrame === 'function'
      ? window.cancelAnimationFrame.bind(window)
      : (frameId: number) => window.clearTimeout(frameId)

  firstFrameId = requestFrame(() => {
    secondFrameId = requestFrame(() => {
      if (!cancelled) {
        callback()
      }
    })
  })

  return () => {
    cancelled = true
    if (firstFrameId !== null) {
      cancelFrame(firstFrameId)
    }
    if (secondFrameId !== null) {
      cancelFrame(secondFrameId)
    }
  }
}

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
  const [shouldRender, setShouldRender] = useState(open)
  const [isOpenVisual, setIsOpenVisual] = useState(open)

  const handleSubmit = async () => {
    await onSave(formState)
  }

  useEffect(() => {
    if (open) {
      setFormState(initialState)
    }
  }, [initialState, open])

  useEffect(() => {
    if (open) {
      setShouldRender(true)
      const cancelEnterTransition = scheduleEnterTransition(() => {
        setIsOpenVisual(true)
      })

      return () => {
        cancelEnterTransition()
      }
    }

    setIsOpenVisual(false)

    if (!shouldRender) {
      return
    }

    const exitTimer = window.setTimeout(() => {
      setShouldRender(false)
    }, DRAWER_TRANSITION_MS)

    return () => {
      window.clearTimeout(exitTimer)
    }
  }, [open, shouldRender])

  if (!shouldRender) {
    return null
  }

  return (
    <div
      className="desktop-drawer-shell"
      data-open={isOpenVisual ? 'true' : 'false'}
      role="presentation"
      onClick={() => {
        if (!pending) {
          onClose()
        }
      }}
    >
      <aside
        className="desktop-drawer"
        aria-label="模型设置"
        onClick={(event) => {
          event.stopPropagation()
        }}
      >
        <form
          className="desktop-drawer__form"
          onSubmit={async (event) => {
            event.preventDefault()
            await handleSubmit()
          }}
        >
          <header className="desktop-drawer__header">
            <div>
              <p className="desktop-drawer__eyebrow">设置</p>
              <h2 className="desktop-drawer__title">模型配置</h2>
            </div>
            <button
              type="button"
              className="desktop-drawer__button desktop-drawer__button--primary"
              disabled={pending}
              onClick={() => {
                void handleSubmit()
              }}
            >
              {pending ? '保存中…' : '保存'}
            </button>
          </header>

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
            <span className="desktop-drawer__label">Chat Model（分析）</span>
            <input
              className="desktop-drawer__input"
              type="text"
              value={formState.chatModel}
              placeholder="gpt-5.4"
              onChange={(event) => setFormState((current) => ({ ...current, chatModel: event.target.value }))}
            />
          </label>

          <label className="desktop-drawer__field">
            <span className="desktop-drawer__label">Simulation Base URL（推演）</span>
            <input
              className="desktop-drawer__input"
              type="url"
              value={formState.simulationBaseUrl}
              placeholder="留空则使用分析 Base URL"
              onChange={(event) => setFormState((current) => ({ ...current, simulationBaseUrl: event.target.value }))}
            />
          </label>

          <label className="desktop-drawer__field">
            <span className="desktop-drawer__label">Simulation API Key（推演）</span>
            <input
              className="desktop-drawer__input"
              type="password"
              value={formState.simulationApiKey}
              placeholder="留空则使用分析 API Key"
              onChange={(event) => setFormState((current) => ({ ...current, simulationApiKey: event.target.value }))}
            />
          </label>

          <label className="desktop-drawer__field">
            <span className="desktop-drawer__label">Simulation Model（推演）</span>
            <input
              className="desktop-drawer__input"
              type="text"
              value={formState.simulationModel}
              placeholder="留空则使用分析模型"
              onChange={(event) => setFormState((current) => ({ ...current, simulationModel: event.target.value }))}
            />
          </label>

          <label className="desktop-drawer__field">
            <span className="desktop-drawer__label">默认推演模式</span>
            <select
              className="desktop-drawer__input"
              value={formState.simulationMode}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  simulationMode: event.target.value as SettingsFormState['simulationMode'],
                }))
              }
            >
              <option value="single_reply">单轮回复</option>
              <option value="short_thread">短链推演</option>
            </select>
          </label>

          <label className="desktop-drawer__field">
            <span className="desktop-drawer__label">默认推演轮数</span>
            <input
              className="desktop-drawer__input"
              type="number"
              min={1}
              max={6}
              value={formState.simulationTurnCount}
              onChange={(event) =>
                setFormState((current) => ({
                  ...current,
                  simulationTurnCount: Math.min(6, Math.max(1, Number.parseInt(event.target.value, 10) || 1)),
                }))
              }
            />
          </label>

          {errorMessage ? (
            <p role="alert" className="desktop-drawer__error">
              {errorMessage}
            </p>
          ) : null}
        </form>
      </aside>
    </div>
  )
}
