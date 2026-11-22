// Thin fetch wrapper around the DepLens API. Uses relative /api URLs (proxied
// to the backend in dev, served by the backend in production).

import type {
  Decision,
  FixEdit,
  GraphEdge,
  GraphNode,
  ImpactReport,
  PackageDetail,
  PackageRow,
  Project,
  RemediationPlan,
  ScanDetail,
  Settings,
  UsageResult,
  Vulnerability,
} from "./types";

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(res.status, detail);
  }
  if (res.status === 204) return undefined as T;
  return res.json() as Promise<T>;
}

export const api = {
  health: () => request<{ status: string; version: string }>("/health"),

  demoPath: () => request<{ path: string; exists: boolean }>("/demo"),

  listProjects: () => request<{ projects: Project[] }>("/projects"),

  scan: (path: string, online: boolean) =>
    request<{ scan_id: number; project_id: number }>("/scan", {
      method: "POST",
      body: JSON.stringify({ path, online }),
    }),

  deleteProject: (id: number) =>
    request<{ ok: boolean }>(`/projects/${id}`, { method: "DELETE" }),

  projectScans: (id: number) =>
    request<{ scans: any[] }>(`/projects/${id}/scans`),

  scanDetail: (id: number) => request<ScanDetail>(`/scans/${id}`),

  packages: (id: number, params: Record<string, string> = {}) => {
    const q = new URLSearchParams(params).toString();
    return request<{ packages: PackageRow[]; count: number }>(
      `/scans/${id}/packages${q ? `?${q}` : ""}`,
    );
  },

  packageDetail: (id: number, name: string) =>
    request<PackageDetail>(`/scans/${id}/package/${encodeURIComponent(name)}`),

  graph: (id: number, includeDev = true, includeOptional = true) =>
    request<{ nodes: GraphNode[]; edges: GraphEdge[] }>(
      `/scans/${id}/graph?include_dev=${includeDev}&include_optional=${includeOptional}`,
    ),

  vulnerabilities: (id: number) =>
    request<{ vulnerabilities: Vulnerability[]; checked: boolean; count: number }>(
      `/scans/${id}/vulnerabilities`,
    ),

  remediation: (id: number) => request<RemediationPlan>(`/scans/${id}/remediation`),

  fixPlan: (id: number, packages?: string[]) =>
    request<FixEdit>(`/scans/${id}/fix-plan`, {
      method: "POST",
      body: JSON.stringify({ packages: packages ?? null }),
    }),

  fixApply: (id: number, packages?: string[]) =>
    request<FixEdit>(`/scans/${id}/fix-apply`, {
      method: "POST",
      body: JSON.stringify({ packages: packages ?? null }),
    }),

  licenses: (id: number) =>
    request<{
      inventory: any[];
      family_distribution: Record<string, number>;
      verdict_distribution: Record<string, number>;
    }>(`/scans/${id}/licenses`),

  usage: (id: number) => request<{ usage: UsageResult[] }>(`/scans/${id}/usage`),

  compare: (id: number, other: number) =>
    request<any>(`/scans/${id}/compare/${other}`),

  impact: (
    id: number,
    body: {
      package: string;
      action: string;
      proposed_version?: string;
      alternative?: string;
      online?: boolean;
    },
  ) =>
    request<ImpactReport>(`/scans/${id}/impact`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  decisions: (projectId: number) =>
    request<{ decisions: Decision[] }>(`/projects/${projectId}/decisions`),

  createDecision: (projectId: number, body: any) =>
    request<Decision>(`/projects/${projectId}/decisions`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  updateDecision: (id: number, body: any) =>
    request<Decision>(`/decisions/${id}`, {
      method: "PUT",
      body: JSON.stringify(body),
    }),

  deleteDecision: (id: number) =>
    request<{ ok: boolean }>(`/decisions/${id}`, { method: "DELETE" }),

  setUsageOverride: (projectId: number, body: any) =>
    request<any>(`/projects/${projectId}/usage-override`, {
      method: "POST",
      body: JSON.stringify(body),
    }),

  getSettings: () => request<Settings>("/settings"),

  updateSettings: (body: any) =>
    request<Settings>("/settings", { method: "PUT", body: JSON.stringify(body) }),

  reportUrl: (id: number, format: string) => `/api/scans/${id}/report?format=${format}`,
};
