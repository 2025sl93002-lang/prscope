import { useEffect, useState } from "react";
import { AlertTriangle, Check, Copy, Download, FileWarning, Terminal } from "lucide-react";
import { api } from "../api/client";
import { Badge, Button, Dialog, Spinner, useToast } from "./ui";
import type { FixEdit } from "../api/types";

function DiffView({ diff }: { diff: string }) {
  return (
    <pre
      className="mono"
      style={{
        margin: 0,
        fontSize: "var(--text-xs)",
        lineHeight: 1.55,
        maxHeight: 320,
        overflow: "auto",
        background: "var(--surface-2)",
        borderRadius: "var(--radius-md)",
        padding: "var(--sp-3)",
      }}
    >
      {diff.split("\n").map((line, i) => {
        let color = "var(--text-2)";
        if (line.startsWith("+") && !line.startsWith("+++")) color = "var(--ok)";
        else if (line.startsWith("-") && !line.startsWith("---")) color = "var(--danger)";
        else if (line.startsWith("@@")) color = "var(--accent-text)";
        return (
          <div key={i} style={{ color, whiteSpace: "pre-wrap" }}>
            {line || " "}
          </div>
        );
      })}
    </pre>
  );
}

export function ApplyFixDialog({
  scanId,
  packages,
  onClose,
  onApplied,
}: {
  scanId: number;
  packages?: string[];
  onClose: () => void;
  onApplied?: () => void;
}) {
  const [edit, setEdit] = useState<FixEdit | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [copied, setCopied] = useState<string | null>(null);
  const [confirmWrite, setConfirmWrite] = useState(false);
  const [writing, setWriting] = useState(false);
  const toast = useToast();

  useEffect(() => {
    api
      .fixPlan(scanId, packages)
      .then(setEdit)
      .catch((e) => setError(e?.message ?? "Could not compute the fix."));
  }, [scanId, packages]);

  function copy(text: string, label: string) {
    navigator.clipboard?.writeText(text);
    setCopied(label);
    setTimeout(() => setCopied(null), 1500);
    toast.push("success", `${label} copied.`);
  }

  function download() {
    if (!edit) return;
    const blob = new Blob([edit.new_content], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "package.json";
    a.click();
    URL.revokeObjectURL(url);
  }

  async function write() {
    setWriting(true);
    try {
      const result = await api.fixApply(scanId, packages);
      setEdit(result);
      toast.push("success", "package.json updated. Run npm install to apply.");
      onApplied?.();
    } catch (e: any) {
      toast.push("error", e?.message ?? "Write failed.");
    } finally {
      setWriting(false);
      setConfirmWrite(false);
    }
  }

  return (
    <Dialog onClose={onClose}>
      <div style={{ padding: "var(--sp-5)", maxWidth: 680 }}>
        <h2 style={{ fontSize: "var(--text-xl)", marginBottom: 4 }}>Apply fix</h2>
        <p className="muted" style={{ marginTop: 0 }}>
          DepLens edits <span className="mono">package.json</span> only — it never runs{" "}
          <span className="mono">npm install</span> (that would execute lifecycle scripts). You run
          the install yourself.
        </p>

        {error && (
          <div className="row" style={{ gap: 8, color: "var(--danger)" }}>
            <AlertTriangle size={16} /> {error}
          </div>
        )}
        {!edit && !error && (
          <div className="row" style={{ gap: 8 }}>
            <Spinner /> Computing changes…
          </div>
        )}

        {edit && (
          <>
            {edit.changes.length === 0 ? (
              <p className="muted">No applicable changes.</p>
            ) : (
              <>
                <div className="col" style={{ gap: 6, margin: "var(--sp-4) 0" }}>
                  {edit.changes.map((c) => (
                    <div key={c.package} className="row spread" style={{ fontSize: "var(--text-sm)" }}>
                      <span className="mono">{c.package}</span>
                      <span className="row" style={{ gap: 8 }}>
                        {c.from_spec && <span className="muted mono">{c.from_spec} →</span>}
                        <span className="mono" style={{ color: "var(--ok)" }}>{c.to_spec}</span>
                        <Badge tone={c.kind === "override" ? "warn" : "accent"}>
                          {c.kind === "override" ? "overrides" : c.field}
                        </Badge>
                      </span>
                    </div>
                  ))}
                </div>

                {edit.warnings.map((w, i) => (
                  <div key={i} className="row" style={{ gap: 7, color: "var(--warn)", fontSize: "var(--text-xs)", marginBottom: 6 }}>
                    <FileWarning size={13} /> {w}
                  </div>
                ))}

                <DiffView diff={edit.diff} />

                <div
                  className="row"
                  style={{ gap: 8, margin: "var(--sp-3) 0", padding: "var(--sp-3)", background: "var(--surface-2)", borderRadius: "var(--radius-md)" }}
                >
                  <Terminal size={15} className="muted" />
                  <span className="mono" style={{ fontSize: "var(--text-sm)" }}>{edit.install_command}</span>
                  <Button size="sm" variant="ghost" onClick={() => copy(edit.install_command, "Command")}>
                    <Copy size={13} />
                  </Button>
                </div>

                {edit.written && (
                  <div className="row" style={{ gap: 8, color: "var(--ok)", fontSize: "var(--text-sm)", marginBottom: 8 }}>
                    <Check size={15} /> Written. Backup saved to{" "}
                    <span className="mono">{edit.backup_path?.split("/").pop()}</span>. Now run{" "}
                    <span className="mono">{edit.install_command}</span>.
                  </div>
                )}

                <div className="row spread wrap" style={{ gap: 8, marginTop: "var(--sp-4)" }}>
                  <div className="row" style={{ gap: 8 }}>
                    <Button variant="secondary" onClick={() => copy(edit.diff, "Diff")}>
                      {copied === "Diff" ? <Check size={15} /> : <Copy size={15} />} Copy diff
                    </Button>
                    <Button variant="secondary" onClick={() => copy(edit.new_content, "package.json")}>
                      <Copy size={15} /> Copy file
                    </Button>
                    <Button variant="ghost" onClick={download}>
                      <Download size={15} /> Download
                    </Button>
                  </div>
                  {!edit.written &&
                    (confirmWrite ? (
                      <div className="row" style={{ gap: 6 }}>
                        <span className="muted" style={{ fontSize: "var(--text-xs)" }}>Overwrite the file?</span>
                        <Button variant="ghost" size="sm" onClick={() => setConfirmWrite(false)}>Cancel</Button>
                        <Button variant="primary" size="sm" onClick={write} disabled={writing}>
                          {writing ? <Spinner /> : "Confirm write"}
                        </Button>
                      </div>
                    ) : (
                      <Button variant="primary" onClick={() => setConfirmWrite(true)}>
                        Write to package.json
                      </Button>
                    ))}
                </div>
              </>
            )}
          </>
        )}
      </div>
    </Dialog>
  );
}
