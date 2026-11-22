import { useEffect, useRef, useState } from "react";
import {
  CheckCircle2,
  CircleDashed,
  FolderSearch,
  MinusCircle,
  XCircle,
} from "lucide-react";
import { api } from "../api/client";
import type { Stage } from "../api/types";
import { Button, Dialog, Spinner, useToast } from "./ui";

const STAGE_LABELS = [
  "Discovering project",
  "Reading manifests",
  "Resolving dependency graph",
  "Analyzing versions & metadata",
  "Checking security advisories",
  "Analyzing licenses",
  "Checking package usage",
  "Generating health findings",
  "Preparing report",
];

function StageIcon({ status }: { status: Stage["status"] }) {
  if (status === "ok") return <CheckCircle2 size={16} color="var(--ok)" />;
  if (status === "partial") return <CheckCircle2 size={16} color="var(--warn)" />;
  if (status === "skipped") return <MinusCircle size={16} color="var(--text-3)" />;
  if (status === "failed") return <XCircle size={16} color="var(--danger)" />;
  return <CircleDashed size={16} color="var(--text-3)" />;
}

export function ScanModal({
  onClose,
  onDone,
}: {
  onClose: () => void;
  onDone: (scanId: number, projectId: number) => void;
}) {
  const [path, setPath] = useState("");
  const [online, setOnline] = useState(true);
  const [running, setRunning] = useState(false);
  const [stages, setStages] = useState<Stage[] | null>(null);
  const [tick, setTick] = useState(0);
  const toast = useToast();
  const timer = useRef<number>();

  useEffect(() => {
    api.demoPath().then((d) => d.exists && setPath((p) => p || d.path)).catch(() => {});
  }, []);

  useEffect(() => {
    if (running) {
      timer.current = window.setInterval(() => setTick((t) => Math.min(t + 1, STAGE_LABELS.length - 1)), 650);
    }
    return () => clearInterval(timer.current);
  }, [running]);

  async function run() {
    if (!path.trim()) {
      toast.push("error", "Enter a project path to scan.");
      return;
    }
    setRunning(true);
    setStages(null);
    setTick(0);
    try {
      const { scan_id, project_id } = await api.scan(path.trim(), online);
      const detail = await api.scanDetail(scan_id);
      setStages(detail.stages);
      clearInterval(timer.current);
      toast.push("success", `Scan complete — ${detail.summary.total} dependencies analyzed.`);
      setTimeout(() => onDone(scan_id, project_id), 700);
    } catch (e: any) {
      setRunning(false);
      clearInterval(timer.current);
      toast.push("error", e?.message ?? "Scan failed.");
    }
  }

  return (
    <Dialog onClose={running ? () => {} : onClose}>
      <div className="scan-modal">
        <h2>Scan a project</h2>
        <p className="muted" style={{ marginTop: 0, marginBottom: "var(--sp-4)" }}>
          Point DepLens at a local npm project folder (one containing{" "}
          <code>package.json</code>). Your source code never leaves your machine.
        </p>

        {!running && (
          <>
            <label className="field" style={{ marginBottom: "var(--sp-4)" }}>
              <span>Project path</span>
              <div className="field-wrap">
                <FolderSearch size={16} />
                <input
                  className="input input-search"
                  value={path}
                  placeholder="/path/to/your/npm/project"
                  onChange={(e) => setPath(e.target.value)}
                  spellCheck={false}
                />
              </div>
            </label>
            <label className="row" style={{ marginBottom: "var(--sp-5)", cursor: "pointer" }}>
              <input type="checkbox" checked={online} onChange={(e) => setOnline(e.target.checked)} />
              <span className="col">
                <span>Online analysis</span>
                <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
                  Query the npm registry and OSV.dev for versions, licenses and advisories.
                  Only package names and versions are sent. Uncheck for fully offline analysis.
                </span>
              </span>
            </label>
            <div className="row spread">
              <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
                The bundled demo fixture is pre-filled.
              </span>
              <div className="row">
                <Button variant="ghost" onClick={onClose}>
                  Cancel
                </Button>
                <Button variant="primary" onClick={run}>
                  Start scan
                </Button>
              </div>
            </div>
          </>
        )}

        {running && (
          <div className="stage-list">
            {(stages ?? STAGE_LABELS.map((label, i) => ({
              key: String(i),
              label,
              status: (i < tick ? "ok" : i === tick ? "pending" : "pending") as Stage["status"],
              detail: "",
              duration_ms: 0,
            }))).map((s, i) => {
              const live = !stages && i === tick;
              return (
                <div key={s.key} className={`stage ${live ? "running" : ""}`}>
                  <span className="stage-icon">{live ? <Spinner /> : <StageIcon status={s.status} />}</span>
                  <span>{s.label}</span>
                  {s.detail && <span className="stage-detail">{s.detail}</span>}
                  {s.status && stages && (
                    <span className="stage-detail">
                      {s.duration_ms}ms
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </Dialog>
  );
}
