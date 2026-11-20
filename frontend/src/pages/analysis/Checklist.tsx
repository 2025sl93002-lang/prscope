// Review checklist tab. SPDX-License-Identifier: MIT
import { useState } from 'react'
import { api } from '../../api'
import { useAsync } from '../../hooks'
import { useToast } from '../../components/Toast'
import { Card, CardHead, Empty, ErrorBox, Loading } from '../../components/ui'

export default function Checklist({ analysisId }: { analysisId: number }) {
  const { notify } = useToast()
  const items = useAsync(() => api.listChecklist(analysisId), [analysisId])
  const [text, setText] = useState('')

  async function toggle(id: number, checked: boolean) {
    try { await api.updateChecklistItem(id, { checked }); items.reload() }
    catch (e) { notify((e as Error).message, 'error') }
  }
  async function add() {
    if (!text.trim()) return
    try { await api.addChecklistItem(analysisId, text.trim()); setText(''); items.reload() }
    catch (e) { notify((e as Error).message, 'error') }
  }
  async function del(id: number) {
    try { await api.deleteChecklistItem(id); items.reload() }
    catch (e) { notify((e as Error).message, 'error') }
  }

  function exportMd() {
    const list = items.data || []
    const md = '# Review checklist\n\n' + list.map((i) => `- [${i.checked ? 'x' : ' '}] ${i.text}`).join('\n') + '\n'
    const blob = new Blob([md], { type: 'text/markdown' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = `prscope-checklist-${analysisId}.md`; a.click()
    URL.revokeObjectURL(url)
  }

  if (items.loading) return <Loading />
  if (items.error) return <ErrorBox message={items.error} />
  const list = items.data || []
  const done = list.filter((i) => i.checked).length

  return (
    <Card>
      <CardHead title="Review checklist" sub={`${done}/${list.length} checked · generated from findings, verification tasks, and test gaps`}
        right={<button className="btn sm" onClick={exportMd} disabled={!list.length}>⤓ Export</button>} />
      <div className="card-pad">
        {list.length === 0 ? <Empty icon="☑" title="No checklist items" /> : (
          <div>
            {list.map((i) => (
              <div key={i.id} className="checkline">
                <input type="checkbox" checked={i.checked} onChange={(e) => toggle(i.id, e.target.checked)} />
                <div style={{ flex: 1 }}>
                  <span style={{ textDecoration: i.checked ? 'line-through' : 'none', color: i.checked ? 'var(--fg-muted)' : 'var(--fg)' }}>{i.text}</span>
                  {i.source === 'custom' && <span className="badge neutral" style={{ marginLeft: 8 }}>custom</span>}
                </div>
                <button className="btn sm ghost" onClick={() => del(i.id)}>✕</button>
              </div>
            ))}
          </div>
        )}
        <div className="inline-form mt">
          <input value={text} onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && add()} placeholder="Add a custom checklist item…" />
          <button className="btn primary" onClick={add} disabled={!text.trim()}>Add</button>
        </div>
      </div>
    </Card>
  )
}
