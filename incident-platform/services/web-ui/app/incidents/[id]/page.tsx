"use client"

import { use, useState } from "react"
import Link from "next/link"
import useSWR, { mutate } from "swr"
import { apiFetch, fetcher } from "@/lib/api-client"
import { SeverityBadge } from "@/components/severity-badge"
import { StatusBadge } from "@/components/status-badge"
import { Button } from "@/components/ui/button"
import { Textarea } from "@/components/ui/textarea"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import {
  ArrowLeft,
  CheckCircle,
  XCircle,
  Clock,
  User,
  AlertTriangle,
  MessageSquare,
  Activity,
  Loader2,
} from "lucide-react"
import type { Incident, IncidentStatus } from "@/lib/types"

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
    second: "2-digit",
  })
}

function formatSeconds(seconds: number | null): string {
  if (seconds === null) return "--"
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m ${Math.round(seconds % 60)}s`
  return `${Math.floor(seconds / 3600)}h ${Math.round((seconds % 3600) / 60)}m`
}

export default function IncidentDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params)
  const [noteText, setNoteText] = useState("")
  const [isUpdating, setIsUpdating] = useState(false)

  const { data: incident, error, isLoading } = useSWR<Incident>(
    `/api/v1/incidents/${id}`,
    fetcher,
    { refreshInterval: 5000 },
  )

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading incident...</span>
      </div>
    )
  }

  if (error || !incident) {
    return (
      <div className="flex flex-col items-center justify-center gap-4 p-12">
        <AlertTriangle className="h-12 w-12 text-muted-foreground" />
        <h2 className="text-lg font-semibold text-foreground">
          {error ? "Failed to load incident" : "Incident not found"}
        </h2>
        <p className="text-sm text-muted-foreground">
          {error ? "Make sure the API Gateway and Incident Management service are running." : `No incident with ID "${id}" exists.`}
        </p>
        <Link href="/incidents">
          <Button variant="outline">Back to incidents</Button>
        </Link>
      </div>
    )
  }

  async function handleStatusChange(newStatus: IncidentStatus) {
    setIsUpdating(true)
    try {
      await apiFetch(`/api/v1/incidents/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ status: newStatus }),
      })
      // Re-fetch the incident and the list
      mutate(`/api/v1/incidents/${id}`)
      mutate("/api/v1/incidents")
    } catch (err) {
      console.error("Failed to update status:", err)
    } finally {
      setIsUpdating(false)
    }
  }

  async function handleAddNote() {
    if (!noteText.trim()) return
    setIsUpdating(true)
    try {
      await apiFetch(`/api/v1/incidents/${id}`, {
        method: "PATCH",
        body: JSON.stringify({ note: { author: "Operator", content: noteText.trim() } }),
      })
      mutate(`/api/v1/incidents/${id}`)
      setNoteText("")
    } catch (err) {
      console.error("Failed to add note:", err)
    } finally {
      setIsUpdating(false)
    }
  }

  const notes = incident.notes ?? []

  // Build timeline events
  const timelineEvents = [
    { time: incident.created_at, label: "Incident created", icon: AlertTriangle, color: "text-red-400" },
    ...(incident.acknowledged_at
      ? [{ time: incident.acknowledged_at, label: "Acknowledged", icon: CheckCircle, color: "text-yellow-400" }]
      : []),
    ...(incident.resolved_at
      ? [{ time: incident.resolved_at, label: "Resolved", icon: CheckCircle, color: "text-emerald-400" }]
      : []),
    ...notes.map((n) => ({
      time: n.created_at,
      label: `${n.author}: ${n.content}`,
      icon: MessageSquare,
      color: "text-blue-400",
    })),
  ].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Back + Header */}
      <div className="flex flex-col gap-4">
        <Link
          href="/incidents"
          className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to incidents
        </Link>

        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-2">
            <h1 className="text-xl font-semibold text-foreground">{incident.title}</h1>
            <div className="flex items-center gap-3">
              <SeverityBadge severity={incident.severity} />
              <StatusBadge status={incident.status} />
              <span className="rounded-md bg-secondary px-2 py-1 font-mono text-xs text-secondary-foreground">
                {incident.service}
              </span>
              <span className="font-mono text-xs text-muted-foreground">{incident.id}</span>
            </div>
          </div>

          {/* Action Buttons */}
          <div className="flex items-center gap-2">
            {incident.status === "open" && (
              <Button
                onClick={() => handleStatusChange("acknowledged")}
                className="gap-1.5 bg-yellow-500/10 text-yellow-400 hover:bg-yellow-500/20"
                variant="outline"
                disabled={isUpdating}
              >
                <CheckCircle className="h-4 w-4" />
                Acknowledge
              </Button>
            )}
            {(incident.status === "acknowledged" || incident.status === "in_progress") && (
              <Button
                onClick={() => handleStatusChange("resolved")}
                className="gap-1.5 bg-emerald-500/10 text-emerald-400 hover:bg-emerald-500/20"
                variant="outline"
                disabled={isUpdating}
              >
                <CheckCircle className="h-4 w-4" />
                Resolve
              </Button>
            )}
            {incident.status === "acknowledged" && (
              <Button
                onClick={() => handleStatusChange("in_progress")}
                className="gap-1.5"
                variant="outline"
                disabled={isUpdating}
              >
                <Activity className="h-4 w-4" />
                In Progress
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Content Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        {/* Left: Timeline + Notes */}
        <div className="flex flex-col gap-6 lg:col-span-2">
          {/* Timeline */}
          <Card className="border-border bg-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-foreground">Timeline</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-4">
                {timelineEvents.map((evt, idx) => (
                  <div key={idx} className="flex items-start gap-3">
                    <div className="mt-0.5 flex flex-col items-center">
                      <evt.icon className={`h-4 w-4 ${evt.color}`} />
                      {idx < timelineEvents.length - 1 && (
                        <div className="mt-1 h-8 w-px bg-border" />
                      )}
                    </div>
                    <div className="flex flex-col gap-0.5">
                      <p className="text-sm text-foreground">{evt.label}</p>
                      <p className="text-xs text-muted-foreground">{formatDate(evt.time)}</p>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Add Note */}
          <Card className="border-border bg-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-foreground">Add Note</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-3">
                <Textarea
                  placeholder="Add investigation notes..."
                  value={noteText}
                  onChange={(e) => setNoteText(e.target.value)}
                  className="min-h-[80px] bg-secondary"
                />
                <Button onClick={handleAddNote} size="sm" className="self-end" disabled={isUpdating}>
                  <MessageSquare className="mr-1.5 h-4 w-4" />
                  Add Note
                </Button>
              </div>
            </CardContent>
          </Card>

          {/* Linked Alerts */}
          {incident.alerts && incident.alerts.length > 0 && (
            <Card className="border-border bg-card">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm font-medium text-foreground">
                  Linked Alerts ({incident.alerts.length})
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-col gap-2">
                  {incident.alerts.map((alert) => (
                    <div
                      key={alert.id}
                      className="flex items-center justify-between rounded-lg border border-border bg-secondary/50 px-4 py-3"
                    >
                      <div className="flex flex-col gap-0.5">
                        <p className="text-sm text-foreground">{alert.message}</p>
                        <p className="font-mono text-xs text-muted-foreground">{alert.id}</p>
                      </div>
                      <div className="flex items-center gap-2">
                        <SeverityBadge severity={alert.severity} />
                        <span className="text-xs text-muted-foreground">
                          {formatDate(alert.timestamp)}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Details Sidebar */}
        <div className="flex flex-col gap-4">
          <Card className="border-border bg-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-foreground">Details</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <User className="h-3.5 w-3.5" />
                    Assigned to
                  </dt>
                  <dd className="text-sm text-foreground">
                    {incident.assigned_to || "Unassigned"}
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
                    <Clock className="h-3.5 w-3.5" />
                    Created
                  </dt>
                  <dd className="text-sm text-foreground">
                    {formatDate(incident.created_at)}
                  </dd>
                </div>
                {incident.acknowledged_at && (
                  <div className="flex items-center justify-between">
                    <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <CheckCircle className="h-3.5 w-3.5" />
                      Acknowledged
                    </dt>
                    <dd className="text-sm text-foreground">
                      {formatDate(incident.acknowledged_at)}
                    </dd>
                  </div>
                )}
                {incident.resolved_at && (
                  <div className="flex items-center justify-between">
                    <dt className="flex items-center gap-1.5 text-xs text-muted-foreground">
                      <XCircle className="h-3.5 w-3.5" />
                      Resolved
                    </dt>
                    <dd className="text-sm text-foreground">
                      {formatDate(incident.resolved_at)}
                    </dd>
                  </div>
                )}
              </dl>
            </CardContent>
          </Card>

          {/* Metrics Card */}
          <Card className="border-border bg-card">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm font-medium text-foreground">Response Metrics</CardTitle>
            </CardHeader>
            <CardContent>
              <dl className="flex flex-col gap-4">
                <div className="flex items-center justify-between">
                  <dt className="text-xs text-muted-foreground">MTTA</dt>
                  <dd className="font-mono text-lg font-semibold text-foreground">
                    {formatSeconds(incident.mtta_seconds)}
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-xs text-muted-foreground">MTTR</dt>
                  <dd className="font-mono text-lg font-semibold text-foreground">
                    {formatSeconds(incident.mttr_seconds)}
                  </dd>
                </div>
                <div className="flex items-center justify-between">
                  <dt className="text-xs text-muted-foreground">Linked Alerts</dt>
                  <dd className="font-mono text-lg font-semibold text-foreground">
                    {incident.alerts?.length ?? 0}
                  </dd>
                </div>
              </dl>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  )
}
