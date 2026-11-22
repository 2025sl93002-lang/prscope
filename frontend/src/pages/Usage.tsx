import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Badge, Button, Card, Skeleton, useToast } from "../components/ui";
import { NoScan } from "../components/Layout";
import { UsageBadge } from "../lib/badges";

export function Usage() {
  const { currentScanId, currentProjectId } = useApp();
  const toast = useToast();
  const { data, loading, reload } = useAsync(
    () => (currentScanId ? api.usage(currentScanId) : Promise.resolve(null)),
    [currentScanId],
  );
  if (!currentScanId) return <NoScan />;
  if (loading) return <Skeleton h={400} />;
  if (!data) return null;

  async function override(pkg: string, state: string) {
    if (!currentProjectId) return;
    await api.setUsageOverride(currentProjectId, { package: pkg, state });
    toast.push("success", state === "cleared" ? "Override cleared." : `Marked ${pkg} as ${state}.`);
    reload();
  }

  const sorted = [...data.usage].sort((a, b) => {
    const rank = { none: 0, potential: 1, incomplete: 2, confirmed: 3 } as Record<string, number>;
    return (rank[a.status] ?? 9) - (rank[b.status] ?? 9);
  });

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Usage Analysis</h2>
          <p>Evidence-based. DepLens never claims a package is unused with certainty.</p>
        </div>
      </div>

      <div className="col" style={{ gap: "var(--sp-4)" }}>
        {sorted.map((u) => (
          <Card key={u.package} className="card-pad">
            <div className="row spread wrap" style={{ gap: 8 }}>
              <div className="row" style={{ gap: 10 }}>
                <span className="mono" style={{ fontWeight: 560 }}>{u.package}</span>
                <span className="muted mono" style={{ fontSize: "var(--text-xs)" }}>{u.version}</span>
                <UsageBadge status={u.status} />
                {u.confidence && <Badge tone="neutral">{u.confidence} confidence</Badge>}
                {u.override && <Badge tone="accent">marked {u.override.state}</Badge>}
              </div>
              {(u.status === "none" || u.status === "potential") && (
                <div className="row" style={{ gap: 6 }}>
                  {u.override ? (
                    <Button size="sm" variant="ghost" onClick={() => override(u.package, "cleared")}>Clear</Button>
                  ) : (
                    <>
                      <Button size="sm" variant="secondary" onClick={() => override(u.package, "intentional")}>Mark intentional</Button>
                      <Button size="sm" variant="ghost" onClick={() => override(u.package, "dismissed")}>Dismiss</Button>
                    </>
                  )}
                </div>
              )}
            </div>
            <p className="dim" style={{ fontSize: "var(--text-sm)", margin: "10px 0 0" }}>{u.explanation}</p>
            {u.evidence.length > 0 && (
              <div className="col" style={{ gap: 3, marginTop: 8 }}>
                {u.evidence.slice(0, 5).map((e, i) => (
                  <div key={i} className="mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-2)" }}>
                    {e.file}{e.line ? `:${e.line}` : ""} <span className="muted">({e.method})</span>
                  </div>
                ))}
              </div>
            )}
          </Card>
        ))}
      </div>
    </>
  );
}
