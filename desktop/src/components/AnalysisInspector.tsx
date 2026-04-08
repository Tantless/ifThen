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
    <aside className="analysis-inspector">
      <div className="analysis-inspector__header">
        <div>
          <p className="analysis-inspector__eyebrow">分析侧栏</p>
          <h3>topics / profile / snapshot</h3>
        </div>
        <button type="button" onClick={onClose}>
          收起
        </button>
      </div>

      <div className="analysis-inspector__tabs" role="tablist" aria-label="分析标签">
        <button
          type="button"
          role="tab"
          aria-selected={currentTab === 'topics'}
          className={`analysis-inspector__tab${currentTab === 'topics' ? ' analysis-inspector__tab--active' : ''}`}
          onClick={() => onTabChange('topics')}
        >
          Topics
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={currentTab === 'profile'}
          className={`analysis-inspector__tab${currentTab === 'profile' ? ' analysis-inspector__tab--active' : ''}`}
          onClick={() => onTabChange('profile')}
        >
          Persona
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={currentTab === 'snapshot'}
          className={`analysis-inspector__tab${currentTab === 'snapshot' ? ' analysis-inspector__tab--active' : ''}`}
          onClick={() => onTabChange('snapshot')}
        >
          Snapshot
        </button>
      </div>

      <section className="analysis-inspector__panel">
        {isLoading ? <p className="analysis-inspector__state">正在加载分析视角…</p> : null}
        {errorMessage ? (
          <p className="analysis-inspector__state analysis-inspector__state--error" role="alert">
            {errorMessage}
          </p>
        ) : null}

        {!isLoading && !errorMessage ? (
          <>
            {currentTab === 'topics' ? (
              <section className="analysis-inspector__section" role="tabpanel">
                <h4>Topics</h4>
                {topics.length === 0 ? (
                  <p className="analysis-inspector__empty">暂无 topics 数据。</p>
                ) : (
                  <ul>
                    {topics.map((topic) => (
                      <li key={topic.id}>
                        <strong>{topic.topic_name}</strong>
                        <p>{topic.topic_summary}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            ) : null}

            {currentTab === 'profile' ? (
              <section className="analysis-inspector__section" role="tabpanel">
                <h4>Persona</h4>
                {profile.length === 0 ? (
                  <p className="analysis-inspector__empty">暂无 persona 数据。</p>
                ) : (
                  <ul>
                    {profile.map((item) => (
                      <li key={item.subject_role}>
                        <strong>{item.subject_role}</strong>
                        <p>{item.global_persona_summary}</p>
                      </li>
                    ))}
                  </ul>
                )}
              </section>
            ) : null}

            {currentTab === 'snapshot' ? (
              <section className="analysis-inspector__section" role="tabpanel">
                <h4>Snapshot</h4>
                {snapshot ? (
                  <div className="analysis-inspector__snapshot">
                    <p>{snapshot.snapshot_summary}</p>
                    <dl>
                      <div>
                        <dt>关系温度</dt>
                        <dd>{snapshot.relationship_temperature}</dd>
                      </div>
                      <div>
                        <dt>关系阶段</dt>
                        <dd>{snapshot.relationship_phase}</dd>
                      </div>
                      <div>
                        <dt>紧张程度</dt>
                        <dd>{snapshot.tension_level}</dd>
                      </div>
                    </dl>
                  </div>
                ) : (
                  <p className="analysis-inspector__empty">暂无 snapshot 数据。</p>
                )}
              </section>
            ) : null}
          </>
        ) : null}
      </section>
    </aside>
  )
}
