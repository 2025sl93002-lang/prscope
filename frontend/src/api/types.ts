// Shared TypeScript types mirroring the DepLens backend API responses.

export type Severity = "critical" | "high" | "moderate" | "low" | "unknown";
export type UpdateType =
  | "up-to-date"
  | "patch"
  | "minor"
  | "major"
  | "prerelease"
  | "unknown";
export type UsageStatus = "confirmed" | "potential" | "none" | "incomplete";
export type LicenseVerdict = "allowed" | "review" | "restricted";
export type MaintenanceStatus =
  | "active"
  | "low-activity"
  | "concerns"
  | "deprecated"
  | "unknown";

export interface ScanRef {
  id: number;
  created_at: number;
  status: string;
  health_score: number | null;
  health_grade: string | null;
}

export interface Project {
  id: number;
  name: string;
  path: string;
  ecosystem: string;
  created_at: number;
  last_scan: ScanRef | null;
}

export interface HealthFactor {
  category: string;
  label: string;
  impact: number;
  detail: string;
}

export interface HealthScore {
  score: number;
  grade: string;
  confidence: string;
  factors: HealthFactor[];
  notes: string[];
}

export interface ScanSummary {
  total: number;
  direct: number;
  transitive: number;
  scope_distribution: Record<string, number>;
  outdated: number;
  update_distribution: Record<string, number>;
  vulnerable_packages: number;
  severity_distribution: Record<string, number>;
  license_distribution: Record<string, number>;
  unknown_licenses: number;
  license_warnings: number;
  potentially_unused: number;
  maintenance_concerns: number;
  health: HealthScore;
}

export interface Stage {
  key: string;
  label: string;
  status: "pending" | "ok" | "partial" | "skipped" | "failed";
  detail: string;
  duration_ms: number;
}

export interface ScanDetail {
  id: number;
  project: Project;
  created_at: number;
  online: boolean;
  lockfile_format: string;
  root_name: string;
  root_version: string;
  health_score: number;
  health_grade: string;
  health_confidence: string;
  summary: ScanSummary;
  stages: Stage[];
  warnings: string[];
}

export interface PackageRow {
  id: number;
  node_id: string;
  name: string;
  version: string;
  is_direct: boolean;
  scope: string;
  depth: number;
  dependents: number;
  path_count: number;
  update_type: UpdateType | null;
  latest: string | null;
  license: string | null;
  license_family: string | null;
  license_verdict: LicenseVerdict | null;
  usage_status: UsageStatus | null;
  maintenance_status: MaintenanceStatus | null;
  max_severity: Severity | null;
  vuln_count: number;
  data: any;
}

export interface Vulnerability {
  id: number;
  package: string;
  installed_version: string;
  osv_id: string;
  cve: string | null;
  severity: Severity;
  summary: string;
  fixed_version: string | null;
  url: string;
  published: string | null;
  data: any;
}

export interface PackageDetail extends Omit<PackageRow, "id"> {
  vulnerabilities: Vulnerability[];
  dependency_paths: string[][];
  dependent_names: string[];
}

export interface GraphNode {
  id: string;
  name: string;
  version: string;
  direct: boolean;
  scope: string;
  depth: number;
  dependents?: number;
  blast_radius?: number;
  max_severity?: Severity | null;
  update_type?: UpdateType | null;
  license_verdict?: LicenseVerdict | null;
  vuln_count?: number;
  root?: boolean;
}

export interface GraphEdge {
  source: string;
  target: string;
  edge_type: string;
}

export interface UsageResult {
  package: string;
  version: string;
  status: UsageStatus;
  confidence: string | null;
  explanation: string | null;
  evidence: { file: string; line: number; method: string; snippet: string }[];
  override: { state: string; note: string | null } | null;
}

export interface ImpactFinding {
  kind: string;
  severity: "info" | "warning" | "critical";
  evidence: string;
  message: string;
  detail: string | null;
}

export interface ImpactReport {
  package: string;
  current_version: string | null;
  action: string;
  proposed_version: string | null;
  alternative: string | null;
  summary: string;
  dependency_paths: string[][];
  affected_packages: string[];
  affected_files: string[];
  findings: ImpactFinding[];
  verification: string[];
  limitations: string[];
}

export interface VerificationTask {
  text: string;
  status: "pending" | "complete" | "blocked" | "not-applicable";
  note?: string | null;
  evidence_url?: string | null;
}

export interface Decision {
  id: number;
  package: string;
  current_version: string | null;
  action: string;
  proposed_version: string | null;
  decision: string;
  reason: string | null;
  notes: string | null;
  status: string;
  impact: ImpactReport | null;
  verification: VerificationTask[];
  created_at: number;
  updated_at: number;
}

export interface ClearedAdvisory {
  id: string;
  cve: string | null;
  severity: Severity;
  fixed_version: string | null;
}

export interface RemediationAction {
  package: string;
  current_version: string;
  target_version: string | null;
  update_type: UpdateType | null;
  strategy: "direct" | "transitive" | "no-fix";
  is_direct: boolean;
  via_direct: string[];
  cleared: ClearedAdvisory[];
  unfixable: ClearedAdvisory[];
  max_severity_cleared: Severity;
  quick_win: boolean;
}

export interface RemediationPlan {
  actions: RemediationAction[];
  total_advisories: number;
  fixable_advisories: number;
  unfixable_advisories: number;
  packages_to_upgrade: number;
  quick_wins: number;
  summary: string;
}

export interface FixChange {
  package: string;
  kind: "dependency" | "override";
  field: string | null;
  from_spec: string | null;
  to_spec: string;
}

export interface FixEdit {
  manifest_path: string;
  changes: FixChange[];
  diff: string;
  old_content: string;
  new_content: string;
  install_command: string;
  warnings: string[];
  written: boolean;
  backup_path: string | null;
}

export interface Settings {
  online_default: boolean;
  license_policy: Record<string, string>;
  default_license_policy: Record<string, string>;
  scan_exclusions: string[];
  privacy: {
    local_data: string[];
    sent_to_public_apis: string[];
    never_sent: string[];
    external_sources: { name: string; url: string; purpose: string }[];
    telemetry: string;
  };
  version: string;
}
