// Changes tab — classified changed files. SPDX-License-Identifier: MIT
import { useState } from 'react'
import { api } from '../../api'
import { useAsync } from '../../hooks'
import { CategoryBadge, Card, CardHead, Empty, ErrorBox, Loading } from '../../components/ui'

const CHANGE_ICON: Record<string, string> = { added: '＋', modified: '∼', deleted: '－', renamed: '→' }

export default function Changes({ analysisId }: { analysisId: number }) {
  const changes = useAsync(() => api.getChanges(analysisId), [analysisId])
  const [filter, setFilter] = useState('')

  if (changes.loading) return <Loading />
  if (changes.error) return <ErrorBox message={changes.error} />
  const all = changes.data || []
  if (all.length === 0) return <Empty title="No changed files" hint="The two refs are identical." />

  const categories = Array.from(new Set(all.map((c) => c.category))).sort()
  const rows = filter ? all.filter((c) => c.category === filter) : all

  return (
    <Card>
      <CardHead
        title="Changed files"
        sub={`${all.length} files · click a category to filter`}
        right={
          <div className="tag-list">
            <span className={`badge ${filter === '' ? 'accent' : 'neutral'} clickable`} onClick={() => setFilter('')}>All ({all.length})</span>
            {categories.map((cat) => (
              <span key={cat} className={`badge ${filter === cat ? 'accent' : 'cat'} clickable`} onClick={() => setFilter(cat)}>
                {cat} ({all.filter((c) => c.category === cat).length})
              </span>
            ))}
          </div>
        }
      />
      <div className="scroll-x">
        <table className="table">
          <thead><tr><th></th><th>File</th><th>Category</th><th>Why (rule)</th><th className="num">+/−</th></tr></thead>
          <tbody>
            {rows.map((c) => (
              <tr key={c.path}>
                <td title={c.change_type} className="nowrap">{CHANGE_ICON[c.change_type]} <span className="small faint">{c.change_type}</span></td>
                <td className="filelabel">{c.path}{c.old_path && <span className="faint"> (was {c.old_path})</span>}</td>
                <td><CategoryBadge category={c.category} /></td>
                <td className="small muted">{c.classification_reason}{c.matched_rule && c.matched_rule !== 'none' && <span className="faint"> · <code>{c.matched_rule}</code></span>}</td>
                <td className="num nowrap"><span className="pos">+{c.lines_added}</span> <span className="neg">-{c.lines_removed}</span></td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  )
}
