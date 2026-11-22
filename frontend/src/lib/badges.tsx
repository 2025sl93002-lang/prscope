import {
  ArrowUpCircle,
  CircleSlash,
  FileQuestion,
  PackageCheck,
  ScanSearch,
  ShieldCheck,
} from "lucide-react";
import { Badge } from "../components/ui";
import type {
  LicenseVerdict,
  MaintenanceStatus,
  UpdateType,
  UsageStatus,
} from "../api/types";

export function UpdateBadge({ type }: { type: UpdateType | null }) {
  if (!type || type === "unknown")
    return (
      <Badge tone="neutral">
        <FileQuestion /> Unknown
      </Badge>
    );
  if (type === "up-to-date")
    return (
      <Badge tone="ok">
        <PackageCheck /> Up to date
      </Badge>
    );
  const tone = type === "major" ? "danger" : type === "minor" ? "warn" : "info";
  const label =
    type === "major"
      ? "Major"
      : type === "minor"
        ? "Minor"
        : type === "patch"
          ? "Patch"
          : "Prerelease";
  return (
    <Badge tone={tone}>
      <ArrowUpCircle /> {label}
    </Badge>
  );
}

export function LicenseBadge({
  verdict,
  family,
}: {
  verdict: LicenseVerdict | null;
  family?: string | null;
}) {
  const label = family ? family.replace(/-/g, " ") : verdict ?? "unknown";
  if (verdict === "allowed") return <Badge tone="ok">{label}</Badge>;
  if (verdict === "restricted") return <Badge tone="danger">{label}</Badge>;
  if (verdict === "review") return <Badge tone="warn">{label}</Badge>;
  return <Badge tone="neutral">{label}</Badge>;
}

const USAGE_META: Record<
  UsageStatus,
  { tone: "ok" | "warn" | "danger" | "neutral"; label: string; icon: JSX.Element }
> = {
  confirmed: { tone: "ok", label: "Used", icon: <ShieldCheck /> },
  potential: { tone: "warn", label: "Possibly used", icon: <ScanSearch /> },
  none: { tone: "danger", label: "No usage found", icon: <CircleSlash /> },
  incomplete: { tone: "neutral", label: "Not analyzed", icon: <FileQuestion /> },
};

export function UsageBadge({ status }: { status: UsageStatus | null }) {
  if (!status) return <Badge tone="neutral">—</Badge>;
  const m = USAGE_META[status];
  return (
    <Badge tone={m.tone}>
      {m.icon} {m.label}
    </Badge>
  );
}

const MAINT_META: Record<MaintenanceStatus, { tone: "ok" | "warn" | "danger" | "neutral"; label: string }> = {
  active: { tone: "ok", label: "Active" },
  "low-activity": { tone: "warn", label: "Low activity" },
  concerns: { tone: "warn", label: "Concerns" },
  deprecated: { tone: "danger", label: "Deprecated" },
  unknown: { tone: "neutral", label: "Unknown" },
};

export function MaintenanceBadge({ status }: { status: MaintenanceStatus | null }) {
  if (!status) return <Badge tone="neutral">—</Badge>;
  const m = MAINT_META[status];
  return <Badge tone={m.tone}>{m.label}</Badge>;
}

export function gradeTone(grade: string | null): string {
  switch (grade) {
    case "A":
      return "var(--ok)";
    case "B":
      return "var(--ok)";
    case "C":
      return "var(--warn)";
    case "D":
      return "var(--warn)";
    default:
      return "var(--danger)";
  }
}
