/**
 * API Client -- fetches from the FastAPI API Gateway.
 *
 * Browser-side: NEXT_PUBLIC_API_GATEWAY_URL (defaults to http://localhost:8080)
 * Server-side:  API_GATEWAY_URL            (defaults to http://api-gateway:8080 for Docker)
 *
 * No mock fallback -- all data comes from the real backend services.
 */

import type {
  Incident,
  Alert,
  PaginatedAlerts,
  IncidentSummaryStats,
  OnCallSchedule,
  CurrentOnCall,
  EscalationRequest,
  EscalationResponse,
  EscalationLog,
  OverrideRequest,
  TeamOverview,
  NotificationPayload,
  NotificationLog,
  ServiceHealth,
} from "@/lib/types"

const GATEWAY_URL =
  typeof window !== "undefined"
    ? (process.env.NEXT_PUBLIC_API_GATEWAY_URL ?? "http://localhost:8080")
    : (process.env.API_GATEWAY_URL ?? "http://api-gateway:8080")

export async function apiFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  const res = await fetch(`${GATEWAY_URL}${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...(options?.headers ?? {}),
    },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => "")
    throw new Error(`API error ${res.status}: ${res.statusText} — ${body}`)
  }
  return (await res.json()) as T
}

/**
 * SWR-compatible fetcher that calls the API Gateway.
 */
export const fetcher = (path: string): Promise<any> => apiFetch(path)

/**
 * Fetcher that unwraps paginated responses from the incident-management API.
 * The /api/v1/incidents endpoint returns { incidents: [...], total, page, per_page }
 * but SWR consumers expect a flat Incident[] array.
 */
export const incidentsFetcher = async (path: string): Promise<any> => {
  const data = await apiFetch<any>(path)
  // If the response is a paginated wrapper, unwrap it
  if (data && typeof data === "object" && Array.isArray(data.incidents)) {
    return data.incidents
  }
  return data
}

/**
 * Fetcher that unwraps paginated alert responses.
 */
export const alertsFetcher = async (path: string): Promise<any> => {
  const data = await apiFetch<PaginatedAlerts>(path)
  if (data && typeof data === "object" && Array.isArray(data.alerts)) {
    return data.alerts
  }
  return data
}

// ── Incident helpers ──────────────────────────────────────────────────────

export async function createIncident(body: {
  title: string
  service: string
  severity: string
  assigned_to?: string
}): Promise<Incident> {
  return apiFetch<Incident>("/api/v1/incidents", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function updateIncident(
  id: string,
  body: { status?: string; notes?: string; assigned_to?: string },
): Promise<Incident> {
  return apiFetch<Incident>(`/api/v1/incidents/${id}`, {
    method: "PATCH",
    body: JSON.stringify(body),
  })
}

export async function getIncidentSummary(): Promise<IncidentSummaryStats> {
  return apiFetch<IncidentSummaryStats>("/api/v1/incidents/stats/summary")
}

// ── Alert helpers ─────────────────────────────────────────────────────────

export async function ingestAlert(body: {
  service: string
  severity: string
  message: string
  source?: string
  labels?: Record<string, string>
}): Promise<any> {
  return apiFetch("/api/v1/alerts", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

// ── On-call helpers ───────────────────────────────────────────────────────

export async function createSchedule(body: {
  team: string
  rotation_type: string
  members: { name: string; email: string; role: string }[]
}): Promise<OnCallSchedule> {
  return apiFetch<OnCallSchedule>("/api/v1/schedules", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function deleteSchedule(team: string): Promise<void> {
  await apiFetch(`/api/v1/schedules/${encodeURIComponent(team)}`, {
    method: "DELETE",
  })
}

export async function setOverride(body: OverrideRequest): Promise<any> {
  return apiFetch("/api/v1/oncall/override", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function removeOverride(team: string): Promise<void> {
  await apiFetch(`/api/v1/oncall/override/${encodeURIComponent(team)}`, {
    method: "DELETE",
  })
}

// ── Escalation helpers ────────────────────────────────────────────────────

export async function triggerEscalation(
  body: EscalationRequest,
): Promise<EscalationResponse> {
  return apiFetch<EscalationResponse>("/api/v1/escalate", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

export async function listEscalations(
  team?: string,
): Promise<EscalationLog[]> {
  const qs = team ? `?team=${encodeURIComponent(team)}` : ""
  return apiFetch<EscalationLog[]>(`/api/v1/escalations${qs}`)
}

// ── Notification helpers ──────────────────────────────────────────────────

export async function sendNotification(
  body: NotificationPayload,
): Promise<NotificationLog> {
  return apiFetch<NotificationLog>("/api/v1/notify", {
    method: "POST",
    body: JSON.stringify(body),
  })
}

// ── Service health ────────────────────────────────────────────────────────

export async function getServicesHealth(): Promise<ServiceHealth> {
  return apiFetch<ServiceHealth>("/api/services/health")
}
