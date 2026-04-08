import type { BranchChatViewState } from '../lib/chatState'

type BranchViewProps = {
  originalMessage: string
  branchState: BranchChatViewState
  onBack: () => void
}

export function BranchView({ originalMessage, branchState, onBack }: BranchViewProps) {
  return (
    <section className="branch-view">
      <div className="branch-view__header">
        <div>
          <p className="branch-view__eyebrow">分支分析</p>
          <h3>消息改写影响</h3>
          <p className="branch-view__subtitle">分支推演 #{branchState.simulation.id}</p>
        </div>
        <button type="button" onClick={onBack}>
          返回原始历史
        </button>
      </div>

      <div className="branch-view__summary-grid">
        <article className="branch-view__card">
          <span className="branch-view__label">原消息</span>
          <p>{originalMessage || '（空消息）'}</p>
        </article>
        <article className="branch-view__card">
          <span className="branch-view__label">改写内容</span>
          <p>{branchState.replacementContent}</p>
        </article>
        <article className="branch-view__card">
          <span className="branch-view__label">首轮回复</span>
          <p>{branchState.simulation.first_reply_text ?? '暂无首轮回复'}</p>
        </article>
        <article className="branch-view__card">
          <span className="branch-view__label">影响摘要</span>
          <p>{branchState.simulation.impact_summary ?? '暂无摘要'}</p>
        </article>
      </div>

      <section className="branch-view__turns branch-view__turns--secondary">
        <h3>短链推演回合</h3>
        {branchState.simulation.simulated_turns.length === 0 ? (
          <p className="branch-view__empty">当前没有可展示的推演回合。</p>
        ) : (
          <ol>
            {branchState.simulation.simulated_turns.map((turn) => (
              <li key={`${turn.turn_index}-${turn.speaker_role}`} className="branch-view__turn">
                <div className="branch-view__turn-meta">
                  <strong>{turn.speaker_role === 'self' ? '我' : '对方'}</strong>
                  <span>回合 {turn.turn_index}</span>
                  <span>{turn.strategy_used}</span>
                </div>
                <p>{turn.message_text}</p>
              </li>
            ))}
          </ol>
        )}
      </section>
    </section>
  )
}
