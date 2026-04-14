import type { CSSProperties } from 'react'

export type WindowTitleBarProps = {
  appTitle: string
  isMaximized: boolean
  onMinimize: () => void
  onToggleMaximize: () => void
  onClose: () => void
}

const dragRegionStyle = { WebkitAppRegion: 'drag' } as CSSProperties
const noDragRegionStyle = { WebkitAppRegion: 'no-drag' } as CSSProperties

type TitleBarSvgIconProps = {
  className: string
  path: string
}

function TitleBarSvgIcon({ className, path }: TitleBarSvgIconProps) {
  return (
    <svg
      aria-hidden="true"
      viewBox="0 0 16 16"
      fill="currentColor"
      className={`${className} pointer-events-none h-3 w-3`}
    >
      <path d={path} />
    </svg>
  )
}

function MinimizeIcon() {
  return (
    <TitleBarSvgIcon
      className="desktop-titlebar__icon desktop-titlebar__icon--minimize"
      path="M3 8c0-.28.22-.5.5-.5h9a.5.5 0 0 1 0 1h-9A.5.5 0 0 1 3 8Z"
    />
  )
}

function MaximizeIcon() {
  return (
    <TitleBarSvgIcon
      className="desktop-titlebar__icon desktop-titlebar__icon--maximize"
      path="M2 4.5A2.5 2.5 0 0 1 4.5 2h7A2.5 2.5 0 0 1 14 4.5v7a2.5 2.5 0 0 1-2.5 2.5h-7A2.5 2.5 0 0 1 2 11.5v-7ZM4.5 3C3.67 3 3 3.67 3 4.5v7c0 .83.67 1.5 1.5 1.5h7c.83 0 1.5-.67 1.5-1.5v-7c0-.83-.67-1.5-1.5-1.5h-7Z"
    />
  )
}

function RestoreIcon() {
  return (
    <TitleBarSvgIcon
      className="desktop-titlebar__icon desktop-titlebar__icon--restore"
      path="M5.08 4c.21-.58.77-1 1.42-1H10a3 3 0 0 1 3 3v3.5c0 .65-.42 1.2-1 1.41V6a2 2 0 0 0-2-2H5.08ZM4.5 5h5c.83 0 1.5.67 1.5 1.5v5c0 .83-.67 1.5-1.5 1.5h-5A1.5 1.5 0 0 1 3 11.5v-5C3 5.67 3.67 5 4.5 5Zm0 1a.5.5 0 0 0-.5.5v5c0 .28.22.5.5.5h5a.5.5 0 0 0 .5-.5v-5a.5.5 0 0 0-.5-.5h-5Z"
    />
  )
}

function CloseIcon() {
  return (
    <TitleBarSvgIcon
      className="desktop-titlebar__icon desktop-titlebar__icon--close"
      path="m2.59 2.72.06-.07a.5.5 0 0 1 .63-.06l.07.06L8 7.29l4.65-4.64a.5.5 0 0 1 .7.7L8.71 8l4.64 4.65c.18.17.2.44.06.63l-.06.07a.5.5 0 0 1-.63.06l-.07-.06L8 8.71l-4.65 4.64a.5.5 0 0 1-.7-.7L7.29 8 2.65 3.35a.5.5 0 0 1-.06-.63l.06-.07-.06.07Z"
    />
  )
}

export function WindowTitleBar({
  appTitle,
  isMaximized,
  onMinimize,
  onToggleMaximize,
  onClose,
}: WindowTitleBarProps) {
  const maximizeLabel = isMaximized ? '还原窗口' : '最大化窗口'

  return (
    <header
      className="desktop-titlebar flex h-10 w-full items-stretch justify-between border-b border-[color:var(--if-divider)] bg-[var(--if-bg-toolbar)] text-[var(--if-text-primary)] select-none"
      style={dragRegionStyle}
    >
      <div className="desktop-titlebar__drag-region flex min-w-0 flex-1 items-center px-4" style={dragRegionStyle}>
        <span className="truncate text-[13px] font-medium tracking-[0.01em]">{appTitle}</span>
      </div>

      <div
        className="desktop-titlebar__actions desktop-titlebar__controls flex items-stretch"
        style={noDragRegionStyle}
      >
        <button
          type="button"
          className="desktop-titlebar__button desktop-titlebar__button--minimize flex h-10 w-12 items-center justify-center text-sm text-[var(--if-text-secondary)] transition-colors duration-150 hover:bg-white/50 hover:text-[var(--if-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(7,193,96,0.22)]"
          aria-label="最小化窗口"
          onClick={onMinimize}
        >
          <MinimizeIcon />
        </button>
        <button
          type="button"
          className="desktop-titlebar__button desktop-titlebar__button--maximize flex h-10 w-12 items-center justify-center text-sm text-[var(--if-text-secondary)] transition-colors duration-150 hover:bg-white/50 hover:text-[var(--if-text-primary)] focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(7,193,96,0.22)]"
          aria-label={maximizeLabel}
          onClick={onToggleMaximize}
        >
          {isMaximized ? <RestoreIcon /> : <MaximizeIcon />}
        </button>
        <button
          type="button"
          className="desktop-titlebar__button desktop-titlebar__button--close flex h-10 w-12 items-center justify-center text-sm text-[var(--if-text-secondary)] transition-colors duration-150 hover:bg-[#d04b57] hover:text-white focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-[rgba(208,75,87,0.22)]"
          aria-label="关闭窗口"
          onClick={onClose}
        >
          <CloseIcon />
        </button>
      </div>
    </header>
  )
}
