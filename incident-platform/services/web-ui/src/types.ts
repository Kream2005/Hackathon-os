export type Severity = 'critical' | 'high' | 'medium' | 'low'
export type IncidentStatus = 'open' | 'acknowledged' | 'in_progress' | 'resolved'

export interface Alert {
  id: string
  service: string
  severity: Severity
  message: string
  source: string
  labels: Record<string, string>
  fingerprint: string | null
  timestamp: string
  incident_id: string | null
  created_at: string
}

export interface Incident {
  id: string
  title: string
  service: string
  severity: Severity
  status: IncidentStatus
  assigned_to: string | null
  alert_count: number
  created_at: string
  updated_at: string
  acknowledged_at: string | null
  resolved_at: string | null
  mtta_seconds: number | null
  mttr_seconds: number | null
  alerts?: Alert[]
  notes?: IncidentNote[]
  timeline?: TimelineEvent[]
}

export interface IncidentNote {
  id: string
  author: string
  content: string
  created_at: string
}

export interface TimelineEvent {
  id: string
  event_type: string
  actor: string
  detail: Record<string, any>
  created_at: string
}

export interface IncidentSummaryStats {
  open: number
  acknowledged: number
  in_progress: number
  resolved: number
  avg_mtta_seconds: number | null
  avg_mttr_seconds: number | null
}

export interface OnCallSchedule {
  id: string
  team: string
  rotation_type: 'weekly' | 'daily' | 'biweekly'
  members: OnCallMember[]
  created_at: string
}

export interface OnCallMember {
  name: string
  email: string
  role: 'primary' | 'secondary'
}

export interface CurrentOnCall {
  team: string
  primary: { name: string; email: string; override?: boolean; reason?: string }
  secondary: { name: string; email: string } | null
  schedule_id: string
  rotation_type: string
}

export interface EscalationLog {
  escalation_id: string
  team: string
  incident_id: string
  reason: string
  escalated_to: { name: string; email: string } | null
  timestamp: string
}

export interface NotificationPayload {
  incident_id: string
  channel: string
  recipient: string
  message: string
}

export interface NotificationLog {
  id: string
  incident_id: string
  channel: string
  recipient: string
  message: string
  status: 'sent' | 'failed'
  created_at: string
}

export interface ServiceHealth {
  [service: string]: { status: 'up' | 'down'; code?: number }
}
