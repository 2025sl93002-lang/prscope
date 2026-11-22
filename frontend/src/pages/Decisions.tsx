import { useState } from "react";
import { CheckCircle2, Circle, CircleSlash, MinusCircle, Plus, Trash2 } from "lucide-react";
import { api } from "../api/client";
import { useApp } from "../state/app";
import { useAsync } from "../hooks/useAsync";
import { Badge, Button, Card, EmptyState, Skeleton, useToast } from "../components/ui";
import { NoScan } from "../components/Layout";
import type { Decision, VerificationTask } from "../api/types";
import { relativeTime } from "../lib/format";

const TASK_STATES: VerificationTask["status"][] = ["pending", "complete", "blocked", "not-applicable"];
const TASK_ICON = {
  pending: <Circle size={15} />,
  complete: <CheckCircle2 size={15} color="var(--ok)" />,
  blocked: <CircleSlash size={15} color="var(--danger)" />,
  "not-applicable": <MinusCircle size={15} color="var(--text-3)" />,
};

export function Decisions() {
  const { currentProjectId } = useApp();
  const toast = useToast();
  const { data, loading, reload } = useAsync(
    () => (currentProjectId ? api.decisions(currentProjectId) : Promise.resolve(null)),
    [currentProjectId],
  );
  if (!currentProjectId) return <NoScan>Select or scan a project to record decisions.</NoScan>;
  if (loading) return <Skeleton h={300} />;
  const decisions = data?.decisions ?? [];

  async function save(d: Decision, patch: Partial<Decision>) {
    await api.updateDecision(d.id, { ...d, ...patch });
    reload();
  }
  async function remove(id: number) {
    await api.deleteDecision(id);
    toast.push("success", "Decision deleted.");
    reload();
  }

  return (
    <>
      <div className="page-head">
        <div>
          <h2>Decision Workspace</h2>
          <p>Every dependency decision, with evidence and a verification trail. Stored locally.</p>
        </div>
      </div>
      {decisions.length === 0 ? (
        <EmptyState title="No decisions recorded yet">
          Run an impact simulation and click “Record decision” to capture the action, its evidence,
          and a verification checklist here.
        </EmptyState>
      ) : (
        <div className="col" style={{ gap: "var(--sp-4)" }}>
          {decisions.map((d) => (
            <DecisionCard key={d.id} d={d} onSave={save} onDelete={remove} />
          ))}
        </div>
      )}
    </>
  );
}

function DecisionCard({
  d,
  onSave,
  onDelete,
}: {
  d: Decision;
  onSave: (d: Decision, patch: Partial<Decision>) => void;
  onDelete: (id: number) => void;
}) {
  const [newTask, setNewTask] = useState("");
  const done = d.verification.filter((t) => t.status === "complete").length;
  const total = d.verification.length;
  const statusTone = d.status === "verified" ? "ok" : d.status === "blocked" ? "danger" : "neutral";

  function cycleTask(i: number) {
    const tasks = [...d.verification];
    const cur = TASK_STATES.indexOf(tasks[i].status);
    tasks[i] = { ...tasks[i], status: TASK_STATES[(cur + 1) % TASK_STATES.length] };
    onSave(d, { verification: tasks });
  }
  function addTask() {
    if (!newTask.trim()) return;
    onSave(d, { verification: [...d.verification, { text: newTask.trim(), status: "pending" }] });
    setNewTask("");
  }

  return (
    <Card className="card-pad">
      <div className="row spread wrap" style={{ gap: 10 }}>
        <div className="row" style={{ gap: 10 }}>
          <Badge tone="accent">{d.action}</Badge>
          <span className="mono" style={{ fontWeight: 560 }}>{d.package}</span>
          {d.current_version && <span className="muted mono">{d.current_version}</span>}
          {d.proposed_version && <span className="mono">→ {d.proposed_version}</span>}
        </div>
        <div className="row" style={{ gap: 8 }}>
          <select className="select" style={{ width: "auto", height: 30 }} value={d.status} onChange={(e) => onSave(d, { status: e.target.value })}>
            <option value="open">Open</option>
            <option value="in-progress">In progress</option>
            <option value="verified">Verified</option>
            <option value="blocked">Blocked</option>
            <option value="done">Done</option>
          </select>
          <Button size="sm" variant="danger" icon onClick={() => onDelete(d.id)} aria-label="Delete"><Trash2 size={15} /></Button>
        </div>
      </div>

      {d.reason && <p className="dim" style={{ fontSize: "var(--text-sm)", margin: "10px 0 0" }}>{d.reason}</p>}

      <div className="row" style={{ gap: 10, marginTop: 12 }}>
        <Badge tone={statusTone as any}>{d.status}</Badge>
        {total > 0 && <Badge tone={done === total ? "ok" : "neutral"}>{done}/{total} verified</Badge>}
        <span className="muted" style={{ fontSize: "var(--text-xs)" }}>updated {relativeTime(d.updated_at)}</span>
      </div>

      <div className="col" style={{ gap: 2, marginTop: 12 }}>
        {d.verification.map((t, i) => (
          <button key={i} className="row" style={{ gap: 10, background: "none", border: "none", cursor: "pointer", padding: "5px 0", textAlign: "left", color: "inherit" }} onClick={() => cycleTask(i)}>
            <span style={{ flex: "none" }}>{TASK_ICON[t.status]}</span>
            <span style={{ fontSize: "var(--text-sm)", textDecoration: t.status === "complete" ? "line-through" : "none", color: t.status === "complete" ? "var(--text-3)" : "var(--text-1)" }}>
              {t.text}
            </span>
          </button>
        ))}
      </div>
      <div className="row" style={{ gap: 6, marginTop: 10 }}>
        <input className="input" style={{ height: 32 }} placeholder="Add a verification task…" value={newTask} onChange={(e) => setNewTask(e.target.value)} onKeyDown={(e) => e.key === "Enter" && addTask()} />
        <Button size="sm" onClick={addTask}><Plus size={14} /> Add</Button>
      </div>
    </Card>
  );
}
