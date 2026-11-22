import { useState } from "react";
import { ExternalLink, ShieldCheck, WifiOff } from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Badge, Card, CardHead, EmptyState, SeverityBadge, Skeleton } from "../components/ui";
import { NoScan } from "../components/Layout";
import { Donut, Legend, SEVERITY_COLORS, type Slice } from "../components/Charts";
import { PackageDrawer } from "../components/PackageDrawer";
import { RemediationCard } from "../components/RemediationCard";
import { titleCase } from "../lib/format";

const SEV_ORDER = ["critical", "high", "moderate", "low", "unknown"];

export function Security() {
  const { currentScanId } = useApp();
  const [pkg, setPkg] = useState<string | null>(null);
  const { data, loading } = useAsync(
    () => (currentScanId ? api.vulnerabilities(currentScanId) : Promise.resolve(null)),
    [currentScanId],
  );

  if (!currentScanId) return <NoScan />;
  if (loading) return <Skeleton h={400} />;
  if (!data) return null;

  if (!data.checked) {
    return (
      <>
        <div className="page-head"><div><h2>Security</h2><p>Advisory analysis via OSV.dev</p></div></div>
        <EmptyState icon={<WifiOff />} title="Security was not checked (offline scan)">
          This scan ran offline, so advisories were not fetched. DepLens does not assume packages
          are safe when it hasn't checked. Re-scan with online analysis enabled to query OSV.dev.
        </EmptyState>
      </>
    );
  }

  const counts: Record<string, number> = {};
  for (const v of data.vulnerabilities) counts[v.severity] = (counts[v.severity] ?? 0) + 1;
  const dist: Slice[] = SEV_ORDER.filter((s) => counts[s]).map((s) => ({
    label: titleCase(s),
    value: counts[s],
    color: SEVERITY_COLORS[s],
  }));

  return (
    <>
      <div className="page-head">
        <div><h2>Security</h2><p>{data.count} advisories from OSV.dev (open-source, no account)</p></div>
      </div>

      {data.count === 0 ? (
        <EmptyState icon={<ShieldCheck />} title="No known advisories">
          None of the installed package versions have advisories in the OSV database at scan time.
          This is not a guarantee of safety — new advisories are published over time.
        </EmptyState>
      ) : (
        <>
          <RemediationCard scanId={currentScanId} />
          <div className="grid-3" style={{ gridTemplateColumns: "300px 1fr" }}>
          <Card>
            <CardHead title="Severity" />
            <div className="card-pad">
              <Donut data={dist} centerLabel="advisories" />
              <Legend data={dist} />
            </div>
          </Card>
          <Card>
            <CardHead title="Findings" subtitle="Most severe first" />
            <div style={{ padding: "var(--sp-2) var(--sp-3)" }}>
              {data.vulnerabilities.map((v) => (
                <div key={v.id} className="card" style={{ padding: "var(--sp-3) var(--sp-4)", marginBottom: 8, boxShadow: "none" }}>
                  <div className="row spread wrap" style={{ gap: 8 }}>
                    <div className="row" style={{ gap: 10 }}>
                      <SeverityBadge severity={v.severity} />
                      <button className="mono" style={{ fontWeight: 560, background: "none", border: "none", cursor: "pointer", color: "var(--text-1)" }} onClick={() => setPkg(v.package)}>
                        {v.package}
                      </button>
                      <span className="muted mono" style={{ fontSize: "var(--text-xs)" }}>{v.installed_version}</span>
                    </div>
                    <a href={v.url} target="_blank" rel="noreferrer" className="row" style={{ gap: 4, fontSize: "var(--text-sm)" }}>
                      {v.cve ?? v.osv_id} <ExternalLink size={12} />
                    </a>
                  </div>
                  <p style={{ margin: "8px 0", fontSize: "var(--text-sm)" }}>{v.summary}</p>
                  <div className="row wrap" style={{ gap: 8 }}>
                    {v.fixed_version ? (
                      <Badge tone="ok">Fix: upgrade to {v.fixed_version}</Badge>
                    ) : (
                      <Badge tone="neutral">No fixed release recorded</Badge>
                    )}
                    <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
                      Why present: {v.package} is installed in the resolved tree.
                    </span>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>
        </>
      )}
      {pkg && <PackageDrawer scanId={currentScanId} name={pkg} onClose={() => setPkg(null)} />}
    </>
  );
}
