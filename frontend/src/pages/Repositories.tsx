// Repositories page. SPDX-License-Identifier: MIT
import { useState } from 'react'
import { api } from '../api'
import { useAsync } from '../hooks'
import { useToast } from '../components/Toast'
import { Card, CardHead, Empty, ErrorBox, Loading } from '../components/ui'

export default function Repositories() {
  const { notify } = useToast()
  const repos = useAsync(() => api.listRepositories(), [])
  const [path, setPath] = useState('')
  const [checking, setChecking] = useState(false)
  const [preview, setPreview] = useState<{ name: string; default_branch: string | null } | null>(null)
  const [expanded, setExpanded] = useState<number | null>(null)

  async function validate() {
    setChecking(true); setPreview(null)
    try {
      const r = await api.validateRepository(path)
      setPreview({ name: r.name, default_branch: r.default_branch })
      notify(`Valid git repository: ${r.name}`, 'success')
    } catch (e) {
      notify(`Invalid: ${(e as Error).message}`, 'error')
    } finally { setChecking(false) }
  }

  async function add() {
    try {
      await api.createRepository(path)
      setPath(''); setPreview(null)
      repos.reload()
      notify('Repository added.', 'success')
    } catch (e) {
      notify(`Could not add: ${(e as Error).message}`, 'error')
    }
  }

  async function remove(id: number) {
    if (!confirm('Remove this repository and all its analyses? This cannot be undone.')) return
    try {
      await api.deleteRepository(id)
      repos.reload()
      notify('Repository removed.', 'info')
    } catch (e) {
      notify((e as Error).message, 'error')
    }
  }

  return (
    <div className="stack" style={{ gap: 20 }}>
      <div>
        <h1>Repositories</h1>
        <p className="muted">Add a local git repository by path. PRScope only reads it — it never executes repository code or uploads source.</p>
      </div>

      <Card>
        <CardHead title="Add a local repository" />
        <div className="card-pad">
          <label className="field">
            <span>Absolute path to a local git repository</span>
            <input value={path} onChange={(e) => { setPath(e.target.value); setPreview(null) }}
              placeholder="/Users/you/projects/my-repo" />
          </label>
          <div className="btn-group">
            <button className="btn" onClick={validate} disabled={!path || checking}>
              {checking ? 'Validating…' : 'Validate'}
            </button>
            <button className="btn primary" onClick={add} disabled={!path}>Add repository</button>
          </div>
          {preview && (
            <div className="small mt muted">
              Detected <b>{preview.name}</b>{preview.default_branch ? ` · default branch ${preview.default_branch}` : ''}
            </div>
          )}
        </div>
      </Card>

      <Card>
        <CardHead title="Your repositories" sub={`${repos.data?.length ?? 0} registered`} />
        {repos.loading ? <Loading /> : repos.error ? <ErrorBox message={repos.error} /> :
          (repos.data?.length ?? 0) === 0 ? (
            <div className="card-pad"><Empty icon="⌥" title="No repositories yet" hint="Add one above to start analyzing." /></div>
          ) : (
            <div className="scroll-x">
              <table className="table">
                <thead><tr><th>Name</th><th>Path</th><th>Default</th><th></th></tr></thead>
                <tbody>
                  {repos.data!.map((r) => (
                    <RepoRow key={r.id} id={r.id} name={r.name} path={r.path}
                      defaultBranch={r.default_branch} expanded={expanded === r.id}
                      onToggle={() => setExpanded(expanded === r.id ? null : r.id)}
                      onRemove={() => remove(r.id)} />
                  ))}
                </tbody>
              </table>
            </div>
          )}
      </Card>
    </div>
  )
}

function RepoRow({ id, name, path, defaultBranch, expanded, onToggle, onRemove }: {
  id: number; name: string; path: string; defaultBranch: string | null
  expanded: boolean; onToggle: () => void; onRemove: () => void
}) {
  const detail = useAsync(() => (expanded ? api.getRepository(id) : Promise.resolve(null)), [expanded])
  return (
    <>
      <tr>
        <td><b>{name}</b></td>
        <td className="mono small">{path}</td>
        <td className="small">{defaultBranch || '—'}</td>
        <td className="nowrap">
          <div className="btn-group">
            <button className="btn sm ghost" onClick={onToggle}>{expanded ? 'Hide' : 'Details'}</button>
            <button className="btn sm danger" onClick={onRemove}>Remove</button>
          </div>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={4}>
            {detail.loading ? <Loading /> : detail.error ? <ErrorBox message={detail.error} /> : detail.data && (
              <div className="grid grid-2" style={{ padding: '6px 2px' }}>
                <div>
                  <div className="small muted">Branches &amp; tags ({detail.data.branches.length})</div>
                  <div className="tag-list mt">
                    {detail.data.branches.slice(0, 20).map((b) => <span key={b} className="badge neutral mono">{b}</span>)}
                  </div>
                </div>
                <div>
                  <div className="small muted">Recent commits</div>
                  <ul className="small mt" style={{ margin: 0, paddingLeft: 16 }}>
                    {detail.data.recent_commits.slice(0, 5).map((c) => (
                      <li key={c.hash}><code>{c.hash}</code> {c.subject} <span className="faint">· {c.date}</span></li>
                    ))}
                  </ul>
                </div>
              </div>
            )}
          </td>
        </tr>
      )}
    </>
  )
}
