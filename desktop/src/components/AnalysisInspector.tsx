import type { PersonaProfileRead, SnapshotRead, TopicRead } from '../types/api'

export type AnalysisInspectorTab = 'topics' | 'profile' | 'snapshot'

type AnalysisInspectorProps = {
  open: boolean
  currentTab: AnalysisInspectorTab
  loadingByTab: Record<AnalysisInspectorTab, boolean>
  errorMessage: string | null
  topics: TopicRead[]
  profile: PersonaProfileRead[]
  snapshot: SnapshotRead | null
  onTabChange: (tab: AnalysisInspectorTab) => void
  onClose: () => void
}

export function AnalysisInspector({
  open,
  currentTab,
  loadingByTab,
  errorMessage,
  topics,
  profile,
  snapshot,
  onTabChange,
  onClose,
}: AnalysisInspectorProps) {
  if (!open) {
    return null
  }

  const isLoading = loadingByTab[currentTab]

  return (
    <div className="desktop-modal" role="dialog" aria-modal="true" aria-labelledby="analysis-dialog-title">
      <section className="desktop-modal__panel desktop-modal__panel--analysis">
        <header className="desktop-modal__header desktop-modal__header--split">
          <div>
            <p className="desktop-modal__eyebrow">分析</p>
            <h2 id="analysis-dialog-title" className="desktop-modal__title">
              会话分析结果
            </h2>
          </div>
          <button type="button" className="desktop-modal__button" onClick={onClose}>
            关闭
          </button>
        </header>

        <div className="desktop-modal__tabs" role="tablist" aria-label="分析标签">
          <button
            type="button"
            role="tab"
            aria-selected={currentTab === 'topics'}
            className={`desktop-modal__tab${currentTab === 'topics' ? ' desktop-modal__tab--active' : ''}`}
            onClick={() => onTabChange('topics')}
          >
            话题
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={currentTab === 'profile'}
            className={`desktop-modal__tab${currentTab === 'profile' ? ' desktop-modal__tab--active' : ''}`}
            onClick={() => onTabChange('profile')}
          >
            人格
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={currentTab === 'snapshot'}
            className={`desktop-modal__tab${currentTab === 'snapshot' ? ' desktop-modal__tab--active' : ''}`}
            onClick={() => onTabChange('snapshot')}
          >
            快照
          </button>
        </div>

        <div className="desktop-modal__content">
          {isLoading ? <p className="desktop-modal__state">正在加载分析数据…</p> : null}
          {errorMessage ? (
            <p className="desktop-modal__state desktop-modal__state--error" role="alert">
              {errorMessage}
            </p>
          ) : null}

          {!isLoading && !errorMessage ? (
            <>
              {currentTab === 'topics' ? (
                <section className="desktop-modal__section" role="tabpanel">
                  {topics.length === 0 ? (
                    <p className="desktop-modal__empty">暂无话题数据</p>
                  ) : (
                    <ul className="desktop-modal__list">
                      {topics.map((topic) => (
                        <li key={topic.id} className="desktop-modal__list-item">
                          <strong className="desktop-modal__list-title">{topic.topic_name}</strong>
                          <p className="desktop-modal__list-text">{topic.topic_summary}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              ) : null}

              {currentTab === 'profile' ? (
                <section className="desktop-modal__section" role="tabpanel">
                  {profile.length === 0 ? (
                    <p className="desktop-modal__empty">暂无人格数据</p>
                  ) : (
                    <ul className="desktop-modal__list">
                      {profile.map((item) => (
                        <li key={item.subject_role} className="desktop-modal__list-item">
                          <strong className="desktop-modal__list-title">{item.subject_role}</strong>
                          <p className="desktop-modal__list-text">{item.global_persona_summary}</p>
                        </li>
                      ))}
                    </ul>
                  )}
                </section>
              ) : null}

              {currentTab === 'snapshot' ? (
                <section className="desktop-modal__section" role="tabpanel">
                  {snapshot ? (
                    <div className="desktop-modal__snapshot">
                      <p className="desktop-modal__snapshot-summary">{snapshot.snapshot_summary}</p>
                      <dl className="desktop-modal__snapshot-details">
                        <div className="desktop-modal__snapshot-row">
                          <dt className="desktop-modal__snapshot-label">关系温度</dt>
                          <dd className="desktop-modal__snapshot-value">{snapshot.relationship_temperature}</dd>
                        </div>
                        <div className="desktop-modal__snapshot-row">
                          <dt className="desktop-modal__snapshot-label">关系阶段</dt>
                          <dd className="desktop-modal__snapshot-value">{snapshot.relationship_phase}</dd>
                        </div>
                        <div className="desktop-modal__snapshot-row">
                          <dt className="desktop-modal__snapshot-label">紧张程度</dt>
                          <dd className="desktop-modal__snapshot-value">{snapshot.tension_level}</dd>
                        </div>
                      </dl>
                    </div>
                  ) : (
                    <p className="desktop-modal__empty">暂无快照数据</p>
                  )}
                </section>
              ) : null}
            </>
          ) : null}
        </div>
      </section>
    </div>
  )
}
