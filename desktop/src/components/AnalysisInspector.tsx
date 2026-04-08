import type { PersonaProfileRead, SnapshotRead, TopicRead } from '../types/api'

type AnalysisInspectorProps = {
  open: boolean
  loading: boolean
  errorMessage: string | null
  topics: TopicRead[]
  profile: PersonaProfileRead[]
  snapshot: SnapshotRead | null
  onClose: () => void
}

export function AnalysisInspector({
  open,
  loading,
  errorMessage,
  topics,
  profile,
  snapshot,
  onClose,
}: AnalysisInspectorProps) {
  if (!open) {
    return null
  }

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

      {loading ? <p className="analysis-inspector__state">正在加载分析视角…</p> : null}
      {errorMessage ? (
        <p className="analysis-inspector__state analysis-inspector__state--error" role="alert">
          {errorMessage}
        </p>
      ) : null}

      {!loading && !errorMessage ? (
        <>
          <section className="analysis-inspector__section">
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

          <section className="analysis-inspector__section">
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

          <section className="analysis-inspector__section">
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
        </>
      ) : null}
    </aside>
  )
}
