// About / Open Source page. SPDX-License-Identifier: MIT
import { api } from '../api'
import { useAsync } from '../hooks'
import { Card, CardHead } from '../components/ui'

export default function About() {
  const health = useAsync(() => api.health().catch(() => null), [])

  return (
    <div className="stack" style={{ gap: 20, maxWidth: 820 }}>
      <div>
        <h1>PRScope</h1>
        <p className="muted">Pull Request Verification &amp; Review Evidence Planner</p>
        <p>“Understand the impact. Know what to verify. Review with evidence.”</p>
      </div>

      <Card>
        <CardHead title="Change-to-Verification Traceability" sub="The core idea" />
        <div className="card-pad">
          <p className="small">PRScope links every stage of reviewing a change, and explains how each finding was derived:</p>
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', fontSize: '0.82rem' }}>
            {['Code change', 'Affected components', 'Potential impact', 'Required verification', 'Available evidence', 'Review readiness']
              .map((s, i, arr) => (
                <span key={s}><span className="badge accent">{s}</span>{i < arr.length - 1 && <span className="faint"> → </span>}</span>
              ))}
          </div>
        </div>
      </Card>

      <Card>
        <CardHead title="Open source &amp; local-first" />
        <div className="card-pad">
          <dl className="kv">
            <dt>License</dt><dd>MIT (SPDX-License-Identifier: MIT)</dd>
            <dt>Backend</dt><dd>Python · FastAPI · SQLite (stdlib) · git via subprocess · stdlib <code>ast</code></dd>
            <dt>Frontend</dt><dd>React · TypeScript · Vite · @xyflow/react</dd>
            <dt>AI</dt><dd>Optional, local (Ollama). Core works fully without it.</dd>
            <dt>API status</dt><dd>{health.data ? <span className="badge low">online · v{health.data.version}</span> : <span className="badge neutral">offline</span>}</dd>
          </dl>
          <p className="small muted mt">
            Repository source code is never uploaded. No telemetry. No paid services. Analysis is deterministic
            and explainable. See the project README and <code>docs/</code> for architecture, risk methodology,
            originality analysis, and limitations.
          </p>
        </div>
      </Card>

      <Card>
        <CardHead title="Limitations" sub="Honest scope of this POC" />
        <div className="card-pad">
          <ul className="small" style={{ margin: 0, paddingLeft: 18 }}>
            <li>File-level static analysis approximates — it does not guarantee runtime impact.</li>
            <li>Dependency analysis supports Python and relative JS/TS imports only.</li>
            <li>Test gaps are <i>potential</i> gaps inferred from imports and naming, not coverage data.</li>
            <li>Review attention reflects how much review a change warrants — not a probability of defects.</li>
            <li>GitHub PR import is not implemented in this POC (see the roadmap).</li>
          </ul>
        </div>
      </Card>
    </div>
  )
}
