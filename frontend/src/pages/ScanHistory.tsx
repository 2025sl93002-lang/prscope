import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Badge, Button, Card, CardHead, EmptyState, Skeleton } from "../components/ui";
import { NoScan } from "../components/Layout";
import { formatDate } from "../lib/format";
import { gradeTone } from "../lib/badges";

export function ScanHistory() {
  const { currentProjectId, currentScanId, setCurrentScan } = useApp();
  const [compareWith, setCompareWith] = useState<number | null>(null);
  const { data, loading } = useAsync(
    () => (currentProjectId ? api.projectScans(currentProjectId) : Promise.resolve(null)),
    [currentProjectId],
  );
  if (!currentProjectId) return <NoScan />;
  if (loading) return <Skeleton h={300} />;
  const scans = data?.scans ?? [];

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Scan History</h2>
          <p>{scans.length} scans recorded locally for this project.</p>
        </div>
      </div>

      {scans.length === 0 ? (
        <EmptyState title="No scans yet" />
      ) : (
        <>
          <div className="table-wrap">
            <table className="data">
              <thead>
                <tr>
                  <th>Date</th><th>Health</th><th>Deps</th><th>Vulnerable</th><th>Outdated</th><th>License warn</th><th>Mode</th><th></th>
                </tr>
              </thead>
              <tbody>
                {scans.map((s) => (
                  <tr key={s.id} className={s.id === currentScanId ? "" : "clickable"} style={s.id === currentScanId ? { background: "var(--accent-soft)" } : {}}>
                    <td>{formatDate(s.created_at)}</td>
                    <td>
                      <strong style={{ color: gradeTone(s.health_grade) }}>{s.health_score}</strong>{" "}
                      <span className="muted">{s.health_grade}</span>
                    </td>
                    <td>{s.total ?? "—"}</td>
                    <td>{s.vulnerable_packages ?? "—"}</td>
                    <td>{s.outdated ?? "—"}</td>
                    <td>{s.license_warnings ?? "—"}</td>
                    <td><Badge tone={s.online ? "info" : "neutral"}>{s.online ? "online" : "offline"}</Badge></td>
                    <td>
                      <div className="row" style={{ gap: 6, justifyContent: "flex-end" }}>
                        {s.id !== currentScanId && <Button size="sm" variant="ghost" onClick={() => setCurrentScan(s.id)}>View</Button>}
                        <Button size="sm" variant="ghost" onClick={() => setCompareWith(s.id)}>Compare</Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          {compareWith && currentScanId && compareWith !== currentScanId && (
            <ComparisonCard base={compareWith} target={currentScanId} onClose={() => setCompareWith(null)} />
          )}
          {compareWith === currentScanId && (
            <Card className="card-pad"><p className="muted" style={{ margin: 0 }}>Select a different scan (then “Compare”) to diff against the current one (#{currentScanId}).</p></Card>
          )}
        </>
      )}
    </>
  );
}

function ComparisonCard({ base, target, onClose }: { base: number; target: number; onClose: () => void }) {
  const { data, loading } = useAsync(() => api.compare(target, base), [base, target]);
  return (
    <Card>
      <CardHead
        title={<span>Comparing scan #{base} <ArrowRight size={14} style={{ verticalAlign: "-2px" }} /> #{target}</span>}
        actions={<Button size="sm" variant="ghost" onClick={onClose}>Close</Button>}
      />
      <div className="card-pad">
        {loading && <Skeleton h={120} />}
        {data && (
          <div className="grid-3">
            <Stat label="Health change" value={`${data.health_change.delta >= 0 ? "+" : ""}${data.health_change.delta}`} tone={data.health_change.delta >= 0 ? "ok" : "danger"} />
            <Stat label="Added" value={data.added.length} />
            <Stat label="Removed" value={data.removed.length} />
            <Stat label="Updated" value={data.updated.length} />
            <Stat label="New advisories" value={data.vulnerabilities_added.length} tone={data.vulnerabilities_added.length ? "danger" : undefined} />
            <Stat label="Resolved advisories" value={data.vulnerabilities_resolved.length} tone="ok" />
          </div>
        )}
        {data && data.updated.length > 0 && (
          <div className="col" style={{ gap: 4, marginTop: 16 }}>
            <strong style={{ fontSize: "var(--text-sm)" }}>Updated packages</strong>
            {data.updated.map((u: any) => (
              <span key={u.name} className="mono" style={{ fontSize: "var(--text-xs)" }}>{u.name}: {u.from} → {u.to}</span>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}

function Stat({ label, value, tone }: { label: string; value: any; tone?: string }) {
  const color = tone === "ok" ? "var(--ok)" : tone === "danger" ? "var(--danger)" : "var(--text-1)";
  return (
    <div className="stat">
      <span className="stat-label">{label}</span>
      <span className="stat-value" style={{ color }}>{value}</span>
    </div>
  );
}
