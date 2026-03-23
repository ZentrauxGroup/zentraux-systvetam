/**
 * SYSTVETAM — Shared Types
 * Zentraux Group LLC
 *
 * Mirrors Pydantic schemas from Central Dispatch.
 * Single source of truth for frontend type safety.
 */

// ---------------------------------------------------------------------------
// Auth
// ---------------------------------------------------------------------------

export interface AuthUser {
  agent_id: string;
  role: 'SUPERUSER' | 'OPERATOR' | 'VIEWER';
  display_name: string;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  agent_id: string;
  role: string;
  display_name: string;
}

// ---------------------------------------------------------------------------
// Crew
// ---------------------------------------------------------------------------

export type CrewStatus = 'ACTIVE' | 'IDLE' | 'EXECUTING' | 'ERROR' | 'OFFLINE';

export interface CrewMember {
  id: string;
  callsign: string;
  display_name: string;
  role: string;
  department: string;
  execution_plane: string;
  status: CrewStatus;
  container_id: string | null;
  current_task_ref: string | null;
  last_heartbeat: string | null;
  bio: string | null;
  sop_reference: string | null;
  container_port: number | null;
  container_image: string | null;
  created_at: string;
}

export interface CrewListResponse {
  crew: CrewMember[];
  total: number;
  active_count: number;
  executing_count: number;
}

// ---------------------------------------------------------------------------
// Tasks
// ---------------------------------------------------------------------------

export type TaskStatus =
  | 'NEW' | 'ASSIGNED' | 'EXECUTING' | 'QA_GATE'
  | 'LEVI_GATE' | 'DEPLOYING' | 'COMPLETE' | 'RECEIPTED' | 'FAILED';

export type TaskType =
  | 'STANDARD' | 'INTELLIGENCE_BRIEF' | 'BUILD_FROM_INTEL'
  | 'OPPORTUNITY' | 'GTM_CAMPAIGN' | 'VOICE_OUTREACH'
  | 'SECURITY_REVIEW' | 'QA_EVALUATION';

export interface Task {
  id: string;
  task_ref: string;
  title: string;
  description: string | null;
  output: string | null;
  task_type: TaskType;
  source: string | null;
  department: string | null;
  assigned_to: string | null;
  requested_by: string;
  status: TaskStatus;
  priority: number;
  qa_result: Record<string, unknown> | null;
  levi_note: string | null;
  intel_brief_id: string | null;
  container_id: string | null;
  execution_plane: string | null;
  payload: Record<string, unknown> | null;
  created_at: string;
  assigned_at: string | null;
  executing_at: string | null;
  completed_at: string | null;
  receipted_at: string | null;
}

export interface TaskListResponse {
  tasks: Task[];
  total: number;
  offset: number;
  limit: number;
}

// ---------------------------------------------------------------------------
// Receipts
// ---------------------------------------------------------------------------

export interface Receipt {
  id: string;
  receipt_ref: string;
  receipt_type: string;
  task_id: string | null;
  crew_member_id: string | null;
  issued_by: string;
  summary: string;
  payload: Record<string, unknown> | null;
  sop_reference: string | null;
  created_at: string;
}

// ---------------------------------------------------------------------------
// WebSocket Events
// ---------------------------------------------------------------------------

export interface WsEvent {
  channel: string;
  ts: string;
  event: string;
  [key: string]: unknown;
}

// ---------------------------------------------------------------------------
// System
// ---------------------------------------------------------------------------

export interface HealthResponse {
  status: 'operational' | 'degraded';
  service: string;
  version: string;
  ts: string;
}

export interface StatusResponse {
  status: 'operational' | 'degraded';
  service: string;
  version: string;
  environment: string;
  uptime_seconds: number;
  checks: {
    postgres: 'connected' | 'unreachable';
    redis: 'connected' | 'unreachable';
  };
  config: {
    default_plane: string;
    dispatch_url: string;
    signal_threshold: number;
  };
  ts: string;
}
