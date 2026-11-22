import { useState } from "react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Card, CardHead, Skeleton } from "../components/ui";
import { NoScan } from "../components/Layout";
import { Donut, Legend, LICENSE_COLORS, type Slice } from "../components/Charts";
import { LicenseBadge } from "../lib/badges";
import { PackageDrawer } from "../components/PackageDrawer";
import { titleCase } from "../lib/format";

export function Licenses() {
  const { currentScanId } = useApp();
  const [pkg, setPkg] = useState<string | null>(null);
  const [filter, setFilter] = useState<string>("");
  const { data, loading } = useAsync(
    () => (currentScanId ? api.licenses(currentScanId) : Promise.resolve(null)),
    [currentScanId],
  );
  if (!currentScanId) return <NoScan />;
  if (loading) return <Skeleton h={400} />;
  if (!data) return null;

  const families: Slice[] = Object.entries(data.family_distribution).map(([k, v]) => ({
    label: titleCase(k),
    value: v,
    color: LICENSE_COLORS[k] ?? "var(--text-3)",
  }));
  const verdicts = data.verdict_distribution;
  const inventory = data.inventory
    .filter((r) => !filter || r.license_verdict === filter || r.license_family === filter)
    .sort((a, b) => a.name.localeCompare(b.name));

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Licenses</h2>
          <p>Heuristic classification against the active policy — not legal advice.</p>
        </div>
      </div>

      <div className="grid-3" style={{ gridTemplateColumns: "300px 1fr" }}>
        <div className="col" style={{ gap: "var(--sp-5)" }}>
          <Card>
            <CardHead title="Families" />
            <div className="card-pad">
              <Donut data={families} centerLabel="packages" />
              <Legend data={families} />
            </div>
          </Card>
          <Card className="card-pad">
            <strong style={{ fontSize: "var(--text-sm)" }}>Policy verdicts</strong>
            <div className="col" style={{ gap: 8, marginTop: 10 }}>
              {["allowed", "review", "restricted"].map((v) => (
                <button key={v} className="row spread" style={{ background: "none", border: "none", cursor: "pointer", padding: 0 }} onClick={() => setFilter(filter === v ? "" : v)}>
                  <LicenseBadge verdict={v as any} />
                  <strong>{verdicts[v] ?? 0}</strong>
                </button>
              ))}
            </div>
          </Card>
        </div>

        <Card>
          <CardHead title="License inventory" subtitle={filter ? `filtered: ${filter}` : `${inventory.length} packages`} />
          <div className="table-wrap" style={{ border: "none", borderRadius: 0 }}>
            <table className="data">
              <thead><tr><th>Package</th><th>Version</th><th>License</th><th>Family / verdict</th></tr></thead>
              <tbody>
                {inventory.map((r) => (
                  <tr key={r.name + r.version} className="clickable" onClick={() => setPkg(r.name)}>
                    <td className="mono" style={{ fontWeight: 540 }}>{r.name}</td>
                    <td className="mono muted">{r.version}</td>
                    <td className="mono">{r.license ?? <span className="muted">unknown</span>}</td>
                    <td><LicenseBadge verdict={r.license_verdict} family={r.license_family} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </Card>
      </div>
      {pkg && <PackageDrawer scanId={currentScanId} name={pkg} onClose={() => setPkg(null)} />}
    </>
  );
}
