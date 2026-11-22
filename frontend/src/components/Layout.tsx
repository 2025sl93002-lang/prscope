import { useState, type ReactNode } from "react";
import { NavLink, Outlet, useLocation, useNavigate } from "react-router-dom";
import {
  Boxes,
  FileBarChart,
  FolderGit2,
  GitFork,
  History,
  LayoutDashboard,
  Lock,
  Moon,
  Plus,
  Scale,
  ScanLine,
  Settings as SettingsIcon,
  ShieldAlert,
  Sun,
  TestTubeDiagonal,
  Workflow,
} from "lucide-react";
import { useTheme } from "../state/theme";
import { useApp } from "../state/app";
import { Button } from "./ui";
import { ScanModal } from "./ScanModal";
import { relativeTime } from "../lib/format";
import "./Layout.css";

const NAV = [
  { to: "/", label: "Overview", icon: LayoutDashboard, end: true },
  { to: "/projects", label: "Projects", icon: FolderGit2 },
  { to: "/graph", label: "Dependency Graph", icon: GitFork },
  { to: "/explorer", label: "Dependencies", icon: Boxes },
  { to: "/security", label: "Security", icon: ShieldAlert },
  { to: "/updates", label: "Updates", icon: ScanLine },
  { to: "/licenses", label: "Licenses", icon: Scale },
  { to: "/usage", label: "Usage Analysis", icon: Workflow },
  { to: "/impact", label: "Impact Simulator", icon: TestTubeDiagonal },
  { to: "/decisions", label: "Decisions", icon: FileBarChart },
  { to: "/reports", label: "Reports", icon: FileBarChart },
  { to: "/history", label: "Scan History", icon: History },
  { to: "/settings", label: "Settings", icon: SettingsIcon },
];

const TITLES: Record<string, string> = {
  "/": "Overview",
  "/projects": "Projects",
  "/graph": "Dependency Graph",
  "/explorer": "Dependencies",
  "/security": "Security",
  "/updates": "Updates",
  "/licenses": "Licenses",
  "/usage": "Usage Analysis",
  "/impact": "Impact Simulator",
  "/decisions": "Decision Workspace",
  "/reports": "Reports",
  "/history": "Scan History",
  "/settings": "Settings",
};

export function Layout() {
  const { theme, toggle } = useTheme();
  const { projects, currentProjectId, setCurrentProject, refreshProjects, setCurrentScan } = useApp();
  const [scanOpen, setScanOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const current = projects.find((p) => p.id === currentProjectId) ?? null;
  const title = TITLES[location.pathname] ?? "DepLens";

  return (
    <div className="app">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">
            <ScanLine size={18} />
          </div>
          <div className="col">
            <span className="brand-name">DepLens</span>
            <span className="brand-tag">Know your dependencies</span>
          </div>
        </div>

        <div className="project-switch">
          <select
            className="select"
            value={currentProjectId ?? ""}
            onChange={(e) => setCurrentProject(e.target.value ? Number(e.target.value) : null)}
            aria-label="Select project"
          >
            {projects.length === 0 && <option value="">No projects yet</option>}
            {projects.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          {current && (
            <div className="project-meta">
              <span title={current.path} className="mono" style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {current.path}
              </span>
              <span>
                {current.ecosystem} · last scan {relativeTime(current.last_scan?.created_at)}
              </span>
            </div>
          )}
        </div>

        <nav className="nav">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              className={({ isActive }) => `nav-item ${isActive ? "active" : ""}`}
            >
              <item.icon />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="sidebar-footer">
          <span className="local-pill">
            <Lock size={11} /> Local-only
          </span>
          <Button icon variant="ghost" onClick={toggle} aria-label="Toggle theme">
            {theme === "dark" ? <Sun size={17} /> : <Moon size={17} />}
          </Button>
        </div>
      </aside>

      <div className="main">
        <header className="topbar">
          <div className="col">
            <h1>{title}</h1>
            {current && <span className="crumb">{current.name}</span>}
          </div>
          <Button variant="primary" onClick={() => setScanOpen(true)}>
            <Plus size={16} /> New scan
          </Button>
        </header>
        <div className="content">
          <div className="content-inner">
            <Outlet />
          </div>
        </div>
      </div>

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
    </div>
  );
}

export function NoScan({ children }: { children?: ReactNode }) {
  return (
    <div className="empty" style={{ paddingTop: 80 }}>
      <ScanLine />
      <h3>No scan selected</h3>
      <div style={{ maxWidth: 400 }}>
        {children ?? "Run a scan on a local npm project to see analysis here. Use the “New scan” button in the top-right — the bundled demo project is pre-filled."}
      </div>
    </div>
  );
}
