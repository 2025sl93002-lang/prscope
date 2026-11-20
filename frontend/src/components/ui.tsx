// Shared UI primitives. SPDX-License-Identifier: MIT
import type { ReactNode } from 'react'
import type { AttentionLevel } from '../api'

export function Spinner() {
  return <span className="spinner" aria-label="loading" />
}

export function Loading({ label = 'Loading…' }: { label?: string }) {
  return (
    <div className="loading-wrap">
      <Spinner /> {label}
    </div>
  )
}

export function ErrorBox({ message }: { message: string }) {
  return (
    <div className="error-box" role="alert">
      <strong>Something went wrong.</strong>
      <div className="small mt">{message}</div>
    </div>
  )
}

export function Empty({ icon = '∅', title, hint }: { icon?: string; title: string; hint?: ReactNode }) {
  return (
    <div className="empty">
      <div className="icon">{icon}</div>
      <div style={{ fontWeight: 600, color: 'var(--fg)' }}>{title}</div>
      {hint && <div className="small mt">{hint}</div>}
    </div>
  )
}

export function Card({ children, className = '' }: { children: ReactNode; className?: string }) {
  return <div className={`card ${className}`}>{children}</div>
}

export function CardHead({ title, sub, right }: { title: ReactNode; sub?: ReactNode; right?: ReactNode }) {
  return (
    <div className="card-head">
      <div style={{ flex: 1 }}>
        <h3>{title}</h3>
        {sub && <div className="sub">{sub}</div>}
      </div>
      {right}
    </div>
  )
}

export function StatTile({ label, value, delta, tone }: {
  label: string; value: ReactNode; delta?: ReactNode; tone?: 'pos' | 'neg'
}) {
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className="value">{value}</div>
      {delta != null && <div className={`delta ${tone || ''}`}>{delta}</div>}
    </div>
  )
}

export function AttentionBadge({ level }: { level: AttentionLevel | null | undefined }) {
  const l = level || 'low'
  return (
    <span className={`badge ${l}`}>
      <span className="dot" /> {l.charAt(0).toUpperCase() + l.slice(1)}
    </span>
  )
}

const CATEGORY_LABELS: Record<string, string> = {
  source: 'Source', test: 'Test', config: 'Config', infrastructure: 'Infra',
  migration: 'Migration', api_contract: 'API', documentation: 'Docs',
  dependency: 'Dependency', security: 'Security', build_ci: 'Build/CI', ui: 'UI', unknown: 'Unknown',
}
export function CategoryBadge({ category }: { category: string }) {
  return <span className="badge cat">{CATEGORY_LABELS[category] || category}</span>
}

export function StatusBadge({ status }: { status: string }) {
  const tone: Record<string, string> = {
    completed: 'low', open: 'accent', blocked: 'critical', not_applicable: 'neutral',
    complete: 'low', running: 'moderate', failed: 'critical', pending: 'neutral',
  }
  const label = status.replace('_', ' ')
  return <span className={`badge ${tone[status] || 'neutral'}`}>{label}</span>
}

export function Meter({ percent, tone }: { percent: number; tone?: string }) {
  return (
    <div className={`meter ${tone || ''}`}>
      <span style={{ width: `${Math.max(0, Math.min(100, percent))}%` }} />
    </div>
  )
}
