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
      <div className="flex flex-col items-center justify-center h-full text-[#999]">
        <Folder size={64} className="mb-4 opacity-30" />
        <p className="text-sm">暂无文件</p>
        <p className="text-xs mt-2">聊天记录中的文件会在此显示</p>
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
          className="w-full flex items-center gap-3 px-4 py-3 hover:bg-[#f5f5f5] transition-colors cursor-pointer border-b border-[#e5e5e5]"
        >
          <div className="w-10 h-10 flex items-center justify-center bg-[#f0f0f0] rounded-md flex-shrink-0">
            {file.type === 'folder' ? (
              <Folder size={24} className="text-[#666]" />
            ) : (
              <FileText size={24} className="text-[#666]" />
            )}
          </div>
          <div className="flex-1 min-w-0 text-left">
            <div className="text-sm font-medium text-[#333] truncate">{file.name}</div>
            <div className="text-xs text-[#999] mt-1 flex gap-2">
              {file.size && <span>{file.size}</span>}
              {file.modifiedTime && <span>{file.modifiedTime}</span>}
            </div>
          </div>
        </button>
      ))}
    </div>
  )
}
