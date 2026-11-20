// Overview tab. SPDX-License-Identifier: MIT
import { Link } from 'react-router-dom'
import type { Analysis } from '../../api'
import { api } from '../../api'
import { useAsync } from '../../hooks'
import { AttentionBadge, Card, CardHead, Loading, Meter, StatTile } from '../../components/ui'

export default function Overview({ analysisId, analysis }: { analysisId: number; analysis: Analysis }) {
  const readiness = useAsync(() => api.getReadiness(analysisId), [analysisId])

  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="grid grid-4">
        <StatTile label="Files changed" value={analysis.files_changed}
          delta={`+${analysis.files_added} / ~${analysis.files_modified} / -${analysis.files_deleted}`} />
        <StatTile label="Lines" value={<span><span className="pos">+{analysis.lines_added}</span> <span className="neg">-{analysis.lines_removed}</span></span>} />
        <StatTile label="Review attention" value={<AttentionBadge level={analysis.attention_level} />}
          delta={`score ${analysis.risk_score}`} />
        <StatTile label="Verification completeness"
          value={readiness.data ? `${readiness.data.completeness_percent}%` : '—'} />
      </div>

      <div className="grid grid-2">
        <Card>
          <CardHead title="Change set" />
          <div className="card-pad">
            <dl className="kv">
              <dt>Added files</dt><dd>{analysis.files_added}</dd>
              <dt>Modified files</dt><dd>{analysis.files_modified}</dd>
              <dt>Deleted files</dt><dd>{analysis.files_deleted}</dd>
              <dt>Renamed files</dt><dd>{analysis.files_renamed}</dd>
              <dt>Lines added</dt><dd className="pos">+{analysis.lines_added}</dd>
              <dt>Lines removed</dt><dd className="neg">-{analysis.lines_removed}</dd>
              <dt>Analyzed at</dt><dd className="small">{analysis.created_at?.replace('T', ' ').slice(0, 19)}</dd>
            </dl>
          </div>
        </Card>

        <Card>
          <CardHead title="Review readiness" />
          <div className="card-pad">
            {readiness.loading ? <Loading /> : readiness.data && (
              <div className="stack" style={{ gap: 14 }}>
                <div>
                  <div className="row between small"><span className="muted">{readiness.data.completeness_label}</span>
                    <b>{readiness.data.completeness_percent}%</b></div>
                  <Meter percent={readiness.data.completeness_percent} tone="low" />
                </div>
                <div className="grid grid-3">
                  <StatTile label="Completed" value={readiness.data.completed_tasks} />
                  <StatTile label="Pending" value={readiness.data.pending_tasks} />
                  <StatTile label="Blocked" value={readiness.data.blocked_tasks} />
                </div>
                <div className="grid grid-3">
                  <StatTile label="Risk findings" value={readiness.data.risk_finding_count} />
                  <StatTile label="Test gaps" value={readiness.data.test_gap_count} />
                  <StatTile label="Affected modules" value={readiness.data.affected_module_count} />
                </div>
                <div className="row">
                  <Link className="btn sm" to={`/analyses/${analysisId}/risk`}>View risk →</Link>
                  <Link className="btn sm" to={`/analyses/${analysisId}/verification`}>Verification plan →</Link>
                  <Link className="btn sm" to={`/analyses/${analysisId}/report`}>Report →</Link>
                </div>
              </div>
            )}
          </div>
        </Card>
      </div>
    </div>
  )
}
