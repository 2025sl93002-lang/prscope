import { useMemo, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ArrowDownUp, Download, Search } from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Badge, Button, EmptyState, Skeleton } from "../components/ui";
import { NoScan } from "../components/Layout";
import { LicenseBadge, MaintenanceBadge, UpdateBadge, UsageBadge } from "../lib/badges";
import { PackageDrawer } from "../components/PackageDrawer";

const FILTERS = [
  { key: "", label: "All" },
  { key: "direct", label: "Direct", type: true },
  { key: "transitive", label: "Transitive", type: true },
  { key: "prod", label: "Production" },
  { key: "dev", label: "Dev" },
  { key: "outdated", label: "Outdated" },
  { key: "vulnerable", label: "Vulnerable" },
  { key: "unused", label: "Unused?" },
  { key: "unknown-license", label: "Unknown license" },
  { key: "license-warning", label: "License warning" },
  { key: "deprecated", label: "Maintenance" },
];

const COLUMNS: { key: string; label: string; sortable?: boolean }[] = [
  { key: "name", label: "Package", sortable: true },
  { key: "version", label: "Installed", sortable: true },
  { key: "latest", label: "Latest" },
  { key: "scope", label: "Type" },
  { key: "update_type", label: "Update" },
  { key: "license_verdict", label: "License" },
  { key: "max_severity", label: "Security", sortable: true },
  { key: "usage_status", label: "Usage" },
  { key: "maintenance_status", label: "Maintenance" },
];

export function Explorer() {
  const { currentScanId } = useApp();
  const [params, setParams] = useSearchParams();
  const [q, setQ] = useState("");
  const [sort, setSort] = useState("name");
  const [order, setOrder] = useState<"asc" | "desc">("asc");
  const [selected, setSelected] = useState<string | null>(null);

  const activeFilter = params.get("filter") ?? "";

  const query = useMemo(() => {
    const p: Record<string, string> = { sort, order };
    const f = FILTERS.find((x) => x.key === activeFilter);
    if (f?.type) p.type = f.key;
    else if (f && f.key) {
      if (f.key === "prod" || f.key === "dev") p.scope = f.key;
      else p.filter = f.key;
    }
    return p;
  }, [activeFilter, sort, order]);

  const { data, loading } = useAsync(
    () => (currentScanId ? api.packages(currentScanId, query) : Promise.resolve(null)),
    [currentScanId, JSON.stringify(query)],
  );

  if (!currentScanId) return <NoScan />;

  const rows = (data?.packages ?? []).filter((p) => p.name.toLowerCase().includes(q.toLowerCase()));

  const toggleSort = (key: string) => {
    if (sort === key) setOrder((o) => (o === "asc" ? "desc" : "asc"));
    else {
      setSort(key);
      setOrder("asc");
    }
  };

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Dependencies</h2>
          <p>{data ? `${rows.length} of ${data.count} packages` : "Loading…"}</p>
        </div>
        <a href={api.reportUrl(currentScanId, "csv")} download>
          <Button><Download size={16} /> Export CSV</Button>
        </a>
      </div>

      <div className="row wrap" style={{ gap: "var(--sp-2)" }}>
        <div className="field-wrap" style={{ flex: "1 1 240px", maxWidth: 320 }}>
          <Search size={16} />
          <input className="input input-search" placeholder="Search packages…" value={q} onChange={(e) => setQ(e.target.value)} />
        </div>
        <div className="row wrap" style={{ gap: 6 }}>
          {FILTERS.map((f) => (
            <button
              key={f.key || "all"}
              className={`tab ${activeFilter === f.key ? "active" : ""}`}
              style={{ borderBottom: "none", borderRadius: "var(--radius-full)", padding: "5px 12px", background: activeFilter === f.key ? "var(--accent-soft)" : "var(--surface-2)" }}
              onClick={() => setParams(f.key ? { filter: f.key } : {})}
            >
              {f.label}
            </button>
          ))}
        </div>
      </div>

      {loading && <Skeleton h={400} />}
      {data && rows.length === 0 && <EmptyState title="No matching packages">Try a different filter or search term.</EmptyState>}
      {data && rows.length > 0 && (
        <div className="table-wrap">
          <table className="data">
            <thead>
              <tr>
                {COLUMNS.map((c) => (
                  <th
                    key={c.key}
                    className={c.sortable ? "sortable" : ""}
                    onClick={() => c.sortable && toggleSort(c.key)}
                  >
                    <span className="row" style={{ gap: 4 }}>
                      {c.label}
                      {c.sortable && sort === c.key && <ArrowDownUp size={11} />}
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {rows.map((p) => (
                <tr key={p.node_id} className="clickable" onClick={() => setSelected(p.name)}>
                  <td>
                    <span className="mono" style={{ fontWeight: 540 }}>{p.name}</span>
                  </td>
                  <td className="mono muted">{p.version}</td>
                  <td className="mono muted">{p.latest ?? "—"}</td>
                  <td>
                    <Badge tone={p.is_direct ? "accent" : "neutral"}>{p.is_direct ? "direct" : "transitive"}</Badge>
                  </td>
                  <td><UpdateBadge type={p.update_type} /></td>
                  <td><LicenseBadge verdict={p.license_verdict} family={p.license_family} /></td>
                  <td>
                    {(p.vuln_count ?? 0) > 0 ? (
                      <Badge tone={p.max_severity === "critical" ? "crit" : p.max_severity === "high" ? "danger" : "warn"}>
                        {p.vuln_count} · {p.max_severity}
                      </Badge>
                    ) : (
                      <span className="muted">—</span>
                    )}
                  </td>
                  <td>{p.is_direct ? <UsageBadge status={p.usage_status} /> : <span className="muted">n/a</span>}</td>
                  <td><MaintenanceBadge status={p.maintenance_status} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {selected && <PackageDrawer scanId={currentScanId} name={selected} onClose={() => setSelected(null)} />}
    </>
  );
}
