// Impact Explorer tab — per-file dependency & impact view. SPDX-License-Identifier: MIT
import { useEffect, useState } from 'react'
import { api } from '../../api'
import { useAsync } from '../../hooks'
import { CategoryBadge, Card, CardHead, Empty, ErrorBox, Loading } from '../../components/ui'

function FileList({ title, files, empty }: { title: string; files: string[]; empty: string }) {
  return (
    <Card>
      <CardHead title={title} sub={`${files.length}`} />
      <div className="card-pad">
        {files.length === 0 ? <span className="small muted">{empty}</span> : (
          <div className="stack" style={{ gap: 4 }}>
            {files.map((f) => <div key={f} className="filelabel">{f}</div>)}
          </div>
        )}
      </div>
    </Card>
  )
}

export default function Impact({ analysisId }: { analysisId: number }) {
  const changes = useAsync(() => api.getChanges(analysisId), [analysisId])
  const [path, setPath] = useState<string>('')

  useEffect(() => {
    if (!path && changes.data && changes.data.length) {
      const src = changes.data.find((c) => c.category === 'source') || changes.data[0]
      setPath(src.path)
    }
  }, [changes.data, path])

  const impact = useAsync(() => (path ? api.getFileImpact(analysisId, path) : Promise.resolve(null)), [analysisId, path])

  if (changes.loading) return <Loading />
  if (changes.error) return <ErrorBox message={changes.error} />
  if (!changes.data?.length) return <Empty title="No changed files to explore" />

  return (
    <div className="stack" style={{ gap: 16 }}>
      <Card>
        <CardHead title="Select a changed file" sub="See what it depends on, what depends on it, and the potential downstream impact." />
        <div className="card-pad">
          <select value={path} onChange={(e) => setPath(e.target.value)}>
            {changes.data.map((c) => <option key={c.path} value={c.path}>{c.path} ({c.category})</option>)}
          </select>
        </div>
      </Card>

      {impact.loading ? <Loading /> : impact.error ? <ErrorBox message={impact.error} /> : impact.data && (
        <>
          <div className="row">
            <span className="filelabel"><b>{impact.data.path}</b></span>
            {impact.data.category && <CategoryBadge category={impact.data.category} />}
          </div>

          <div className="grid grid-2">
            <FileList title="Direct dependencies (this file imports)" files={impact.data.direct_dependencies}
              empty="No intra-repo imports detected from this file." />
            <FileList title="Reverse dependencies (files importing this)" files={impact.data.reverse_dependencies}
              empty="No files import this one (by static analysis)." />
            <FileList title="Potential downstream impact (transitive)" files={impact.data.downstream_impact}
              empty="No transitive dependents detected." />
            <FileList title="Related tests" files={impact.data.related_tests}
              empty="No related tests detected by import/name." />
          </div>

          <Card>
            <CardHead title="Relationship explanations"
              sub="Static, file-level analysis — approximates but does not guarantee runtime impact." />
            <div className="card-pad">
              {impact.data.path_explanations.length === 0 ? (
                <span className="small muted">No relationships detected for this file.</span>
              ) : (
                <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
                  {impact.data.path_explanations.map((e, i) => <li key={i}>{e}</li>)}
                </ul>
              )}
            </div>
          </Card>
        </>
      )}
    </div>
  )
}
