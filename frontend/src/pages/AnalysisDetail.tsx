// Analysis detail shell with tabs. SPDX-License-Identifier: MIT
import { useEffect } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { api } from '../api'
import { useAsync } from '../hooks'
import { useActiveAnalysis } from '../active'
import { Layout } from '../components/Layout'
import { AttentionBadge, ErrorBox, Loading, StatusBadge } from '../components/ui'
import Overview from './analysis/Overview'
import Changes from './analysis/Changes'
import Graph from './analysis/Graph'
import Impact from './analysis/Impact'
import Risk from './analysis/Risk'
import Verification from './analysis/Verification'
import Evidence from './analysis/Evidence'
import Checklist from './analysis/Checklist'
import Report from './analysis/Report'

const TABS = [
  { key: 'overview', label: 'Overview' },
  { key: 'changes', label: 'Changes' },
  { key: 'graph', label: 'Impact Graph' },
  { key: 'impact', label: 'Impact Explorer' },
  { key: 'risk', label: 'Risk Findings' },
  { key: 'verification', label: 'Verification' },
  { key: 'evidence', label: 'Evidence' },
  { key: 'checklist', label: 'Checklist' },
  { key: 'report', label: 'Report' },
]

export default function AnalysisDetail() {
  const { id, tab = 'overview' } = useParams()
  const analysisId = Number(id)
  const navigate = useNavigate()
  const { setActiveId } = useActiveAnalysis()

  useEffect(() => { if (analysisId) setActiveId(analysisId) }, [analysisId, setActiveId])

  const analysis = useAsync(() => api.getAnalysis(analysisId), [analysisId])

  const crumbs = (
    <>
      <Link to="/analyses">Analyses</Link> / <b>#{analysisId}</b>
      {analysis.data && <> &nbsp;<AttentionBadge level={analysis.data.attention_level} /></>}
    </>
  )

  function renderTab() {
    const a = analysis.data!
    switch (tab) {
      case 'changes': return <Changes analysisId={analysisId} />
      case 'graph': return <Graph analysisId={analysisId} />
      case 'impact': return <Impact analysisId={analysisId} />
      case 'risk': return <Risk analysisId={analysisId} />
      case 'verification': return <Verification analysisId={analysisId} />
      case 'evidence': return <Evidence analysisId={analysisId} />
      case 'checklist': return <Checklist analysisId={analysisId} />
      case 'report': return <Report analysisId={analysisId} />
      default: return <Overview analysisId={analysisId} analysis={a} />
    }
  }

  return (
    <Layout crumbs={crumbs}>
      {analysis.loading ? <Loading /> : analysis.error ? <ErrorBox message={analysis.error} /> : analysis.data && (
        <div className="stack" style={{ gap: 16 }}>
          <div className="row between">
            <div>
              <h1 style={{ marginBottom: 4 }}>Analysis #{analysisId}</h1>
              <div className="mono small muted">{analysis.data.base_ref} → {analysis.data.target_ref} &nbsp;·&nbsp; <StatusBadge status={analysis.data.status} /></div>
            </div>
          </div>

          {analysis.data.status === 'failed' && <ErrorBox message={analysis.data.error || 'Analysis failed.'} />}

          <div className="tabs">
            {TABS.map((t) => (
              <div key={t.key} className={`tab ${tab === t.key ? 'active' : ''}`}
                onClick={() => navigate(`/analyses/${analysisId}/${t.key}`)}>
                {t.label}
              </div>
            ))}
          </div>

          <div>{renderTab()}</div>
        </div>
      )}
    </Layout>
  )
}
