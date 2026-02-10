/**
 * API Client for the Incident Platform.
 * In Docker: proxied through Vite dev server or nginx → api-gateway:8080
 * In browser (dev): direct to http://localhost:8080
 */

import type {
  Incident,
  Alert,
  IncidentSummaryStats,
  OnCallSchedule,
  CurrentOnCall,
  EscalationLog,
  NotificationPayload,
  NotificationLog,
  ServiceHealth,
} from './types'

// When served by nginx in Docker, API calls go through /api prefix which nginx proxies to api-gateway.
// When running locally with `npm run dev`, we use the direct URL.
// If the page is accessed at localhost:3001 (Docker), use '' (relative paths, nginx proxies).
// If accessed at localhost:5173 (Vite dev), the env var or fallback handles it.
const GATEWAY_URL = import.meta.env.VITE_API_GATEWAY_URL ?? ''

function getApiKey(): string {
  return localStorage.getItem('api_key') ?? ''
}

export async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const apiKey = getApiKey()
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (apiKey) headers['X-API-Key'] = apiKey

  const res = await fetch(`${GATEWAY_URL}${path}`, {
    ...options,
    headers: { ...headers, ...(options?.headers as Record<string, string> ?? {}) },
  })
  if (!res.ok) {
    const body = await res.text().catch(() => '')
    throw new Error(`API ${res.status}: ${res.statusText} — ${body}`)
  }
  return (await res.json()) as T
}

// ── Auth ──────────────────────────────────────────────────────────────────
export async function login(username: string, password: string): Promise<{ api_key: string; username: string }> {
  return apiFetch('/api/v1/auth/login', {
    method: 'POST',
    body: JSON.stringify({ username, password }),
  })
}

// ── Incidents ─────────────────────────────────────────────────────────────
export async function fetchIncidents(): Promise<Incident[]> {
  const data = await apiFetch<any>('/api/v1/incidents')
  return Array.isArray(data) ? data : (data.incidents ?? [])
}

export async function fetchIncident(id: string): Promise<Incident> {
  return apiFetch<Incident>(`/api/v1/incidents/${id}`)
}

export async function createIncident(body: { title: string; service: string; severity: string; assigned_to?: string }): Promise<Incident> {
  return apiFetch<Incident>('/api/v1/incidents', { method: 'POST', body: JSON.stringify(body) })
}

export async function updateIncident(id: string, body: Record<string, any>): Promise<Incident> {
  return apiFetch<Incident>(`/api/v1/incidents/${id}`, { method: 'PATCH', body: JSON.stringify(body) })
}

export async function fetchIncidentSummary(): Promise<IncidentSummaryStats> {
  return apiFetch<IncidentSummaryStats>('/api/v1/incidents/stats/summary')
}

// ── Alerts ────────────────────────────────────────────────────────────────
export async function fetchAlerts(): Promise<Alert[]> {
  const data = await apiFetch<any>('/api/v1/alerts')
  return Array.isArray(data) ? data : (data.alerts ?? [])
}

export async function ingestAlert(body: { service: string; severity: string; message: string; source?: string }): Promise<any> {
  return apiFetch('/api/v1/alerts', { method: 'POST', body: JSON.stringify(body) })
}

// ── On-Call ───────────────────────────────────────────────────────────────
export async function fetchSchedules(): Promise<OnCallSchedule[]> {
  return apiFetch<OnCallSchedule[]>('/api/v1/schedules')
}

export async function createSchedule(body: { team: string; rotation_type: string; members: { name: string; email: string; role: string }[] }): Promise<OnCallSchedule> {
  return apiFetch<OnCallSchedule>('/api/v1/schedules', { method: 'POST', body: JSON.stringify(body) })
}

export async function deleteSchedule(team: string): Promise<void> {
  await apiFetch(`/api/v1/schedules/${encodeURIComponent(team)}`, { method: 'DELETE' })
}

export async function fetchCurrentOnCall(team: string): Promise<CurrentOnCall> {
  return apiFetch<CurrentOnCall>(`/api/v1/oncall/current?team=${encodeURIComponent(team)}`)
}

export async function setOverride(body: { team: string; user_name: string; user_email: string; reason?: string }): Promise<any> {
  return apiFetch('/api/v1/oncall/override', { method: 'POST', body: JSON.stringify(body) })
}

export async function removeOverride(team: string): Promise<void> {
  await apiFetch(`/api/v1/oncall/override/${encodeURIComponent(team)}`, { method: 'DELETE' })
}

export async function triggerEscalation(body: { team: string; incident_id: string; reason?: string }): Promise<any> {
  return apiFetch('/api/v1/escalate', { method: 'POST', body: JSON.stringify(body) })
}

export async function fetchEscalations(): Promise<EscalationLog[]> {
  return apiFetch<EscalationLog[]>('/api/v1/escalations')
}

// ── Notifications ─────────────────────────────────────────────────────────
export async function fetchNotifications(): Promise<NotificationLog[]> {
  const data = await apiFetch<any>('/api/v1/notifications')
  return Array.isArray(data) ? data : (data.notifications ?? [])
}

export async function sendNotification(body: NotificationPayload): Promise<NotificationLog> {
  return apiFetch<NotificationLog>('/api/v1/notify', { method: 'POST', body: JSON.stringify(body) })
}

// ── Health ────────────────────────────────────────────────────────────────
export async function fetchServicesHealth(): Promise<ServiceHealth> {
  return apiFetch<ServiceHealth>('/api/services/health')
}
