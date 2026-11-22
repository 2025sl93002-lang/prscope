import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { FolderGit2, Plus, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { Badge, Button, Card, EmptyState, useToast } from "../components/ui";
import { ScanModal } from "../components/ScanModal";
import { relativeTime } from "../lib/format";
import { gradeTone } from "../lib/badges";

export function Projects() {
  const { projects, setCurrentProject, setCurrentScan, refreshProjects, currentProjectId } = useApp();
  const [scanOpen, setScanOpen] = useState(false);
  const toast = useToast();
  const navigate = useNavigate();

  async function remove(id: number, name: string) {
    if (!confirm(`Remove "${name}" from DepLens? This deletes its scans and decisions locally (your project files are untouched).`)) return;
    await api.deleteProject(id);
    toast.push("success", `Removed ${name}.`);
    await refreshProjects();
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Projects</h2>
          <p>Local npm projects you've scanned. Source never leaves your machine.</p>
        </div>
        <Button variant="primary" onClick={() => setScanOpen(true)}>
          <Plus size={16} /> Scan a project
        </Button>
      </div>

      {projects.length === 0 ? (
        <EmptyState icon={<FolderGit2 />} title="No projects yet">
          Scan a local npm project (a folder with a <code>package.json</code>) to get started. The
          bundled demo fixture is pre-filled in the scan dialog.
        </EmptyState>
      ) : (
        <div className="grid-3">
          {projects.map((p) => (
            <Card key={p.id} className="card-pad">
              <div className="row spread" style={{ alignItems: "flex-start" }}>
                <div className="col" style={{ gap: 4, minWidth: 0 }}>
                  <strong style={{ fontSize: "var(--text-md)" }}>{p.name}</strong>
                  <span className="muted mono" style={{ fontSize: "var(--text-xs)", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} title={p.path}>
                    {p.path}
                  </span>
                </div>
                {p.last_scan?.health_grade && (
                  <div style={{ fontSize: "var(--text-xl)", fontWeight: 700, color: gradeTone(p.last_scan.health_grade) }}>
                    {p.last_scan.health_grade}
                  </div>
                )}
              </div>
              <div className="row wrap" style={{ gap: 6, margin: "var(--sp-3) 0" }}>
                <Badge tone="neutral">{p.ecosystem}</Badge>
                <Badge tone={currentProjectId === p.id ? "accent" : "neutral"}>
                  {currentProjectId === p.id ? "selected" : "scanned"}
                </Badge>
                <span className="muted" style={{ fontSize: "var(--text-xs)" }}>
                  {p.last_scan ? `scanned ${relativeTime(p.last_scan.created_at)}` : "never scanned"}
                </span>
              </div>
              <div className="row spread">
                <Button
                  size="sm"
                  variant="primary"
                  onClick={() => {
                    setCurrentProject(p.id);
                    if (p.last_scan) setCurrentScan(p.last_scan.id);
                    navigate("/");
                  }}
                >
                  Open
                </Button>
                <Button size="sm" variant="danger" icon onClick={() => remove(p.id, p.name)} aria-label="Remove">
                  <Trash2 size={15} />
                </Button>
              </div>
            </Card>
          ))}
        </div>
      )}

      {scanOpen && (
        <ScanModal
          onClose={() => setScanOpen(false)}
          onDone={async (scanId, projectId) => {
            await refreshProjects();
            setCurrentProject(projectId);
            setCurrentScan(scanId);
            setScanOpen(false);
            navigate("/");
          }}
        />
      )}
    </>
  );
}
