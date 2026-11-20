// Analyses list + create. SPDX-License-Identifier: MIT
import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { api } from '../api'
import { useAsync } from '../hooks'
import { useActiveAnalysis } from '../active'
import { useToast } from '../components/Toast'
import { AttentionBadge, Card, CardHead, Empty, ErrorBox, Loading, StatusBadge } from '../components/ui'

export default function Analyses() {
  const navigate = useNavigate()
  const { notify } = useToast()
  const { setActiveId } = useActiveAnalysis()

  const repos = useAsync(() => api.listRepositories(), [])
  const analyses = useAsync(() => api.listAnalyses(), [])

  const [repoId, setRepoId] = useState<number | null>(null)
  const [base, setBase] = useState('')
  const [target, setTarget] = useState('')
  const [running, setRunning] = useState(false)

  const repoDetail = useAsync(
    () => (repoId ? api.getRepository(repoId) : Promise.resolve(null)),
    [repoId],
  )

  function onPickRepo(id: number) {
    setRepoId(id)
    setBase(''); setTarget('')
  }

  // Pre-fill default branch as base once detail loads.
  const branches = repoDetail.data?.branches ?? []
  const defaultBranch = repoDetail.data?.default_branch

  async function run() {
    if (!repoId || !base || !target) return
    setRunning(true)
    try {
      const a = await api.createAnalysis(repoId, base, target)
      setActiveId(a.id)
      notify(`Analysis #${a.id} complete.`, 'success')
      navigate(`/analyses/${a.id}`)
    } catch (e) {
      notify(`Analysis failed: ${(e as Error).message}`, 'error')
    } finally { setRunning(false) }
  }

  async function remove(id: number) {
    if (!confirm('Delete this analysis and all its tasks, evidence, and findings?')) return
    try { await api.deleteAnalysis(id); analyses.reload(); notify('Analysis deleted.', 'info') }
    catch (e) { notify((e as Error).message, 'error') }
  }

  return (
    <div className="stack" style={{ gap: 20 }}>
      <div><h1>Analyses</h1><p className="muted">Compare two branches or commits and run the deterministic analysis engine.</p></div>

      <Card>
        <CardHead title="New analysis" />
        <div className="card-pad">
          {(repos.data?.length ?? 0) === 0 ? (
            <Empty icon="⌥" title="Add a repository first" hint="Go to Repositories to register a local git repo." />
          ) : (
            <div className="grid grid-4" style={{ alignItems: 'end' }}>
              <label className="field" style={{ margin: 0 }}>
                <span>Repository</span>
                <select value={repoId ?? ''} onChange={(e) => onPickRepo(Number(e.target.value))}>
                  <option value="" disabled>Select…</option>
                  {repos.data!.map((r) => <option key={r.id} value={r.id}>{r.name}</option>)}
                </select>
              </label>
              <label className="field" style={{ margin: 0 }}>
                <span>Base ref {defaultBranch && <span className="faint">(default: {defaultBranch})</span>}</span>
                <input list="branchlist" value={base} onChange={(e) => setBase(e.target.value)}
                  placeholder={defaultBranch || 'main'} disabled={!repoId} />
              </label>
              <label className="field" style={{ margin: 0 }}>
                <span>Target ref</span>
                <input list="branchlist" value={target} onChange={(e) => setTarget(e.target.value)}
                  placeholder="feature/…" disabled={!repoId} />
              </label>
              <button className="btn primary" onClick={run} disabled={!repoId || !base || !target || running}>
                {running ? 'Analyzing…' : 'Run analysis'}
              </button>
              <datalist id="branchlist">
                {branches.map((b) => <option key={b} value={b} />)}
              </datalist>
            </div>
          )}
          {repoDetail.loading && <div className="small muted mt"><Loading label="Loading branches…" /></div>}
        </div>
      </Card>

      <Card>
        <CardHead title="All analyses" sub={`${analyses.data?.length ?? 0} total`} />
        {analyses.loading ? <Loading /> : analyses.error ? <ErrorBox message={analyses.error} /> :
          (analyses.data?.length ?? 0) === 0 ? (
            <div className="card-pad"><Empty icon="≋" title="No analyses yet" /></div>
          ) : (
            <div className="scroll-x">
              <table className="table">
                <thead><tr><th>#</th><th>Range</th><th>Status</th><th>Attention</th>
                  <th className="num">Files</th><th className="num">Score</th><th>Created</th><th></th></tr></thead>
                <tbody>
                  {analyses.data!.map((a) => (
                    <tr key={a.id}>
                      <td className="clickable" onClick={() => { setActiveId(a.id); navigate(`/analyses/${a.id}`) }}><b>{a.id}</b></td>
                      <td className="mono small nowrap clickable" onClick={() => { setActiveId(a.id); navigate(`/analyses/${a.id}`) }}>{a.base_ref} → {a.target_ref}</td>
                      <td><StatusBadge status={a.status} /></td>
                      <td><AttentionBadge level={a.attention_level} /></td>
                      <td className="num">{a.files_changed}</td>
                      <td className="num">{a.risk_score}</td>
                      <td className="small faint nowrap">{a.created_at?.slice(0, 16).replace('T', ' ')}</td>
                      <td><button className="btn sm danger" onClick={() => remove(a.id)}>Delete</button></td>
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
