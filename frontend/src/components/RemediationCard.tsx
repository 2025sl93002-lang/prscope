import { useState } from "react";
import { ArrowUpCircle, CheckCircle2, ChevronDown, Wrench, Zap } from "lucide-react";
import { useAsync } from "../hooks/useAsync";
import { api } from "../api/client";
import { Badge, Button, Card, CardHead, Skeleton } from "./ui";
import { ApplyFixDialog } from "./ApplyFixDialog";
import { UpdateBadge } from "../lib/badges";
import type { RemediationAction } from "../api/types";

const SEV_TONE: Record<string, "crit" | "danger" | "warn" | "info" | "neutral"> = {
  critical: "crit",
  high: "danger",
  moderate: "warn",
  low: "info",
  unknown: "neutral",
};

export function RemediationCard({ scanId }: { scanId: number }) {
  const { data, loading } = useAsync(() => api.remediation(scanId), [scanId]);
  const [open, setOpen] = useState(true);
  const [applyPackages, setApplyPackages] = useState<string[] | null>(null);
  const [showApply, setShowApply] = useState(false);

  if (loading) return <Skeleton h={120} />;
  if (!data || data.total_advisories === 0) return null;

  const openApply = (packages?: string[]) => {
    setApplyPackages(packages ?? null);
    setShowApply(true);
  };

  return (
    <Card>
      <CardHead
        title={
          <span className="row" style={{ gap: 8 }}>
            <Wrench size={16} color="var(--accent)" /> Remediation plan
          </span>
        }
        subtitle={data.summary}
        actions={
          <div className="row" style={{ gap: 6 }}>
            {data.packages_to_upgrade > 0 && (
              <Button size="sm" variant="primary" onClick={() => openApply(undefined)}>
                Apply all fixes
              </Button>
            )}
            <button
              className="btn btn-ghost btn-sm btn-icon"
              onClick={() => setOpen((v) => !v)}
              aria-expanded={open}
              aria-label="Toggle"
            >
              <ChevronDown
                size={16}
                style={{ transform: open ? "rotate(180deg)" : "none", transition: "transform 140ms" }}
              />
            </button>
          </div>
        }
      />
      <div className="card-pad" style={{ paddingTop: "var(--sp-3)" }}>
        <div className="row wrap" style={{ gap: "var(--sp-2)", marginBottom: "var(--sp-4)" }}>
          <Badge tone="ok">
            <CheckCircle2 /> {data.fixable_advisories}/{data.total_advisories} fixable
          </Badge>
          <Badge tone="accent">{data.packages_to_upgrade} upgrades</Badge>
          {data.quick_wins > 0 && (
            <Badge tone="info">
              <Zap /> {data.quick_wins} quick wins
            </Badge>
          )}
          {data.unfixable_advisories > 0 && (
            <Badge tone="neutral">{data.unfixable_advisories} no fix yet</Badge>
          )}
        </div>
        {open && (
          <div className="col" style={{ gap: "var(--sp-2)" }}>
            {data.actions.map((a) => (
              <ActionRow key={a.package} a={a} onApply={() => openApply([a.package])} />
            ))}
          </div>
        )}
      </div>
      {showApply && (
        <ApplyFixDialog
          scanId={scanId}
          packages={applyPackages ?? undefined}
          onClose={() => setShowApply(false)}
        />
      )}
    </Card>
  );
}

function ActionRow({ a, onApply }: { a: RemediationAction; onApply: () => void }) {
  return (
    <div
      className="card"
      style={{ padding: "var(--sp-3) var(--sp-4)", boxShadow: "none", background: "var(--surface-2)" }}
    >
      <div className="row spread wrap" style={{ gap: 8 }}>
        <div className="row" style={{ gap: 10, flexWrap: "wrap" }}>
          {a.quick_win && (
            <span title="Low-risk upgrade clearing a high/critical advisory">
              <Zap size={15} color="var(--info)" />
            </span>
          )}
          <span className="mono" style={{ fontWeight: 560 }}>
            {a.package}
          </span>
          {a.target_version ? (
            <span className="mono" style={{ fontSize: "var(--text-sm)" }}>
              <span className="muted">{a.current_version}</span>{" "}
              <ArrowUpCircle size={12} style={{ verticalAlign: "-2px" }} /> {a.target_version}
            </span>
          ) : (
            <Badge tone="neutral">no fixed release</Badge>
          )}
          {a.update_type && <UpdateBadge type={a.update_type} />}
        </div>
        <div className="row" style={{ gap: 6 }}>
          <Badge tone={SEV_TONE[a.max_severity_cleared] ?? "neutral"}>
            clears {a.cleared.length}
          </Badge>
          {a.strategy === "transitive" && (
            <Badge tone="warn">via {a.via_direct.join(", ") || "parent"}</Badge>
          )}
          {a.strategy === "direct" && <Badge tone="accent">direct</Badge>}
          {a.target_version && (
            <Button size="sm" variant="ghost" onClick={onApply}>
              Apply
            </Button>
          )}
        </div>
      </div>
      {a.strategy === "transitive" && (
        <p className="muted" style={{ fontSize: "var(--text-xs)", margin: "6px 0 0" }}>
          Transitive — bump{" "}
          <span className="mono">{a.via_direct.join(" / ") || "the parent"}</span>, or pin with an
          npm <span className="mono">overrides</span> entry.
        </p>
      )}
      {a.unfixable.length > 0 && (
        <p className="muted" style={{ fontSize: "var(--text-xs)", margin: "6px 0 0" }}>
          {a.unfixable.length} advisory(ies) for this package have no fixed release yet.
        </p>
      )}
    </div>
  );
}
