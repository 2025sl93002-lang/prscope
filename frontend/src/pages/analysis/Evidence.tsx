// Evidence ledger tab. SPDX-License-Identifier: MIT
import { useEffect, useState } from 'react'
import type { EvidenceType, VerificationTask } from '../../api'
import { api } from '../../api'
import { useAsync } from '../../hooks'
import { useToast } from '../../components/Toast'
import { Card, CardHead, Empty, ErrorBox, Loading, StatusBadge } from '../../components/ui'

const EVIDENCE_TYPES: EvidenceType[] = [
  'test_result', 'ci', 'manual', 'build', 'api', 'security_scan', 'screenshot', 'report', 'reviewer_note', 'doc',
]

export default function Evidence({ analysisId }: { analysisId: number }) {
  const { notify } = useToast()
  const tasks = useAsync(() => api.listTasks(analysisId), [analysisId])
  const [taskId, setTaskId] = useState<number | null>(null)

  useEffect(() => {
    if (taskId == null && tasks.data?.length) setTaskId(tasks.data[0].id)
  }, [tasks.data, taskId])

  if (tasks.loading) return <Loading />
  if (tasks.error) return <ErrorBox message={tasks.error} />
  if (!tasks.data?.length) return <Empty title="No tasks to attach evidence to" />

  const task = tasks.data.find((t) => t.id === taskId) || tasks.data[0]

  return (
    <div className="grid" style={{ gridTemplateColumns: '280px 1fr', gap: 16 }}>
      <Card>
        <CardHead title="Tasks" sub="Select to view evidence" />
        <div className="stack" style={{ gap: 0 }}>
          {tasks.data.map((t) => (
            <div key={t.id} className={`nav-item ${t.id === task.id ? 'active' : ''}`}
              style={{ color: 'var(--fg)', borderRadius: 0, borderBottom: '1px solid var(--border)' }}
              onClick={() => setTaskId(t.id)} role="button" tabIndex={0}>
              <div style={{ flex: 1 }}>
                <div className="small"><b>{t.title}</b></div>
                <div className="faint small"><StatusBadge status={t.status} /></div>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <TaskEvidence key={task.id} task={task} onChange={() => notify('Evidence ledger updated.', 'success')} />
    </div>
  )
}

function TaskEvidence({ task, onChange }: { task: VerificationTask; onChange: () => void }) {
  const { notify } = useToast()
  const evidence = useAsync(() => api.listEvidence(task.id), [task.id])
  const history = useAsync(() => api.taskHistory(task.id), [task.id])

  const [type, setType] = useState<EvidenceType>('test_result')
  const [note, setNote] = useState('')
  const [command, setCommand] = useState('')
  const [result, setResult] = useState('')
  const [link, setLink] = useState('')
  const [by, setBy] = useState('')

  async function add() {
    try {
      await api.addEvidence(task.id, {
        evidence_type: type, note: note || null, command: command || null,
        result: result || null, link: link || null, performed_by: by || null,
      } as never)
      setNote(''); setCommand(''); setResult(''); setLink('')
      evidence.reload(); onChange()
    } catch (e) { notify((e as Error).message, 'error') }
  }

  async function del(id: number) {
    try { await api.deleteEvidence(id); evidence.reload(); onChange() }
    catch (e) { notify((e as Error).message, 'error') }
  }

  return (
    <div className="stack" style={{ gap: 16 }}>
      <Card>
        <CardHead title={task.title} right={<StatusBadge status={task.status} />}
          sub={`${task.evidence_requirements.length ? 'Expected: ' + task.evidence_requirements.join(', ') : 'No specific evidence requirements'}`} />
        <div className="card-pad">
          {evidence.loading ? <Loading /> : (evidence.data?.length ?? 0) === 0 ? (
            <Empty icon="▤" title="No evidence recorded yet" hint="Add a test result, CI link, or reviewer note below." />
          ) : (
            <div className="stack" style={{ gap: 10 }}>
              {evidence.data!.map((e) => (
                <div key={e.id} className="card" style={{ background: 'var(--bg-sunken)' }}>
                  <div className="card-pad" style={{ padding: 12 }}>
                    <div className="row between">
                      <span className="badge accent">{e.evidence_type}</span>
                      <span className="faint small">{e.created_at?.replace('T', ' ').slice(0, 19)} · {e.performed_by || 'unknown'}
                        &nbsp;<button className="btn sm ghost" onClick={() => del(e.id)}>✕</button></span>
                    </div>
                    {e.note && <p className="small mt" style={{ margin: '6px 0 0' }}>{e.note}</p>}
                    {e.command && <pre className="small mono" style={{ margin: '6px 0 0' }}>$ {e.command}</pre>}
                    {e.result && <pre className="small mono" style={{ margin: '4px 0 0', color: 'var(--fg-muted)' }}>{e.result}</pre>}
                    {e.link && <div className="small mt"><a href={e.link} target="_blank" rel="noreferrer">{e.link}</a></div>}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </Card>

      <Card>
        <CardHead title="Record evidence" />
        <div className="card-pad">
          <div className="grid grid-2">
            <label className="field"><span>Type</span>
              <select value={type} onChange={(e) => setType(e.target.value as EvidenceType)}>
                {EVIDENCE_TYPES.map((t) => <option key={t} value={t}>{t}</option>)}
              </select></label>
            <label className="field"><span>Performed by</span><input value={by} onChange={(e) => setBy(e.target.value)} placeholder="your name" /></label>
          </div>
          <label className="field"><span>Note</span><textarea value={note} onChange={(e) => setNote(e.target.value)} placeholder="What was verified and the outcome" /></label>
          <div className="grid grid-2">
            <label className="field"><span>Command (optional)</span><input value={command} onChange={(e) => setCommand(e.target.value)} placeholder="pytest tests/…" /></label>
            <label className="field"><span>Result (optional)</span><input value={result} onChange={(e) => setResult(e.target.value)} placeholder="12 passed" /></label>
          </div>
          <label className="field"><span>Link (optional)</span><input value={link} onChange={(e) => setLink(e.target.value)} placeholder="https://ci/…" /></label>
          <button className="btn primary" onClick={add}>Add evidence</button>
        </div>
      </Card>

      <Card>
        <CardHead title="Status history" sub="Audit trail of verification status changes" />
        <div className="card-pad">
          {history.loading ? <Loading /> : (history.data?.length ?? 0) === 0 ? (
            <span className="small muted">No status changes yet.</span>
          ) : (
            <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
              {history.data!.map((h) => (
                <li key={h.id}>
                  <b>{h.from_status || '—'} → {h.to_status}</b>
                  <span className="faint"> · {h.created_at?.replace('T', ' ').slice(0, 19)}{h.actor ? ` · ${h.actor}` : ''}</span>
                  {h.note && <> — {h.note}</>}
                </li>
              ))}
            </ul>
          )}
        </div>
      </Card>
    </div>
  )
}
