export type IncidentSeverity = "low" | "medium" | "high" | "critical";
export type IncidentStatus = "created" | "investigating" | "resolved" | "failed";
export type AgentRole = "planner" | "executor" | "reflector" | "system";

export interface IncidentReport {
  incident_id: string;
  root_cause: string;
  suggested_fix: string;
  confidence: number;
  retries: number;
  tools_executed: number;
  resolution_time_ms: number;
  evidence: string[];
  timeline_summary: string[];
}

export interface Incident {
  id: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  created_at: string;
  updated_at: string;
  demo_key?: string | null;
  uploaded_log_path?: string | null;
  report?: IncidentReport | null;
}

export interface TraceEvent {
  id: string;
  incident_id: string;
  role: AgentRole;
  message: string;
  created_at: string;
  metadata: Record<string, unknown>;
}

export interface StreamEvent {
  type: string;
  incident_id: string;
  created_at: string;
  trace?: TraceEvent | null;
  incident?: Incident | null;
  report?: IncidentReport | null;
}

export interface DemoIncident {
  key: string;
  title: string;
  description: string;
  severity: IncidentSeverity;
  log_lines: string[];
  runbook_title: string;
  expected_root_cause: string;
  expected_fix: string;
}
