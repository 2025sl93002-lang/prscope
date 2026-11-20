// Dashboard. SPDX-License-Identifier: MIT
import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAsync } from '../hooks'
import { useActiveAnalysis } from '../active'
import { useToast } from '../components/Toast'
import {
  AttentionBadge, Card, CardHead, Empty, ErrorBox, Loading, Meter, StatTile, StatusBadge,
} from '../components/ui'

export default function Dashboard() {
  const navigate = useNavigate()
  const { notify } = useToast()
  const { setActiveId } = useActiveAnalysis()
  const [busy, setBusy] = useState(false)

  const repos = useAsync(() => api.listRepositories(), [])
  const analyses = useAsync(() => api.listAnalyses(), [])
  const latestId = analyses.data?.[0]?.id ?? null
  const readiness = useAsync(
    () => (latestId ? api.getReadiness(latestId) : Promise.resolve(null)),
    [latestId],
  )

  async function runDemo() {
    setBusy(true)
    try {
      const d = await api.setupDemo()
      setActiveId(d.analysis_id)
      notify('Demo analysis created — running the real engine on a sample repo.', 'success')
      navigate(`/analyses/${d.analysis_id}`)
    } catch (e) {
      notify(`Demo setup failed: ${(e as Error).message}`, 'error')
    } finally {
      setBusy(false)
    }
  }

  if (analyses.loading || repos.loading) return <Loading />
  if (analyses.error) return <ErrorBox message={analyses.error} />

  const list = analyses.data || []
  const highest = list.reduce<string>((acc, a) => {
    const order = ['low', 'moderate', 'high', 'critical']
    return order.indexOf(a.attention_level || 'low') > order.indexOf(acc) ? (a.attention_level || 'low') : acc
  }, 'low')

  return (
    <div className="stack" style={{ gap: 20 }}>
      <div className="row between">
        <div>
          <h1>Dashboard</h1>
          <p className="muted">Understand the impact. Know what to verify. Review with evidence.</p>
        </div>
        <div className="btn-group">
          <button className="btn" onClick={runDemo} disabled={busy}>
            {busy ? 'Setting up…' : '▶ Run demo'}
          </button>
          <Link className="btn primary" to="/analyses">+ New analysis</Link>
        </div>
      </div>

      {list.length === 0 ? (
        <Empty
          icon="◎"
          title="No analyses yet"
          hint={
            <>
              Add a local repository and compare two branches, or{' '}
              <a onClick={runDemo} className="clickable" style={{ color: 'var(--accent)' }}>run the one-click demo</a>{' '}
              to see PRScope analyze a real sample repo.
            </>
          }
        />
      ) : (
        <>
          <div className="grid grid-4">
            <StatTile label="Repositories" value={repos.data?.length ?? 0} />
            <StatTile label="Analyses" value={list.length} />
            <StatTile label="Highest attention" value={<AttentionBadge level={highest as never} />} />
            <StatTile
              label="Latest completeness"
              value={readiness.data ? `${readiness.data.completeness_percent}%` : '—'}
              delta={readiness.data ? `${readiness.data.completed_tasks}/${readiness.data.applicable_tasks} checks` : undefined}
            />
          </div>

          <div className="grid grid-2">
            <Card>
              <CardHead title="Recent analyses" sub="Most recent first" />
              <div className="scroll-x">
                <table className="table">
                  <thead>
                    <tr><th>#</th><th>Range</th><th>Status</th><th>Attention</th><th className="num">Files</th><th className="num">Lines</th></tr>
                  </thead>
                  <tbody>
                    {list.slice(0, 8).map((a) => (
                      <tr key={a.id} className="clickable" onClick={() => { setActiveId(a.id); navigate(`/analyses/${a.id}`) }}>
                        <td>{a.id}</td>
                        <td className="mono small nowrap">{a.base_ref} → {a.target_ref}</td>
                        <td><StatusBadge status={a.status} /></td>
                        <td><AttentionBadge level={a.attention_level} /></td>
                        <td className="num">{a.files_changed}</td>
                        <td className="num"><span className="pos">+{a.lines_added}</span> <span className="neg">-{a.lines_removed}</span></td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>

            <Card>
              <CardHead title="Latest review readiness" sub={latestId ? `Analysis #${latestId}` : undefined} />
              <div className="card-pad">
                {readiness.loading ? <Loading /> : readiness.data ? (
                  <div className="stack" style={{ gap: 14 }}>
                    <div>
                      <div className="row between small"><span className="muted">{readiness.data.completeness_label}</span>
                        <b>{readiness.data.completeness_percent}%</b></div>
                      <Meter percent={readiness.data.completeness_percent} tone="low" />
                    </div>
                    <div className="grid grid-3">
                      <StatTile label="Pending" value={readiness.data.pending_tasks} />
                      <StatTile label="Blocked" value={readiness.data.blocked_tasks} />
                      <StatTile label="Test gaps" value={readiness.data.test_gap_count} />
                    </div>
                    <div className="grid grid-2">
                      <StatTile label="With evidence" value={readiness.data.tasks_with_evidence} />
                      <StatTile label="Without evidence" value={readiness.data.tasks_without_evidence} />
                    </div>
                    <Link className="btn sm" to={`/analyses/${latestId}`}>Open analysis →</Link>
                  </div>
                ) : <Empty title="No readiness data" />}
              </div>
            </Card>
          </div>
        </>
      )}
    </div>
  )
}
