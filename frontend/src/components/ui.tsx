import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  AlertTriangle,
  CheckCircle2,
  HelpCircle,
  Info,
  ShieldAlert,
  X,
} from "lucide-react";
import type { Severity } from "../api/types";
import "./ui.css";

export function Card({
  children,
  className = "",
}: {
  children: ReactNode;
  className?: string;
}) {
  return <div className={`card ${className}`}>{children}</div>;
}

export function CardHead({
  title,
  subtitle,
  actions,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  actions?: ReactNode;
}) {
  return (
    <div className="card-head">
      <div className="col">
        <span className="card-title">{title}</span>
        {subtitle && <span className="card-subtitle">{subtitle}</span>}
      </div>
      {actions}
    </div>
  );
}

type BtnVariant = "primary" | "secondary" | "ghost" | "danger";
export function Button({
  children,
  variant = "secondary",
  size,
  icon,
  ...props
}: {
  children?: ReactNode;
  variant?: BtnVariant;
  size?: "sm";
  icon?: boolean;
} & React.ButtonHTMLAttributes<HTMLButtonElement>) {
  return (
    <button
      className={`btn btn-${variant} ${size === "sm" ? "btn-sm" : ""} ${
        icon ? "btn-icon" : ""
      }`}
      {...props}
    >
      {children}
    </button>
  );
}

export function Badge({
  children,
  tone = "neutral",
}: {
  children: ReactNode;
  tone?: "neutral" | "ok" | "warn" | "danger" | "crit" | "info" | "accent";
}) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

const SEV_META: Record<
  Severity,
  { tone: "crit" | "danger" | "warn" | "info" | "neutral"; label: string }
> = {
  critical: { tone: "crit", label: "Critical" },
  high: { tone: "danger", label: "High" },
  moderate: { tone: "warn", label: "Moderate" },
  low: { tone: "info", label: "Low" },
  unknown: { tone: "neutral", label: "Unknown" },
};

export function SeverityBadge({ severity }: { severity: Severity }) {
  const m = SEV_META[severity] ?? SEV_META.unknown;
  return (
    <Badge tone={m.tone}>
      <ShieldAlert /> {m.label}
    </Badge>
  );
}

export function Skeleton({ h = 16, w = "100%" }: { h?: number; w?: number | string }) {
  return <div className="skeleton" style={{ height: h, width: w }} />;
}

export function Spinner() {
  return <span className="spinner" role="status" aria-label="Loading" />;
}

export function EmptyState({
  icon,
  title,
  children,
}: {
  icon?: ReactNode;
  title: string;
  children?: ReactNode;
}) {
  return (
    <div className="empty">
      {icon ?? <HelpCircle />}
      <h3>{title}</h3>
      {children && <div style={{ maxWidth: 380 }}>{children}</div>}
    </div>
  );
}

export function Tabs({
  tabs,
  active,
  onChange,
}: {
  tabs: { key: string; label: ReactNode }[];
  active: string;
  onChange: (k: string) => void;
}) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button
          key={t.key}
          role="tab"
          aria-selected={active === t.key}
          className={`tab ${active === t.key ? "active" : ""}`}
          onClick={() => onChange(t.key)}
        >
          {t.label}
        </button>
      ))}
    </div>
  );
}

export function Drawer({
  title,
  subtitle,
  onClose,
  children,
}: {
  title: ReactNode;
  subtitle?: ReactNode;
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <>
      <div className="drawer-overlay" onClick={onClose} />
      <aside className="drawer" role="dialog" aria-label={typeof title === "string" ? title : "Details"}>
        <div className="drawer-head">
          <div className="col">
            <h2 style={{ fontSize: "var(--text-lg)" }}>{title}</h2>
            {subtitle && <span className="muted" style={{ fontSize: "var(--text-sm)" }}>{subtitle}</span>}
          </div>
          <Button icon variant="ghost" onClick={onClose} aria-label="Close">
            <X size={18} />
          </Button>
        </div>
        <div className="drawer-body">{children}</div>
      </aside>
    </>
  );
}

export function Dialog({
  onClose,
  children,
}: {
  onClose: () => void;
  children: ReactNode;
}) {
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="dialog-overlay" onClick={onClose}>
      <div className="dialog" onClick={(e) => e.stopPropagation()} role="dialog">
        {children}
      </div>
    </div>
  );
}

export function Tooltip({ label, children }: { label: ReactNode; children: ReactNode }) {
  return (
    <span className="tip" tabIndex={0}>
      {children}
      <span className="tip-content" role="tooltip">
        {label}
      </span>
    </span>
  );
}

export function Meter({ value, tone = "accent" }: { value: number; tone?: string }) {
  const color =
    tone === "ok"
      ? "var(--ok)"
      : tone === "warn"
        ? "var(--warn)"
        : tone === "danger"
          ? "var(--danger)"
          : "var(--accent)";
  return (
    <div className="meter">
      <span style={{ width: `${Math.max(0, Math.min(100, value))}%`, background: color }} />
    </div>
  );
}

/* ---- Toast system ---- */
type Toast = { id: number; kind: "info" | "success" | "error"; message: string };
const ToastCtx = createContext<{ push: (kind: Toast["kind"], message: string) => void }>({
  push: () => {},
});
export const useToast = () => useContext(ToastCtx);

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([]);
  const push = useCallback((kind: Toast["kind"], message: string) => {
    const id = Date.now() + Math.random();
    setToasts((t) => [...t, { id, kind, message }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), 4200);
  }, []);
  return (
    <ToastCtx.Provider value={{ push }}>
      {children}
      <div className="toast-stack" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.kind}`}>
            {t.kind === "success" ? (
              <CheckCircle2 size={16} color="var(--ok)" />
            ) : t.kind === "error" ? (
              <AlertTriangle size={16} color="var(--danger)" />
            ) : (
              <Info size={16} color="var(--accent)" />
            )}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastCtx.Provider>
  );
}
