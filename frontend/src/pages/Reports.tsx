import { useState } from "react";
import { Download, FileJson, FileText, Table } from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Button, Card, CardHead, Skeleton } from "../components/ui";
import { NoScan } from "../components/Layout";

export function Reports() {
  const { currentScanId } = useApp();
  const [preview, setPreview] = useState<string>("");
  const [loadingPreview, setLoadingPreview] = useState(false);
  const { data } = useAsync(
    () => (currentScanId ? api.scanDetail(currentScanId) : Promise.resolve(null)),
    [currentScanId],
  );
  if (!currentScanId) return <NoScan />;

  async function loadPreview() {
    setLoadingPreview(true);
    try {
      const res = await fetch(api.reportUrl(currentScanId!, "markdown"));
      setPreview(await res.text());
    } finally {
      setLoadingPreview(false);
    }
  }

  const formats = [
    { fmt: "markdown", label: "Markdown", icon: FileText, desc: "Human-readable report for reviews & PRs." },
    { fmt: "json", label: "JSON", icon: FileJson, desc: "Full structured data for tooling." },
    { fmt: "csv", label: "CSV", icon: Table, desc: "Dependency inventory for spreadsheets." },
  ];

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Reports</h2>
          <p>Export the current scan. Reports include limitations and data sources.</p>
        </div>
      </div>

      <div className="grid-3">
        {formats.map((f) => (
          <Card key={f.fmt} className="card-pad">
            <div className="row" style={{ gap: 10, marginBottom: 8 }}>
              <f.icon size={20} color="var(--accent)" />
              <strong>{f.label}</strong>
            </div>
            <p className="dim" style={{ fontSize: "var(--text-sm)", minHeight: 40 }}>{f.desc}</p>
            <a href={api.reportUrl(currentScanId, f.fmt)} download>
              <Button variant="secondary" style={{ width: "100%" }}><Download size={15} /> Download .{f.fmt === "markdown" ? "md" : f.fmt}</Button>
            </a>
          </Card>
        ))}
      </div>

      <Card>
        <CardHead
          title="Markdown preview"
          subtitle={data ? `${data.project.name} · scan #${data.id}` : ""}
          actions={<Button size="sm" onClick={loadPreview}>Generate preview</Button>}
        />
        <div className="card-pad">
          {loadingPreview ? (
            <Skeleton h={200} />
          ) : preview ? (
            <pre className="mono" style={{ whiteSpace: "pre-wrap", fontSize: "var(--text-xs)", margin: 0, maxHeight: 460, overflow: "auto", color: "var(--text-2)" }}>
              {preview}
            </pre>
          ) : (
            <p className="muted" style={{ margin: 0 }}>Click “Generate preview” to render the Markdown report.</p>
          )}
        </div>
      </Card>
    </>
  );
}
