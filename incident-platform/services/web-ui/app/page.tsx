"use client"

import { useState, useMemo } from "react"
import useSWR, { mutate } from "swr"
import { incidentsFetcher, createIncident, getIncidentSummary } from "@/lib/api-client"
import type { Incident, IncidentSummaryStats } from "@/lib/types"
import { MetricCard } from "@/components/metric-card"
import { IncidentsTable } from "@/components/incidents-table"
import { AlertTriangle, Clock, CheckCircle2, Timer, Loader2, Plus, Send } from "lucide-react"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Textarea } from "@/components/ui/textarea"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

function formatSeconds(seconds: number): string {
  if (seconds < 60) return `${Math.round(seconds)}s`
  if (seconds < 3600) return `${Math.round(seconds / 60)}m`
  return `${(seconds / 3600).toFixed(1)}h`
}

export default function DashboardPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all")

  const { data: incidents, error, isLoading } = useSWR<Incident[]>(
    "/api/v1/incidents",
    incidentsFetcher,
    { refreshInterval: 10000 },
  )

  // Use the backend stats/summary endpoint for accurate aggregates
  const { data: summary } = useSWR<IncidentSummaryStats>(
    "/api/v1/incidents/stats/summary",
    () => getIncidentSummary(),
    { refreshInterval: 10000 },
  )

  const openCount = summary?.open ?? incidents?.filter((i) => i.status === "open").length ?? 0
  const ackedCount = summary?.acknowledged ?? incidents?.filter((i) => i.status === "acknowledged").length ?? 0
  const inProgressCount = summary?.in_progress ?? incidents?.filter((i) => i.status === "in_progress").length ?? 0
  const resolvedCount = summary?.resolved ?? incidents?.filter((i) => i.status === "resolved").length ?? 0

  const avgMtta = summary?.avg_mtta_seconds ?? useMemo(() => {
    if (!incidents) return 0
    const withMtta = incidents.filter((i) => i.mtta_seconds !== null)
    if (withMtta.length === 0) return 0
    return withMtta.reduce((acc, i) => acc + (i.mtta_seconds || 0), 0) / withMtta.length
  }, [incidents])

  const avgMttr = summary?.avg_mttr_seconds ?? useMemo(() => {
    if (!incidents) return 0
    const withMttr = incidents.filter((i) => i.mttr_seconds !== null)
    if (withMttr.length === 0) return 0
    return withMttr.reduce((acc, i) => acc + (i.mttr_seconds || 0), 0) / withMttr.length
  }, [incidents])

  // Create incident dialog state
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [newTitle, setNewTitle] = useState("")
  const [newService, setNewService] = useState("")
  const [newSeverity, setNewSeverity] = useState("medium")
  const [newAssignee, setNewAssignee] = useState("")

  async function handleCreateIncident() {
    if (!newTitle.trim() || !newService.trim()) return
    setCreating(true)
    try {
      await createIncident({
        title: newTitle.trim(),
        service: newService.trim(),
        severity: newSeverity,
        assigned_to: newAssignee.trim() || undefined,
      })
      mutate("/api/v1/incidents")
      mutate("/api/v1/incidents/stats/summary")
      setCreateOpen(false)
      setNewTitle("")
      setNewService("")
      setNewSeverity("medium")
      setNewAssignee("")
    } catch (err) {
      console.error("Failed to create incident:", err)
    } finally {
      setCreating(false)
    }
  }

  const filteredIncidents = useMemo(() => {
    if (!incidents) return []
    if (statusFilter === "all") return incidents
    return incidents.filter((i) => i.status === statusFilter)
  }, [incidents, statusFilter])

  const filters = [
    { value: "all", label: "All", count: incidents?.length ?? 0 },
    { value: "open", label: "Open", count: openCount },
    { value: "acknowledged", label: "Acknowledged", count: ackedCount },
    { value: "in_progress", label: "In Progress", count: inProgressCount },
    { value: "resolved", label: "Resolved", count: resolvedCount },
  ]

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Real-time incident overview and SRE metrics
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Dialog open={createOpen} onOpenChange={setCreateOpen}>
            <DialogTrigger asChild>
              <Button className="gap-1.5">
                <Plus className="h-4 w-4" />
                New Incident
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>Create Incident</DialogTitle>
                <DialogDescription>
                  Manually create a new incident for tracking.
                </DialogDescription>
              </DialogHeader>
              <div className="flex flex-col gap-4 py-2">
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-foreground">Title</label>
                  <Input
                    placeholder="e.g. API Gateway 5xx spike"
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-foreground">Service</label>
                  <Input
                    placeholder="e.g. frontend-api"
                    value={newService}
                    onChange={(e) => setNewService(e.target.value)}
                  />
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-foreground">Severity</label>
                  <Select value={newSeverity} onValueChange={setNewSeverity}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="critical">Critical</SelectItem>
                      <SelectItem value="high">High</SelectItem>
                      <SelectItem value="medium">Medium</SelectItem>
                      <SelectItem value="low">Low</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex flex-col gap-1.5">
                  <label className="text-sm font-medium text-foreground">Assigned To (optional)</label>
                  <Input
                    placeholder="e.g. alice@example.com"
                    value={newAssignee}
                    onChange={(e) => setNewAssignee(e.target.value)}
                  />
                </div>
              </div>
              <DialogFooter>
                <Button variant="outline" onClick={() => setCreateOpen(false)}>
                  Cancel
                </Button>
                <Button
                  onClick={handleCreateIncident}
                  disabled={creating || !newTitle.trim() || !newService.trim()}
                  className="gap-1.5"
                >
                  <Send className="h-4 w-4" />
                  Create
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
          <span className="flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
            Live
          </span>
        </div>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load incidents from the API Gateway. Make sure the backend services are running.
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading incidents...</span>
        </div>
      )}

      {!isLoading && (
        <>
          {/* Metric Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            <MetricCard
              title="Open Incidents"
              value={openCount}
              subtitle={`${ackedCount} acknowledged`}
              icon={AlertTriangle}
              variant={openCount > 2 ? "critical" : "default"}
            />
            <MetricCard
              title="In Progress"
              value={inProgressCount}
              subtitle="Being investigated"
              icon={Clock}
              variant="warning"
            />
            <MetricCard
              title="Avg MTTA"
              value={formatSeconds(avgMtta)}
              subtitle="Mean Time to Acknowledge"
              icon={Timer}
              variant="default"
            />
            <MetricCard
              title="Resolved"
              value={resolvedCount}
              subtitle={`Avg MTTR: ${formatSeconds(avgMttr)}`}
              icon={CheckCircle2}
              variant="success"
            />
          </div>

          {/* Filter Tabs + Table */}
          <div className="flex flex-col gap-4">
            <div className="flex items-center gap-2">
              {filters.map((f) => (
                <Button
                  key={f.value}
                  variant={statusFilter === f.value ? "default" : "outline"}
                  size="sm"
                  onClick={() => setStatusFilter(f.value)}
                  className="gap-1.5"
                >
                  {f.label}
                  <span className="rounded-full bg-background/20 px-1.5 py-0.5 text-[10px] font-mono">
                    {f.count}
                  </span>
                </Button>
              ))}
            </div>
            <IncidentsTable incidents={filteredIncidents} />
          </div>
        </>
      )}
    </div>
  )
}
