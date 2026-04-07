type BootScreenProps = {
  label: string
  detail?: string
}

export function BootScreen({ label, detail }: BootScreenProps) {
  return (
    <main className="boot-screen" aria-live="polite">
      <div className="boot-card">
        <h1>{label}</h1>
        <p>{detail ?? '应用即将进入主界面'}</p>
      </div>
    </main>
  )
}
