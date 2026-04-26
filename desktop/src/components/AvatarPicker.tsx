import { useState } from 'react'

import { pickAvatarFile } from '../lib/desktop'
import { AVATAR_PRESETS } from '../lib/avatarPresets'

type AvatarPickerProps = {
  title: string
  selectedAvatarUrl: string
  onChange: (value: string) => void
  uploadLabel?: string
}

export function AvatarPicker({
  title,
  selectedAvatarUrl,
  onChange,
  uploadLabel = '上传本地头像',
}: AvatarPickerProps) {
  const [uploadPending, setUploadPending] = useState(false)

  const handleUpload = async () => {
    setUploadPending(true)

    try {
      const nextAvatar = await pickAvatarFile()
      if (nextAvatar?.dataUrl) {
        onChange(nextAvatar.dataUrl)
      }
    } finally {
      setUploadPending(false)
    }
  }

  return (
    <section className="avatar-picker">
      <div className="avatar-picker__header">
        <span className="avatar-picker__title">{title}</span>
        <button
          type="button"
          className="desktop-modal__button"
          onClick={() => {
            void handleUpload()
          }}
          disabled={uploadPending}
        >
          {uploadPending ? '读取中…' : uploadLabel}
        </button>
      </div>

      <div className="avatar-picker__current">
        <img className="avatar-picker__preview" src={selectedAvatarUrl} alt={title} />
      </div>

      <div className="avatar-picker__grid">
        {AVATAR_PRESETS.map((preset) => (
          <button
            key={preset.id}
            type="button"
            data-testid={`avatar-preset-${preset.id}`}
            className={`avatar-picker__option${selectedAvatarUrl === preset.url ? ' avatar-picker__option--active' : ''}`}
            onClick={() => onChange(preset.url)}
          >
            <img className="avatar-picker__option-image" src={preset.url} alt={preset.name} />
          </button>
        ))}
      </div>
    </section>
  )
}
