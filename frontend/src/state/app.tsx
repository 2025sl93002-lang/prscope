import { createContext, useContext, useEffect, useState, type ReactNode } from "react";
import { api } from "../api/client";
import type { Project } from "../api/types";

interface AppState {
  projects: Project[];
  loading: boolean;
  currentProjectId: number | null;
  currentScanId: number | null;
  setCurrentProject: (id: number | null) => void;
  setCurrentScan: (id: number | null) => void;
  refreshProjects: () => Promise<void>;
}

const AppCtx = createContext<AppState>(null as unknown as AppState);
export const useApp = () => useContext(AppCtx);

export function AppProvider({ children }: { children: ReactNode }) {
  const [projects, setProjects] = useState<Project[]>([]);
  const [loading, setLoading] = useState(true);
  const [currentProjectId, setProjectId] = useState<number | null>(
    () =>
      Number(new URLSearchParams(window.location.search).get("project")) ||
      Number(localStorage.getItem("deplens-project")) ||
      null,
  );
  const [currentScanId, setScanId] = useState<number | null>(
    () => Number(localStorage.getItem("deplens-scan")) || null,
  );

  const refreshProjects = async () => {
    setLoading(true);
    try {
      const { projects } = await api.listProjects();
      setProjects(projects);
      // Auto-select a sensible default.
      setProjectId((pid) => {
        if (pid && projects.some((p) => p.id === pid)) return pid;
        return projects[0]?.id ?? null;
      });
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshProjects();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Keep the selected scan in sync with the selected project's latest scan.
  useEffect(() => {
    if (currentProjectId == null) {
      setScanId(null);
      return;
    }
    const proj = projects.find((p) => p.id === currentProjectId);
    if (proj && proj.last_scan) {
      setScanId((sid) => sid ?? proj.last_scan!.id);
    }
  }, [currentProjectId, projects]);

  useEffect(() => {
    if (currentProjectId) localStorage.setItem("deplens-project", String(currentProjectId));
    else localStorage.removeItem("deplens-project");
  }, [currentProjectId]);
  useEffect(() => {
    if (currentScanId) localStorage.setItem("deplens-scan", String(currentScanId));
    else localStorage.removeItem("deplens-scan");
  }, [currentScanId]);

  const setCurrentProject = (id: number | null) => {
    setProjectId(id);
    const proj = projects.find((p) => p.id === id);
    setScanId(proj?.last_scan?.id ?? null);
  };

  return (
    <AppCtx.Provider
      value={{
        projects,
        loading,
        currentProjectId,
        currentScanId,
        setCurrentProject,
        setCurrentScan: setScanId,
        refreshProjects,
      }}
    >
      {children}
    </AppCtx.Provider>
  );
}
