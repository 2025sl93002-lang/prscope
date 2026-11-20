// Risk findings tab. SPDX-License-Identifier: MIT
import { useState } from 'react'
import { api } from '../../api'
import { useAsync } from '../../hooks'
import { AttentionBadge, Card, CardHead, Empty, ErrorBox, Loading } from '../../components/ui'

export default function Risk({ analysisId }: { analysisId: number }) {
  const risk = useAsync(() => api.getRisk(analysisId), [analysisId])
  const gaps = useAsync(() => api.getTestGaps(analysisId), [analysisId])
  const [ai, setAi] = useState<{ source: string; text: string } | null>(null)
  const [aiBusy, setAiBusy] = useState(false)

  async function explain() {
    setAiBusy(true)
    try { const r = await api.aiExplain(analysisId, 'risk'); setAi({ source: r.source, text: r.text }) }
    finally { setAiBusy(false) }
  }

  if (risk.loading) return <Loading />
  if (risk.error) return <ErrorBox message={risk.error} />
  const r = risk.data!

  return (
    <div className="stack" style={{ gap: 16 }}>
      <Card>
        <CardHead
          title={<>Review attention: <AttentionBadge level={r.attention_level} /></>}
          sub={`Deterministic score: ${r.score}`}
          right={<button className="btn sm" onClick={explain} disabled={aiBusy}>{aiBusy ? 'Explaining…' : '✨ Explain'}</button>}
        />
        <div className="card-pad">
          <p className="small muted" style={{ margin: 0 }}>{r.methodology_note}</p>
          {ai && (
            <div className="card mt" style={{ background: 'var(--bg-sunken)' }}>
              <div className="card-pad">
                <div className="small">
                  <span className={`badge ${ai.source === 'ai' ? 'accent' : 'neutral'}`}>
                    {ai.source === 'ai' ? 'AI-generated' : 'Deterministic (AI unavailable)'}
                  </span>
                </div>
                <p className="small mt" style={{ whiteSpace: 'pre-wrap', margin: '8px 0 0' }}>{ai.text}</p>
              </div>
            </div>
          )}
        </div>
      </Card>

      {r.findings.length === 0 ? (
        <Empty icon="✓" title="No risk findings" hint="No deterministic rule flagged this change for extra review attention." />
      ) : (
        <div className="stack" style={{ gap: 12 }}>
          {r.findings.map((f, i) => (
            <Card key={i}>
              <CardHead
                title={f.title}
                right={<><AttentionBadge level={f.severity} /> &nbsp;<span className="badge neutral">+{f.score_contribution}</span></>}
              />
              <div className="card-pad">
                <dl className="kv">
                  <dt>Explanation</dt><dd>{f.explanation}</dd>
                  <dt>Evidence</dt><dd>{f.evidence}</dd>
                  <dt>Suggested action</dt><dd>{f.suggested_action}</dd>
                  <dt>Rule</dt><dd><code>{f.rule}</code></dd>
                  {f.related_files.length > 0 && (
                    <><dt>Files</dt><dd>{f.related_files.map((x) => <div key={x} className="filelabel">{x}</div>)}</dd></>
                  )}
                </dl>
              </div>
            </Card>
          ))}
        </div>
      )}

      <Card>
        <CardHead title="Potential test gaps" sub="Inferred from imports and naming — potential gaps, not confirmed failures." />
        {gaps.loading ? <Loading /> : (gaps.data?.length ?? 0) === 0 ? (
          <div className="card-pad"><span className="small muted">No potential test gaps detected.</span></div>
        ) : (
          <div className="scroll-x">
            <table className="table">
              <thead><tr><th>Changed file</th><th>Potential gap</th><th>Detection</th><th>Severity</th></tr></thead>
              <tbody>
                {gaps.data!.map((g, i) => (
                  <tr key={i}>
                    <td className="filelabel">{g.changed_file}</td>
                    <td className="small">{g.missing_coverage}
                      {g.recommended_tests.length > 0 && <div className="faint small mt">→ {g.recommended_tests.join('; ')}</div>}</td>
                    <td className="small muted">{g.detection_method}</td>
                    <td><AttentionBadge level={g.severity} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  )
}
