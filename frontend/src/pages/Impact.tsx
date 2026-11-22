import { useEffect, useMemo, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { AlertTriangle, FlaskConical, Info, ShieldAlert } from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Badge, Button, Card, CardHead, EmptyState, Spinner, useToast } from "../components/ui";
import { NoScan } from "../components/Layout";
import type { ImpactReport } from "../api/types";

const ACTIONS = [
  { key: "upgrade", label: "Upgrade" },
  { key: "remove", label: "Remove" },
  { key: "replace", label: "Replace" },
  { key: "keep", label: "Keep current" },
];

const EV_LABEL: Record<string, string> = {
  lockfile: "From lockfile",
  static: "Static analysis",
  potential: "Potential",
  unknown: "Unknown",
};

export function Impact() {
  const { currentScanId, currentProjectId } = useApp();
  const [params] = useSearchParams();
  const toast = useToast();
  const navigate = useNavigate();

  const [pkg, setPkg] = useState(params.get("package") ?? "");
  const [action, setAction] = useState("upgrade");
  const [proposed, setProposed] = useState("");
  const [alternative, setAlternative] = useState("");
  const [report, setReport] = useState<ImpactReport | null>(null);
  const [running, setRunning] = useState(false);

  const { data: pkgList } = useAsync(
    () => (currentScanId ? api.packages(currentScanId, {}) : Promise.resolve(null)),
    [currentScanId],
  );
  const names = useMemo(() => (pkgList?.packages ?? []).map((p) => p.name), [pkgList]);

  useEffect(() => {
    setReport(null);
  }, [pkg, action]);

  if (!currentScanId) return <NoScan />;

  async function run() {
    if (!pkg) return toast.push("error", "Choose a package to simulate.");
    if (action === "upgrade" && !proposed) return toast.push("error", "Enter a proposed version.");
    if (action === "replace" && !alternative) return toast.push("error", "Enter an alternative package.");
    setRunning(true);
    try {
      const r = await api.impact(currentScanId!, {
        package: pkg,
        action,
        proposed_version: proposed || undefined,
        alternative: alternative || undefined,
        online: true,
      });
      setReport(r);
    } catch (e: any) {
      toast.push("error", e?.message ?? "Simulation failed.");
    } finally {
      setRunning(false);
    }
  }

  async function recordDecision() {
    if (!report || !currentProjectId) return;
    await api.createDecision(currentProjectId, {
      package: report.package,
      current_version: report.current_version,
      action: report.action,
      proposed_version: report.proposed_version,
      decision: report.action,
      reason: report.summary,
      impact: report,
      verification: report.verification.map((t) => ({ text: t, status: "pending" })),
    });
    toast.push("success", "Decision recorded with a verification checklist.");
    navigate("/decisions");
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Impact Simulator</h2>
          <p>Model a change before you make it. Findings are evidence-labelled; nothing is assumed proven.</p>
        </div>
      </div>

      <Card className="card-pad">
        <div className="row wrap" style={{ gap: "var(--sp-4)", alignItems: "flex-end" }}>
          <label className="field" style={{ flex: "2 1 240px" }}>
            <span>Package</span>
            <input className="input" list="pkgs" value={pkg} onChange={(e) => setPkg(e.target.value)} placeholder="e.g. lodash" spellCheck={false} />
            <datalist id="pkgs">{names.map((n) => <option key={n} value={n} />)}</datalist>
          </label>
          <label className="field" style={{ flex: "1 1 160px" }}>
            <span>Action</span>
            <select className="select" value={action} onChange={(e) => setAction(e.target.value)}>
              {ACTIONS.map((a) => <option key={a.key} value={a.key}>{a.label}</option>)}
            </select>
          </label>
          {action === "upgrade" && (
            <label className="field" style={{ flex: "1 1 140px" }}>
              <span>Proposed version</span>
              <input className="input mono" value={proposed} onChange={(e) => setProposed(e.target.value)} placeholder="4.17.21" spellCheck={false} />
            </label>
          )}
          {action === "replace" && (
            <label className="field" style={{ flex: "1 1 160px" }}>
              <span>Alternative package</span>
              <input className="input mono" value={alternative} onChange={(e) => setAlternative(e.target.value)} placeholder="dayjs" spellCheck={false} />
            </label>
          )}
          <Button variant="primary" onClick={run} disabled={running}>
            {running ? <Spinner /> : <FlaskConical size={16} />} Run simulation
          </Button>
        </div>
      </Card>

      {!report && !running && (
        <EmptyState icon={<FlaskConical />} title="No simulation yet">
          Pick a package and an action, then run a simulation. Upgrade and remove analyses use the
          resolved lockfile graph and declared version ranges to find constraint conflicts, affected
          packages and files, and to generate a verification checklist.
        </EmptyState>
      )}

      {report && (
        <>
          <Card className="card-pad">
            <div className="row spread wrap">
              <div className="row" style={{ gap: 10 }}>
                <Badge tone="accent">{report.action}</Badge>
                <span className="mono" style={{ fontWeight: 560 }}>{report.package}</span>
                {report.current_version && <span className="muted mono">{report.current_version}</span>}
                {report.proposed_version && <span className="mono">→ {report.proposed_version}</span>}
                {report.alternative && <span className="mono">→ {report.alternative}</span>}
              </div>
              <Button variant="primary" onClick={recordDecision}>Record decision</Button>
            </div>
            <p style={{ marginBottom: 0 }}>{report.summary}</p>
          </Card>

          <div className="grid-2">
            <Card>
              <CardHead title="Findings" subtitle={`${report.findings.length} items`} />
              <div style={{ padding: "var(--sp-3)" }}>
                {report.findings.length === 0 && <p className="muted" style={{ padding: "0 var(--sp-2)" }}>No notable findings.</p>}
                {report.findings.map((f, i) => (
                  <div key={i} className="row" style={{ gap: 10, padding: "8px var(--sp-2)", alignItems: "flex-start" }}>
                    {f.severity === "critical" ? <ShieldAlert size={16} color="var(--danger)" style={{ flex: "none", marginTop: 2 }} /> : f.severity === "warning" ? <AlertTriangle size={16} color="var(--warn)" style={{ flex: "none", marginTop: 2 }} /> : <Info size={16} color="var(--info)" style={{ flex: "none", marginTop: 2 }} />}
                    <div className="col" style={{ gap: 2 }}>
                      <div className="row" style={{ gap: 7 }}>
                        <span style={{ fontSize: "var(--text-sm)" }}>{f.message}</span>
                      </div>
                      <div className="row" style={{ gap: 6 }}>
                        <Badge tone="neutral">{EV_LABEL[f.evidence] ?? f.evidence}</Badge>
                        {f.detail && <span className="muted mono" style={{ fontSize: "var(--text-xs)" }}>{f.detail}</span>}
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>

            <div className="col" style={{ gap: "var(--sp-5)" }}>
              <Card>
                <CardHead title="Verification checklist" subtitle="Generated for this change" />
                <div className="card-pad">
                  <ol style={{ margin: 0, paddingLeft: 18, display: "flex", flexDirection: "column", gap: 6 }}>
                    {report.verification.map((t, i) => (
                      <li key={i} style={{ fontSize: "var(--text-sm)" }}>{t}</li>
                    ))}
                  </ol>
                </div>
              </Card>
              {report.affected_files.length > 0 && (
                <Card className="card-pad">
                  <strong style={{ fontSize: "var(--text-sm)" }}>Affected source files ({report.affected_files.length})</strong>
                  <div className="col" style={{ gap: 2, marginTop: 8 }}>
                    {report.affected_files.map((f) => <span key={f} className="mono" style={{ fontSize: "var(--text-xs)", color: "var(--text-2)" }}>{f}</span>)}
                  </div>
                </Card>
              )}
              {report.limitations.length > 0 && (
                <Card className="card-pad">
                  <strong style={{ fontSize: "var(--text-sm)" }}>Limitations</strong>
                  <ul className="muted" style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: "var(--text-xs)" }}>
                    {report.limitations.map((l, i) => <li key={i}>{l}</li>)}
                  </ul>
                </Card>
              )}
            </div>
          </div>
        </>
      )}
    </>
  );
}
