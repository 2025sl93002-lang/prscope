// PRScope API client + shared types. SPDX-License-Identifier: MIT
// Mirrors the backend Pydantic models in backend/prscope/models.py.

export type AttentionLevel = 'low' | 'moderate' | 'high' | 'critical'
export type TaskStatus = 'open' | 'completed' | 'blocked' | 'not_applicable'
export type Priority = 'low' | 'medium' | 'high'
export type ImpactType = 'changed' | 'direct' | 'indirect' | 'unaffected'
export type ChangeType = 'added' | 'modified' | 'deleted' | 'renamed'
export type EvidenceType =
  | 'test_result' | 'ci' | 'manual' | 'screenshot' | 'report'
  | 'build' | 'api' | 'security_scan' | 'reviewer_note' | 'doc'

export interface Repository {
  id: number
  name: string
  path: string
  default_branch: string | null
  created_at: string
}
export interface RepositoryDetail extends Repository {
  branches: string[]
  recent_commits: { hash: string; author: string; date: string; subject: string }[]
  head: string | null
}
export interface Analysis {
  id: number
  repository_id: number
  base_ref: string
  target_ref: string
  status: 'pending' | 'running' | 'complete' | 'failed'
  error: string | null
  files_changed: number
  files_added: number
  files_modified: number
  files_deleted: number
  files_renamed: number
  lines_added: number
  lines_removed: number
  attention_level: AttentionLevel | null
  risk_score: number
  created_at: string
}
export interface ChangedFile {
  id: number
  path: string
  old_path: string | null
  change_type: ChangeType
  lines_added: number
  lines_removed: number
  category: string
  classification_reason: string | null
  confidence: number
  matched_rule: string | null
}
export interface GraphNode {
  id: string; label: string; impact_type: ImpactType; category: string | null; distance: number
}
export interface GraphEdge {
  source: string; target: string; relation_type: string; detection: string
}
export interface DependencyGraph {
  nodes: GraphNode[]; edges: GraphEdge[]; function_level: boolean; note: string | null
}
export interface FileImpact {
  path: string
  category: string | null
  direct_dependencies: string[]
  reverse_dependencies: string[]
  downstream_impact: string[]
  related_tests: string[]
  path_explanations: string[]
}
export interface RiskFinding {
  id?: number
  title: string
  severity: AttentionLevel
  related_files: string[]
  explanation: string
  evidence: string
  suggested_action: string
  rule: string
  score_contribution: number
}
export interface RiskReport {
  attention_level: AttentionLevel
  score: number
  findings: RiskFinding[]
  methodology_note: string
}
export interface VerificationTask {
  id: number
  task_key: string
  title: string
  description: string
  reason: string
  related_files: string[]
  verification_type: string
  priority: Priority
  status: TaskStatus
  steps: string[]
  evidence_requirements: string[]
  generated: boolean
  created_at: string | null
  updated_at: string | null
}
export interface TaskHistoryEntry {
  id: number; from_status: string | null; to_status: string; note: string | null
  actor: string | null; created_at: string
}
export interface EvidenceRecord {
  id: number; task_id: number; analysis_id: number; evidence_type: EvidenceType
  note: string | null; link: string | null; command: string | null; result: string | null
  performed_by: string | null; created_at: string
}
export interface TestGap {
  id?: number; changed_file: string; related_tests: string[]; detection_method: string
  missing_coverage: string; recommended_tests: string[]; severity: AttentionLevel
}
export interface ChecklistItem {
  id: number; text: string; checked: boolean; reviewer_note: string | null
  source: string; sort_order: number; created_at: string | null
}
export interface ReviewReadiness {
  attention_level: AttentionLevel | null
  risk_score: number
  total_tasks: number
  applicable_tasks: number
  completed_tasks: number
  pending_tasks: number
  blocked_tasks: number
  not_applicable_tasks: number
  tasks_with_evidence: number
  tasks_without_evidence: number
  completeness_percent: number
  completeness_label: string
  test_gap_count: number
  risk_finding_count: number
  changed_file_count: number
  affected_module_count: number
}
export interface Settings {
  ai_enabled: boolean; ai_endpoint: string; ai_model: string; theme: string
}
export interface AIStatus { enabled: boolean; endpoint: string; model: string; available: boolean }
export interface AIExplain { available: boolean; source: string; text: string; model: string | null }

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  const opts: RequestInit = { method, headers: {} }
  if (body !== undefined) {
    opts.headers = { 'Content-Type': 'application/json' }
    opts.body = JSON.stringify(body)
  }
  const resp = await fetch(url, opts)
  if (!resp.ok) {
    let detail = `${resp.status} ${resp.statusText}`
    try {
      const data = await resp.json()
      if (data?.detail) detail = typeof data.detail === 'string' ? data.detail : JSON.stringify(data.detail)
    } catch {
      /* non-JSON error body */
    }
    throw new ApiError(resp.status, detail)
  }
  if (resp.status === 204) return undefined as T
  const ct = resp.headers.get('content-type') || ''
  return (ct.includes('application/json') ? resp.json() : resp.text()) as Promise<T>
}

export const api = {
  health: () => req<{ status: string; version: string; name: string }>('GET', '/api/health'),

  // Repositories
  listRepositories: () => req<Repository[]>('GET', '/api/repositories'),
  getRepository: (id: number) => req<RepositoryDetail>('GET', `/api/repositories/${id}`),
  createRepository: (path: string, name?: string) =>
    req<Repository>('POST', '/api/repositories', { path, name }),
  validateRepository: (path: string) =>
    req<{ valid: boolean; path: string; name: string; default_branch: string | null }>(
      'POST', '/api/repositories/validate', { path }),
  deleteRepository: (id: number) => req<void>('DELETE', `/api/repositories/${id}`),

  // Analyses
  listAnalyses: (repoId?: number) =>
    req<Analysis[]>('GET', `/api/analyses${repoId ? `?repository_id=${repoId}` : ''}`),
  getAnalysis: (id: number) => req<Analysis>('GET', `/api/analyses/${id}`),
  createAnalysis: (repository_id: number, base_ref: string, target_ref: string) =>
    req<Analysis>('POST', '/api/analyses', { repository_id, base_ref, target_ref }),
  deleteAnalysis: (id: number) => req<void>('DELETE', `/api/analyses/${id}`),
  getChanges: (id: number) => req<ChangedFile[]>('GET', `/api/analyses/${id}/changes`),
  getGraph: (id: number) => req<DependencyGraph>('GET', `/api/analyses/${id}/graph`),
  getFileImpact: (id: number, path: string) =>
    req<FileImpact>('GET', `/api/analyses/${id}/impact/file?path=${encodeURIComponent(path)}`),
  getRisk: (id: number) => req<RiskReport>('GET', `/api/analyses/${id}/risk`),
  getTestGaps: (id: number) => req<TestGap[]>('GET', `/api/analyses/${id}/test-gaps`),
  getReadiness: (id: number) => req<ReviewReadiness>('GET', `/api/analyses/${id}/readiness`),

  // Verification tasks
  listTasks: (id: number) => req<VerificationTask[]>('GET', `/api/analyses/${id}/tasks`),
  createTask: (id: number, body: Partial<VerificationTask>) =>
    req<VerificationTask>('POST', `/api/analyses/${id}/tasks`, body),
  updateTask: (taskId: number, body: Record<string, unknown>) =>
    req<VerificationTask>('PATCH', `/api/tasks/${taskId}`, body),
  deleteTask: (taskId: number) => req<void>('DELETE', `/api/tasks/${taskId}`),
  taskHistory: (taskId: number) => req<TaskHistoryEntry[]>('GET', `/api/tasks/${taskId}/history`),

  // Evidence
  listEvidence: (taskId: number) => req<EvidenceRecord[]>('GET', `/api/tasks/${taskId}/evidence`),
  listAnalysisEvidence: (id: number) => req<EvidenceRecord[]>('GET', `/api/analyses/${id}/evidence`),
  addEvidence: (taskId: number, body: Partial<EvidenceRecord>) =>
    req<EvidenceRecord>('POST', `/api/tasks/${taskId}/evidence`, body),
  deleteEvidence: (evidenceId: number) => req<void>('DELETE', `/api/evidence/${evidenceId}`),

  // Checklist
  listChecklist: (id: number) => req<ChecklistItem[]>('GET', `/api/analyses/${id}/checklist`),
  addChecklistItem: (id: number, text: string) =>
    req<ChecklistItem>('POST', `/api/analyses/${id}/checklist`, { text }),
  updateChecklistItem: (itemId: number, body: Record<string, unknown>) =>
    req<ChecklistItem>('PATCH', `/api/checklist/${itemId}`, body),
  deleteChecklistItem: (itemId: number) => req<void>('DELETE', `/api/checklist/${itemId}`),

  // Settings & AI
  getSettings: () => req<Settings>('GET', '/api/settings'),
  updateSettings: (body: Settings) => req<Settings>('PUT', '/api/settings', body),
  aiStatus: () => req<AIStatus>('GET', '/api/ai/status'),
  aiExplain: (analysis_id: number, kind: string, target_id?: number) =>
    req<AIExplain>('POST', '/api/ai/explain', { analysis_id, kind, target_id }),

  // Demo
  setupDemo: () => req<{ repository_id: number; analysis_id: number; is_demo: boolean }>(
    'POST', '/api/demo/setup'),

  reportUrl: (id: number, fmt: 'md' | 'json' | 'html') => `/api/analyses/${id}/report.${fmt}`,
}
