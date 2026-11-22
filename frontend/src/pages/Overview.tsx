import { useNavigate } from "react-router-dom";
import {
  AlertTriangle,
  Boxes,
  CircleSlash,
  Download,
  GitFork,
  PackageX,
  Scale,
  ShieldAlert,
} from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Badge, Button, Card, CardHead, EmptyState, Skeleton } from "../components/ui";
import { NoScan } from "../components/Layout";
import { Donut, Legend, LICENSE_COLORS, SEVERITY_COLORS, type Slice } from "../components/Charts";
import { gradeTone } from "../lib/badges";
import { formatDate, titleCase } from "../lib/format";
import { useState } from "react";
import { PackageDrawer } from "../components/PackageDrawer";

export function Overview() {
  const { currentScanId } = useApp();
  const navigate = useNavigate();
  const [pkg, setPkg] = useState<string | null>(null);
  const { data, loading, error } = useAsync(
    () => (currentScanId ? api.scanDetail(currentScanId) : Promise.resolve(null)),
    [currentScanId],
  );

  if (!currentScanId) return <NoScan />;
  if (loading) return <OverviewSkeleton />;
  if (error || !data) return <EmptyState icon={<AlertTriangle />} title="Could not load scan">{error}</EmptyState>;

  const s = data.summary;
  const health = s.health;
  const composition: Slice[] = [
    { label: "Direct", value: s.direct, color: "var(--accent)" },
    { label: "Transitive", value: s.transitive, color: "var(--text-3)" },
  ];
  const severity: Slice[] = Object.entries(s.severity_distribution).map(([k, v]) => ({
    label: titleCase(k),
    value: v,
    color: SEVERITY_COLORS[k] ?? "var(--text-3)",
  }));
  const licenses: Slice[] = Object.entries(s.license_distribution).map(([k, v]) => ({
    label: titleCase(k),
    value: v,
    color: LICENSE_COLORS[k] ?? "var(--text-3)",
  }));

  const kpis = [
    { label: "Dependencies", value: s.total, sub: `${s.direct} direct · ${s.transitive} transitive`, icon: Boxes, to: "/explorer" },
    { label: "Vulnerable", value: s.vulnerable_packages, sub: "packages with advisories", icon: ShieldAlert, to: "/security", danger: s.vulnerable_packages > 0 },
    { label: "Outdated", value: s.outdated, sub: "updates available", icon: GitFork, to: "/updates" },
    { label: "Unused", value: s.potentially_unused, sub: "no usage evidence", icon: PackageX, to: "/usage" },
    { label: "License warnings", value: s.license_warnings, sub: `${s.unknown_licenses} unknown`, icon: Scale, to: "/licenses" },
    { label: "Maintenance", value: s.maintenance_concerns, sub: "concerns / deprecated", icon: CircleSlash, to: "/explorer?filter=deprecated" },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <h2>{data.root_name ?? data.project.name}</h2>
          <p>
            <span className="mono">{data.project.path}</span>
          </p>
        </div>
        <div className="row">
          <Badge tone={data.online ? "info" : "neutral"}>{data.online ? "Online scan" : "Offline scan"}</Badge>
          <span className="muted" style={{ fontSize: "var(--text-sm)" }}>{formatDate(data.created_at)}</span>
          <Button onClick={() => navigate("/reports")}>
            <Download size={16} /> Export
          </Button>
        </div>
      </div>

      <div className="grid-3" style={{ gridTemplateColumns: "340px 1fr", alignItems: "stretch" }}>
        <HealthCard score={data.health_score} grade={data.health_grade} confidence={data.health_confidence} factors={health.factors} notes={health.notes} />
        <div className="stat-grid" style={{ alignContent: "start" }}>
          {kpis.map((k) => (
            <button key={k.label} className="stat" onClick={() => navigate(k.to)}>
              <span className="stat-label">
                <k.icon size={14} /> {k.label}
              </span>
              <span className="stat-value" style={{ color: k.danger ? "var(--danger)" : undefined }}>
                {k.value}
              </span>
              <span className="stat-sub">{k.sub}</span>
            </button>
          ))}
        </div>
      </div>

      <div className="grid-3">
        <Card>
          <CardHead title="Composition" subtitle="Direct vs transitive" />
          <div className="card-pad">
            <Donut data={composition} centerLabel="packages" />
            <Legend data={composition} />
          </div>
        </Card>
        <Card>
          <CardHead title="Security severity" subtitle={`${s.vulnerable_packages} affected packages`} />
          <div className="card-pad">
            {severity.length ? (
              <>
                <Donut data={severity} centerLabel="advisories" />
                <Legend data={severity} />
              </>
            ) : (
              <EmptyState icon={<ShieldAlert />} title={data.online ? "No advisories found" : "Not checked offline"}>
                {data.online ? "No known advisories for the installed versions." : "Run an online scan to check OSV.dev."}
              </EmptyState>
            )}
          </div>
        </Card>
        <Card>
          <CardHead title="License families" />
          <div className="card-pad">
            <Donut data={licenses} centerLabel="packages" />
            <Legend data={licenses} />
          </div>
        </Card>
      </div>

      <RecentFindings scanId={currentScanId} onOpen={setPkg} />

      {pkg && <PackageDrawer scanId={currentScanId} name={pkg} onClose={() => setPkg(null)} />}
    </>
  );
}

function HealthCard({
  score,
  grade,
  confidence,
  factors,
  notes,
}: {
  score: number;
  grade: string;
  confidence: string;
  factors: { label: string; impact: number; category: string }[];
  notes: string[];
}) {
  const color = gradeTone(grade);
  return (
    <Card>
      <CardHead title="Health score" subtitle="Transparent, rule-based" />
      <div className="card-pad">
        <div className="row" style={{ gap: "var(--sp-5)", alignItems: "baseline" }}>
          <div style={{ fontSize: 56, fontWeight: 700, color, lineHeight: 1, letterSpacing: "-0.03em" }}>
            {score}
          </div>
          <div className="col" style={{ gap: 4 }}>
            <Badge tone={grade === "A" || grade === "B" ? "ok" : grade === "C" || grade === "D" ? "warn" : "danger"}>
              Grade {grade}
            </Badge>
            <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
              out of 100 · {confidence}
            </span>
          </div>
        </div>
        {confidence === "partial" && (
          <div className="row" style={{ gap: 7, marginTop: 12, color: "var(--warn)", fontSize: "var(--text-sm)" }}>
            <AlertTriangle size={14} /> Based on incomplete data — not inflated.
          </div>
        )}
        <div className="col" style={{ gap: 6, marginTop: "var(--sp-4)" }}>
          <span className="muted" style={{ fontSize: "var(--text-xs)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
            What reduced the score
          </span>
          {factors.length === 0 && <span className="dim" style={{ fontSize: "var(--text-sm)" }}>Nothing — clean bill of health.</span>}
          {factors.slice(0, 7).map((f, i) => (
            <div key={i} className="row spread" style={{ fontSize: "var(--text-sm)" }}>
              <span className="dim">{f.label}</span>
              <strong style={{ color: "var(--danger)" }}>{f.impact.toFixed(0)}</strong>
            </div>
          ))}
        </div>
        {notes.map((n, i) => (
          <p key={i} className="muted" style={{ fontSize: "var(--text-xs)", marginTop: 10, marginBottom: 0 }}>
            {n}
          </p>
        ))}
      </div>
    </Card>
  );
}

function RecentFindings({ scanId, onOpen }: { scanId: number; onOpen: (p: string) => void }) {
  const { data } = useAsync(
    () => api.packages(scanId, { sort: "severity", order: "asc" }),
    [scanId],
  );
  if (!data) return null;
  const findings = data.packages
    .filter((p) => (p.vuln_count ?? 0) > 0 || p.update_type === "major" || p.usage_status === "none" || p.license_verdict === "restricted")
    .slice(0, 8);
  if (findings.length === 0) return null;
  return (
    <Card>
      <CardHead title="Top findings" subtitle="Highest-priority items across all checks" />
      <div style={{ padding: "var(--sp-2) var(--sp-3)" }}>
        {findings.map((p) => (
          <button
            key={p.node_id}
            className="nav-item"
            style={{ width: "100%", justifyContent: "flex-start" }}
            onClick={() => onOpen(p.name)}
          >
            <span className="mono" style={{ minWidth: 160, textAlign: "left" }}>{p.name}</span>
            <span className="muted mono" style={{ fontSize: "var(--text-xs)" }}>{p.version}</span>
            <span className="row" style={{ marginLeft: "auto", gap: 6 }}>
              {(p.vuln_count ?? 0) > 0 && (
                <Badge tone={p.max_severity === "critical" ? "crit" : p.max_severity === "high" ? "danger" : "warn"}>
                  {p.vuln_count} advisory{(p.vuln_count ?? 0) > 1 ? "s" : ""}
                </Badge>
              )}
              {p.update_type === "major" && <Badge tone="warn">major update</Badge>}
              {p.usage_status === "none" && <Badge tone="neutral">unused?</Badge>}
              {p.license_verdict === "restricted" && <Badge tone="danger">license</Badge>}
            </span>
          </button>
        ))}
      </div>
    </Card>
  );
}

function OverviewSkeleton() {
  return (
    <>
      <Skeleton h={40} w={320} />
      <div className="grid-3" style={{ gridTemplateColumns: "340px 1fr" }}>
        <Skeleton h={320} />
        <div className="stat-grid">
          {Array.from({ length: 6 }).map((_, i) => (
            <Skeleton key={i} h={96} />
          ))}
        </div>
      </div>
      <div className="grid-3">
        <Skeleton h={260} />
        <Skeleton h={260} />
        <Skeleton h={260} />
      </div>
    </>
  );
}
