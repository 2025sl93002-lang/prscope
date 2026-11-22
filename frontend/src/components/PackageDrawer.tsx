import { useNavigate } from "react-router-dom";
import { ExternalLink, GitBranch, TestTubeDiagonal } from "lucide-react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { Badge, Button, Drawer, SeverityBadge, Skeleton } from "./ui";
import { LicenseBadge, MaintenanceBadge, UpdateBadge, UsageBadge } from "../lib/badges";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="col" style={{ gap: 3 }}>
      <span className="muted" style={{ fontSize: "var(--text-xs)", textTransform: "uppercase", letterSpacing: "0.04em" }}>
        {label}
      </span>
      <span>{children}</span>
    </div>
  );
}

export function PackageDrawer({
  scanId,
  name,
  onClose,
}: {
  scanId: number;
  name: string;
  onClose: () => void;
}) {
  const { data, loading } = useAsync(() => api.packageDetail(scanId, name), [scanId, name]);
  const navigate = useNavigate();

  return (
    <Drawer
      title={<span className="mono">{name}</span>}
      subtitle={data ? `${data.version}${data.latest && data.latest !== data.version ? ` → ${data.latest} available` : ""}` : ""}
      onClose={onClose}
    >
      {loading && (
        <div className="col" style={{ gap: 12 }}>
          <Skeleton h={60} />
          <Skeleton h={120} />
          <Skeleton h={90} />
        </div>
      )}
      {data && (
        <div className="col" style={{ gap: "var(--sp-5)" }}>
          {data.data?.description && <p className="dim" style={{ margin: 0 }}>{data.data.description}</p>}

          <div className="row wrap" style={{ gap: "var(--sp-2)" }}>
            <Badge tone={data.is_direct ? "accent" : "neutral"}>
              {data.is_direct ? "Direct" : "Transitive"}
            </Badge>
            <Badge tone="neutral">{data.scope}</Badge>
            <UpdateBadge type={data.update_type} />
            <LicenseBadge verdict={data.license_verdict} family={data.license_family} />
            <UsageBadge status={data.usage_status} />
            <MaintenanceBadge status={data.maintenance_status} />
          </div>

          <div className="grid-3" style={{ gridTemplateColumns: "repeat(3,1fr)", gap: "var(--sp-4)" }}>
            <Field label="Installed">{data.version}</Field>
            <Field label="Latest">{data.latest ?? "unknown"}</Field>
            <Field label="License">{data.license ?? "unknown"}</Field>
            <Field label="Depth">{data.depth}</Field>
            <Field label="Dependents">{data.dependents}</Field>
            <Field label="Paths">{data.path_count}</Field>
          </div>

          {data.data?.maintenance?.signals?.length > 0 && (
            <div className="col" style={{ gap: 4 }}>
              <strong style={{ fontSize: "var(--text-sm)" }}>Maintenance signals</strong>
              {data.data.maintenance.signals.map((s: string, i: number) => (
                <span key={i} className="dim" style={{ fontSize: "var(--text-sm)" }}>• {s}</span>
              ))}
            </div>
          )}

          {data.vulnerabilities.length > 0 && (
            <div className="col" style={{ gap: "var(--sp-2)" }}>
              <strong style={{ fontSize: "var(--text-sm)" }}>
                Security advisories ({data.vulnerabilities.length})
              </strong>
              {data.vulnerabilities.map((v) => (
                <div key={v.osv_id} className="card card-pad" style={{ padding: "var(--sp-3)" }}>
                  <div className="row spread">
                    <SeverityBadge severity={v.severity} />
                    <a href={v.url} target="_blank" rel="noreferrer" className="row" style={{ gap: 4, fontSize: "var(--text-sm)" }}>
                      {v.cve ?? v.osv_id} <ExternalLink size={12} />
                    </a>
                  </div>
                  <p style={{ margin: "8px 0 4px", fontSize: "var(--text-sm)" }}>{v.summary}</p>
                  <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
                    {v.fixed_version ? `Fixed in ${v.fixed_version}` : "No fixed release recorded"}
                  </span>
                </div>
              ))}
            </div>
          )}

          {data.data?.usage?.evidence?.length > 0 && (
            <div className="col" style={{ gap: 4 }}>
              <strong style={{ fontSize: "var(--text-sm)" }}>Usage evidence</strong>
              <span className="muted" style={{ fontSize: "var(--text-xs)" }}>{data.data.usage.explanation}</span>
              {data.data.usage.evidence.slice(0, 6).map((e: any, i: number) => (
                <div key={i} className="mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-2)" }}>
                  {e.file}:{e.line} <span className="muted">({e.method})</span>
                </div>
              ))}
            </div>
          )}

          <div className="col" style={{ gap: 6 }}>
            <strong style={{ fontSize: "var(--text-sm)" }}>
              <GitBranch size={13} style={{ verticalAlign: "-2px" }} /> Dependency paths
            </strong>
            {data.dependency_paths.length === 0 && <span className="muted">No path data.</span>}
            {data.dependency_paths.slice(0, 8).map((path, i) => (
              <div key={i} className="mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-2)" }}>
                {path.join(" → ")}
              </div>
            ))}
          </div>

          <Button
            variant="secondary"
            onClick={() => navigate(`/impact?package=${encodeURIComponent(name)}`)}
          >
            <TestTubeDiagonal size={16} /> Simulate a change to this package
          </Button>
        </div>
      )}
    </Drawer>
  );
}
