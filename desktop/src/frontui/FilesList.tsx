import { FileText, Folder } from 'lucide-react'

type FileItem = {
  id: string
  name: string
  type: 'file' | 'folder'
  size?: string
  modifiedTime?: string
  conversationId?: number | null
}

type FilesListProps = {
  files: FileItem[]
  onSelectFile: (fileId: string) => void
}

export function FilesList({ files, onSelectFile }: FilesListProps) {
  if (files.length === 0) {
    return (
      <div className="flex h-full flex-col items-center justify-center text-[var(--if-text-tertiary)]">
        <Folder size={64} className="mb-4 opacity-30" />
        <p className="text-sm">暂无文件</p>
        <p className="mt-2 text-xs">聊天记录中的文件会在此显示</p>
      </div>
    )
  }

  return (
    <div className="h-full overflow-y-auto">
      {files.map((file) => (
        <button
          key={file.id}
          type="button"
          onClick={() => onSelectFile(file.id)}
          className="flex w-full cursor-pointer items-center gap-3 border-b border-[color:var(--if-divider)] px-4 py-3 text-left transition-colors duration-150 hover:bg-white/36"
        >
          <div className="flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-[10px] border border-[color:var(--if-divider)] bg-white/72 text-[var(--if-text-secondary)]">
            {file.type === 'folder' ? (
              <Folder size={22} />
            ) : (
              <FileText size={22} />
            )}
          </div>
          <div className="flex-1 min-w-0 text-left">
            <div className="truncate text-sm font-medium text-[var(--if-text-primary)]">{file.name}</div>
            <div className="mt-1 flex gap-2 text-xs text-[var(--if-text-secondary)]">
              {file.size && <span>{file.size}</span>}
              {file.modifiedTime && <span>{file.modifiedTime}</span>}
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}
