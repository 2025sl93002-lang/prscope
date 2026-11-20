// App layout: sidebar navigation + topbar. SPDX-License-Identifier: MIT
import { useState } from 'react'
import { NavLink, useNavigate } from 'react-router-dom'
import { useActiveAnalysis } from '../active'

interface NavDef { to: string; label: string; icon: string; section?: boolean }

const MAIN: NavDef[] = [
  { to: '/', label: 'Dashboard', icon: '▦' },
  { to: '/repositories', label: 'Repositories', icon: '⌥' },
  { to: '/analyses', label: 'Analyses', icon: '≋' },
]
const ANALYSIS_SECTIONS: { tab: string; label: string; icon: string }[] = [
  { tab: 'impact', label: 'Impact Explorer', icon: '◉' },
  { tab: 'verification', label: 'Verification Plan', icon: '✓' },
  { tab: 'evidence', label: 'Evidence Ledger', icon: '▤' },
  { tab: 'checklist', label: 'Review Checklist', icon: '☑' },
  { tab: 'report', label: 'Reports', icon: '⤓' },
]
const FOOT: NavDef[] = [
  { to: '/settings', label: 'Settings', icon: '⚙' },
  { to: '/about', label: 'About / OSS', icon: 'ⓘ' },
]

export function Sidebar({ open }: { open: boolean }) {
  const { activeId } = useActiveAnalysis()
  const navigate = useNavigate()

  const goSection = (tab: string) => {
    if (activeId) navigate(`/analyses/${activeId}/${tab}`)
    else navigate('/analyses')
  }

  return (
    <aside className={`sidebar ${open ? 'open' : ''}`}>
      <div className="brand">
        <div className="logo">P</div>
        <div>
          PRScope
          <div className="tagline">Review with evidence</div>
        </div>
      </div>

      {MAIN.map((n) => (
        <NavLink key={n.to} to={n.to} end={n.to === '/'}
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="ico">{n.icon}</span> {n.label}
        </NavLink>
      ))}

      <div className="nav-group-label">
        Active analysis {activeId ? `#${activeId}` : '(none)'}
      </div>
      {ANALYSIS_SECTIONS.map((s) => (
        <div key={s.tab} className="nav-item" onClick={() => goSection(s.tab)} role="button" tabIndex={0}
          onKeyDown={(e) => e.key === 'Enter' && goSection(s.tab)}
          style={{ opacity: activeId ? 1 : 0.55 }}>
          <span className="ico">{s.icon}</span> {s.label}
        </div>
      ))}

      <div className="spacer" />
      {FOOT.map((n) => (
        <NavLink key={n.to} to={n.to}
          className={({ isActive }) => `nav-item ${isActive ? 'active' : ''}`}>
          <span className="ico">{n.icon}</span> {n.label}
        </NavLink>
      ))}
      <div className="side-foot">MIT-licensed · local-first · v0.1.0</div>
    </aside>
  )
}

export function Layout({ crumbs, children }: { crumbs: React.ReactNode; children: React.ReactNode }) {
  const [open, setOpen] = useState(false)
  return (
    <div className="app">
      <Sidebar open={open} />
      <div className="main">
        <div className="topbar">
          <button className="btn ghost sm" onClick={() => setOpen((o) => !o)}
            aria-label="Toggle navigation" style={{ display: 'none' }}>☰</button>
          <div className="crumbs">{crumbs}</div>
        </div>
        <div className="content">{children}</div>
      </div>
    </div>
  )
}
