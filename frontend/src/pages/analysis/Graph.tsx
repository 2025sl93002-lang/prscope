// Impact Graph tab — interactive file-level dependency graph. SPDX-License-Identifier: MIT
import { useMemo, useState } from 'react'
import {
  Background, Controls, MiniMap, ReactFlow, type Edge, type Node,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { GraphNode } from '../../api'
import { api } from '../../api'
import { useAsync } from '../../hooks'
import { Card, CardHead, Empty, ErrorBox, Loading } from '../../components/ui'

const IMPACT_COLOR: Record<string, string> = {
  changed: '#2f6df6', direct: '#d9730d', indirect: '#b8860b', unaffected: '#8a94a3',
}

function layout(nodes: GraphNode[]): Record<string, { x: number; y: number }> {
  // Column by distance (changed=0 … unaffected last); stack within a column.
  const columns = new Map<number, GraphNode[]>()
  const colFor = (n: GraphNode) => (n.distance < 0 ? 99 : n.distance)
  for (const n of nodes) {
    const c = colFor(n)
    if (!columns.has(c)) columns.set(c, [])
    columns.get(c)!.push(n)
  }
  const sortedCols = Array.from(columns.keys()).sort((a, b) => a - b)
  const pos: Record<string, { x: number; y: number }> = {}
  sortedCols.forEach((c, ci) => {
    const group = columns.get(c)!
    group.forEach((n, i) => { pos[n.id] = { x: ci * 260, y: i * 78 } })
  })
  return pos
}

export default function Graph({ analysisId }: { analysisId: number }) {
  const graph = useAsync(() => api.getGraph(analysisId), [analysisId])
  const [selected, setSelected] = useState<GraphNode | null>(null)
  const [categoryFilter, setCategoryFilter] = useState('')
  const [search, setSearch] = useState('')

  const { rfNodes, rfEdges, categories } = useMemo(() => {
    const g = graph.data
    if (!g) return { rfNodes: [] as Node[], rfEdges: [] as Edge[], categories: [] as string[] }
    const pos = layout(g.nodes)
    const cats = Array.from(new Set(g.nodes.map((n) => n.category).filter(Boolean))) as string[]

    const visible = g.nodes.filter((n) => {
      if (categoryFilter && n.category !== categoryFilter) return false
      return true
    })
    const visibleIds = new Set(visible.map((n) => n.id))

    const nodes: Node[] = visible.map((n) => {
      const matches = search && n.id.toLowerCase().includes(search.toLowerCase())
      return {
        id: n.id,
        position: pos[n.id] || { x: 0, y: 0 },
        data: { label: n.label },
        style: {
          background: IMPACT_COLOR[n.impact_type],
          color: '#fff',
          border: matches ? '3px solid #111' : n.impact_type === 'changed' ? '2px solid #fff' : '1px solid rgba(0,0,0,.2)',
          borderRadius: 7,
          fontSize: 11,
          width: 170,
          padding: 6,
          opacity: search && !matches ? 0.35 : 1,
        },
      }
    })
    const edges: Edge[] = g.edges
      .filter((e) => visibleIds.has(e.source) && visibleIds.has(e.target))
      .map((e, i) => ({
        id: `e${i}`, source: e.source, target: e.target, animated: false,
        style: { stroke: 'var(--border-strong)' },
      }))
    return { rfNodes: nodes, rfEdges: edges, categories: cats }
  }, [graph.data, categoryFilter, search])

  if (graph.loading) return <Loading />
  if (graph.error) return <ErrorBox message={graph.error} />
  const g = graph.data!
  if (g.nodes.length === 0) {
    return <Empty icon="◉" title="No dependency relationships detected"
      hint="No intra-repo Python or relative JS/TS imports were found among the changed/affected files." />
  }

  return (
    <div className="stack" style={{ gap: 12 }}>
      <Card>
        <CardHead
          title="File-level dependency graph"
          sub={g.note || undefined}
          right={
            <div className="row" style={{ gap: 8 }}>
              <input placeholder="Search file…" value={search} onChange={(e) => setSearch(e.target.value)} style={{ width: 160 }} />
              <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)} style={{ width: 150 }}>
                <option value="">All categories</option>
                {categories.map((c) => <option key={c} value={c}>{c}</option>)}
              </select>
            </div>
          }
        />
        <div className="card-pad">
          <div className="legend" style={{ marginBottom: 10 }}>
            {Object.entries(IMPACT_COLOR).map(([k, v]) => (
              <span key={k} className="item"><span className="swatch" style={{ background: v }} /> {k}</span>
            ))}
            <span className="faint">· drag to pan, scroll to zoom, click a node for details</span>
          </div>
          <div className="graph-wrap">
            <ReactFlow nodes={rfNodes} edges={rfEdges} fitView
              onNodeClick={(_, node) => setSelected(g.nodes.find((n) => n.id === node.id) || null)}
              proOptions={{ hideAttribution: true }} minZoom={0.2}>
              <Background />
              <Controls />
              <MiniMap pannable zoomable nodeColor={(n) => (n.style?.background as string) || '#999'} />
            </ReactFlow>
          </div>
        </div>
      </Card>

      {selected && (
        <Card>
          <CardHead title={<span className="filelabel">{selected.id}</span>}
            right={<button className="btn sm ghost" onClick={() => setSelected(null)}>Close</button>} />
          <div className="card-pad">
            <dl className="kv">
              <dt>Impact</dt><dd><span className={`badge ${selected.impact_type === 'changed' ? 'accent' : selected.impact_type === 'direct' ? 'high' : selected.impact_type === 'indirect' ? 'moderate' : 'neutral'}`}>{selected.impact_type}</span></dd>
              <dt>Distance from change</dt><dd>{selected.distance < 0 ? 'n/a' : `${selected.distance} hop(s)`}</dd>
              <dt>Category</dt><dd>{selected.category || '—'}</dd>
            </dl>
          </div>
        </Card>
      )}
    </div>
  )
}
