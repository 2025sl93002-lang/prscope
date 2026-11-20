// Verification plan tab. SPDX-License-Identifier: MIT
import { useState } from 'react'
import type { VerificationTask } from '../../api'
import { api } from '../../api'
import { useAsync } from '../../hooks'
import { useToast } from '../../components/Toast'
import { Card, CardHead, Empty, ErrorBox, Loading, Meter, StatusBadge } from '../../components/ui'

const STATUSES: { value: VerificationTask['status']; label: string }[] = [
  { value: 'open', label: 'Open' },
  { value: 'completed', label: 'Completed' },
  { value: 'blocked', label: 'Blocked' },
  { value: 'not_applicable', label: 'N/A' },
]
const PRIORITY_TONE: Record<string, string> = { high: 'high', medium: 'moderate', low: 'neutral' }

export default function Verification({ analysisId }: { analysisId: number }) {
  const { notify } = useToast()
  const tasks = useAsync(() => api.listTasks(analysisId), [analysisId])
  const readiness = useAsync(() => api.getReadiness(analysisId), [analysisId])
  const [adding, setAdding] = useState(false)
  const [title, setTitle] = useState('')
  const [desc, setDesc] = useState('')

  async function setStatus(t: VerificationTask, status: VerificationTask['status']) {
    try {
      await api.updateTask(t.id, { status, actor: 'reviewer' })
      tasks.reload(); readiness.reload()
    } catch (e) { notify((e as Error).message, 'error') }
  }

  async function addTask() {
    if (!title.trim()) return
    try {
      await api.createTask(analysisId, { title, description: desc, verification_type: 'manual' })
      setTitle(''); setDesc(''); setAdding(false); tasks.reload(); readiness.reload()
      notify('Custom task added.', 'success')
    } catch (e) { notify((e as Error).message, 'error') }
  }

  async function del(t: VerificationTask) {
    if (!confirm('Delete this custom task?')) return
    try { await api.deleteTask(t.id); tasks.reload(); readiness.reload() }
    catch (e) { notify((e as Error).message, 'error') }
  }

  if (tasks.loading) return <Loading />
  if (tasks.error) return <ErrorBox message={tasks.error} />
  const list = tasks.data || []

  return (
    <div className="stack" style={{ gap: 16 }}>
      {readiness.data && (
        <Card>
          <div className="card-pad">
            <div className="row between small"><span className="muted">{readiness.data.completeness_label}</span>
              <b>{readiness.data.completeness_percent}%</b></div>
            <Meter percent={readiness.data.completeness_percent} tone="low" />
            <div className="row small mt" style={{ gap: 18 }}>
              <span className="muted">Completed <b>{readiness.data.completed_tasks}</b></span>
              <span className="muted">Pending <b>{readiness.data.pending_tasks}</b></span>
              <span className="muted">Blocked <b>{readiness.data.blocked_tasks}</b></span>
              <span className="muted">N/A <b>{readiness.data.not_applicable_tasks}</b></span>
              <span className="muted">With evidence <b>{readiness.data.tasks_with_evidence}</b></span>
            </div>
          </div>
        </Card>
      )}

      <div className="row between">
        <h2 style={{ margin: 0 }}>Verification tasks</h2>
        <button className="btn sm" onClick={() => setAdding((a) => !a)}>{adding ? 'Cancel' : '+ Add custom task'}</button>
      </div>

      {adding && (
        <Card><div className="card-pad">
          <label className="field"><span>Title</span><input value={title} onChange={(e) => setTitle(e.target.value)} /></label>
          <label className="field"><span>Description</span><textarea value={desc} onChange={(e) => setDesc(e.target.value)} /></label>
          <button className="btn primary" onClick={addTask} disabled={!title.trim()}>Add task</button>
        </div></Card>
      )}

      {list.length === 0 ? <Empty title="No verification tasks" /> : (
        <div className="stack" style={{ gap: 12 }}>
          {list.map((t) => (
            <Card key={t.id}>
              <CardHead
                title={<>{t.title} {!t.generated && <span className="badge neutral">custom</span>}</>}
                sub={t.reason}
                right={
                  <div className="row" style={{ gap: 8 }}>
                    <span className={`badge ${PRIORITY_TONE[t.priority]}`}>{t.priority}</span>
                    <StatusBadge status={t.status} />
                  </div>
                }
              />
              <div className="card-pad">
                {t.description && <p className="small">{t.description}</p>}
                {t.steps.length > 0 && (
                  <><div className="small muted">Suggested steps</div>
                    <ol className="small" style={{ margin: '4px 0 10px', paddingLeft: 18 }}>
                      {t.steps.map((s, i) => <li key={i}>{s}</li>)}</ol></>
                )}
                {t.evidence_requirements.length > 0 && (
                  <div className="small"><span className="muted">Evidence expected: </span>
                    {t.evidence_requirements.map((e) => <span key={e} className="badge neutral" style={{ marginRight: 4 }}>{e}</span>)}</div>
                )}
                {t.related_files.length > 0 && (
                  <div className="small mt"><span className="muted">Files: </span>
                    {t.related_files.map((f) => <span key={f} className="filelabel" style={{ marginRight: 8 }}>{f}</span>)}</div>
                )}
                <div className="divider" />
                <div className="row between">
                  <div className="btn-group">
                    {STATUSES.map((s) => (
                      <button key={s.value} className={`btn sm ${t.status === s.value ? 'primary' : ''}`}
                        onClick={() => setStatus(t, s.value)} disabled={t.status === s.value}>{s.label}</button>
                    ))}
                  </div>
                  {!t.generated && <button className="btn sm danger" onClick={() => del(t)}>Delete</button>}
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
