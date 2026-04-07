type ConversationEmptyStateProps = {
  variant?: 'loading' | 'error' | 'empty' | 'welcome'
  showWelcome?: boolean
}

export function ConversationEmptyState({
  variant,
  showWelcome = false,
}: ConversationEmptyStateProps) {
  const resolvedVariant =
    variant ?? (showWelcome ? 'welcome' : 'empty')

  const titleByVariant = {
    loading: '正在准备桌面界面',
    error: '暂时无法加载桌面数据',
    empty: '选择一个会话开始查看',
    welcome: '准备开始首次使用',
  } as const

  const bodyByVariant = {
    loading: '正在读取模型设置与会话列表，请稍候。',
    error: '应用已就绪，但会话或设置数据读取失败。你可以稍后重试，设置与导入入口会在后续任务接入。',
    empty: 'App shell 已接入真实启动流程；会话列表、详情视图与欢迎弹层将在后续任务继续实现。',
    welcome: '当前还缺少模型设置或会话数据。Task 2 仅负责判定该状态并渲染最小壳层，欢迎引导将在后续任务接入。',
  } as const

  return (
    <section className="conversation-empty-state">
      <div className="conversation-empty-state__card">
        <span className="conversation-empty-state__eyebrow">聊天主视图</span>
        <h1>{titleByVariant[resolvedVariant]}</h1>
        <p>{bodyByVariant[resolvedVariant]}</p>
      </div>
    </section>
  )
}
