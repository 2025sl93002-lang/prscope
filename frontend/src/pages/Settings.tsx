import { useState } from "react";
import { Github, Lock, Moon, Sun } from "lucide-react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { useTheme } from "../state/theme";
import { Badge, Button, Card, CardHead, Skeleton, useToast } from "../components/ui";
import { titleCase } from "../lib/format";

const FAMILIES = ["permissive", "weak-copyleft", "copyleft", "proprietary", "other", "unknown"];
const VERDICTS = ["allowed", "review", "restricted"];

export function Settings() {
  const { theme, toggle } = useTheme();
  const toast = useToast();
  const { data, loading, reload } = useAsync(() => api.getSettings(), []);
  const [policy, setPolicy] = useState<Record<string, string> | null>(null);

  if (loading || !data) return <Skeleton h={400} />;
  const activePolicy = policy ?? data.license_policy;

  async function saveOnline(v: boolean) {
    await api.updateSettings({ online_default: v });
    toast.push("success", "Preference saved.");
    reload();
  }
  async function savePolicy() {
    await api.updateSettings({ license_policy: activePolicy });
    toast.push("success", "License policy saved.");
    setPolicy(null);
    reload();
  }

  return (
    <>
      <div className="page-head">
        <div><h2>Settings</h2><p>DepLens v{data.version} · local-first, no account required.</p></div>
      </div>

      <Card>
        <CardHead title="General" />
        <div className="card-pad col" style={{ gap: "var(--sp-4)" }}>
          <div className="row spread">
            <div className="col"><strong>Theme</strong><span className="muted" style={{ fontSize: "var(--text-sm)" }}>Preference is saved in your browser.</span></div>
            <Button variant="secondary" onClick={toggle}>{theme === "dark" ? <Sun size={16} /> : <Moon size={16} />} {titleCase(theme)}</Button>
          </div>
          <div className="row spread">
            <div className="col"><strong>Online analysis by default</strong><span className="muted" style={{ fontSize: "var(--text-sm)" }}>Query npm registry & OSV.dev on new scans.</span></div>
            <label className="row" style={{ cursor: "pointer" }}>
              <input type="checkbox" checked={data.online_default} onChange={(e) => saveOnline(e.target.checked)} />
            </label>
          </div>
        </div>
      </Card>

      <Card>
        <CardHead title="License policy" subtitle="How each license family is treated" actions={policy && <Button size="sm" variant="primary" onClick={savePolicy}>Save policy</Button>} />
        <div className="card-pad col" style={{ gap: 10 }}>
          {FAMILIES.map((f) => (
            <div key={f} className="row spread">
              <span>{titleCase(f)}</span>
              <select
                className="select"
                style={{ width: "auto" }}
                value={activePolicy[f] ?? "review"}
                onChange={(e) => setPolicy({ ...activePolicy, [f]: e.target.value })}
              >
                {VERDICTS.map((v) => <option key={v} value={v}>{titleCase(v)}</option>)}
              </select>
            </div>
          ))}
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}>Classification is heuristic and is not legal advice.</span>
        </div>
      </Card>

      <Card>
        <CardHead title="Privacy" subtitle={data.privacy.telemetry} />
        <div className="card-pad grid-3">
          <PrivacyList title="Stays on your machine" items={data.privacy.local_data} tone="ok" />
          <PrivacyList title="Sent to public APIs" items={data.privacy.sent_to_public_apis} tone="warn" />
          <PrivacyList title="Never sent" items={data.privacy.never_sent} tone="danger" />
        </div>
        <div className="card-pad" style={{ paddingTop: 0 }}>
          <div className="row wrap" style={{ gap: 8 }}>
            {data.privacy.external_sources.map((s) => (
              <a key={s.name} href={s.url} target="_blank" rel="noreferrer" className="badge badge-neutral">{s.name} — {s.purpose}</a>
            ))}
          </div>
        </div>
      </Card>

      <Card>
        <CardHead title="About" />
        <div className="card-pad col" style={{ gap: 10 }}>
          <div className="row spread"><span>Version</span><Badge tone="neutral">v{data.version}</Badge></div>
          <div className="row spread"><span>License</span><Badge tone="ok">MIT</Badge></div>
          <div className="row spread"><span>Privacy model</span><span className="local-pill"><Lock size={11} /> Local-first</span></div>
          <a href="https://github.com/2025sl93002-lang/prscope" target="_blank" rel="noreferrer" className="row" style={{ gap: 6 }}><Github size={15} /> Source repository</a>
          <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
            Built with FastAPI, NetworkX, React, Cytoscape.js and Recharts — all open source. Advisory
            data from OSV.dev. See THIRD_PARTY_NOTICES.md for the full inventory.
          </span>
        </div>
      </Card>
    </>
  );
}

function PrivacyList({ title, items, tone }: { title: string; items: string[]; tone: "ok" | "warn" | "danger" }) {
  const color = tone === "ok" ? "var(--ok)" : tone === "warn" ? "var(--warn)" : "var(--danger)";
  return (
    <div className="col" style={{ gap: 6 }}>
      <strong style={{ fontSize: "var(--text-sm)", color }}>{title}</strong>
      {items.map((i) => <span key={i} className="dim" style={{ fontSize: "var(--text-sm)" }}>• {i}</span>)}
    </div>
  );
}
