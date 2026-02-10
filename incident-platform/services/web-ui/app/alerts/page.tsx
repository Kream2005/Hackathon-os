"use client"

import { useState, useMemo } from "react"
import useSWR from "swr"
import { alertsFetcher, ingestAlert } from "@/lib/api-client"
import type { Alert, Severity } from "@/lib/types"
import { SeverityBadge } from "@/components/severity-badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
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
import { Textarea } from "@/components/ui/textarea"
import { Zap, Search, Loader2, Plus, Send, Link as LinkIcon } from "lucide-react"
import Link from "next/link"
import { mutate } from "swr"

function timeAgo(dateStr: string) {
  const now = new Date()
  const date = new Date(dateStr)
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  return `${Math.floor(diffHr / 24)}d ago`
}

export default function AlertsPage() {
  const [search, setSearch] = useState("")
  const [severityFilter, setSeverityFilter] = useState<string>("all")
  const [dialogOpen, setDialogOpen] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  // Form state
  const [newService, setNewService] = useState("")
  const [newSeverity, setNewSeverity] = useState<string>("medium")
  const [newMessage, setNewMessage] = useState("")
  const [newSource, setNewSource] = useState("manual")

  const { data: alerts, error, isLoading } = useSWR<Alert[]>(
    "/api/v1/alerts",
    alertsFetcher,
    { refreshInterval: 10000 },
  )

  const filtered = useMemo(() => {
    if (!alerts) return []
    let result = alerts
    if (severityFilter !== "all") {
      result = result.filter((a) => a.severity === severityFilter)
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      result = result.filter(
        (a) =>
          a.message.toLowerCase().includes(q) ||
          a.service.toLowerCase().includes(q) ||
          a.id.toLowerCase().includes(q),
      )
    }
    return result
  }, [alerts, severityFilter, search])

  const severityCounts = useMemo(() => {
    if (!alerts) return { critical: 0, high: 0, medium: 0, low: 0 }
    return {
      critical: alerts.filter((a) => a.severity === "critical").length,
      high: alerts.filter((a) => a.severity === "high").length,
      medium: alerts.filter((a) => a.severity === "medium").length,
      low: alerts.filter((a) => a.severity === "low").length,
    }
  }, [alerts])

  async function handleIngest() {
    if (!newService.trim() || !newMessage.trim()) return
    setIsSubmitting(true)
    try {
      await ingestAlert({
        service: newService.trim(),
        severity: newSeverity,
        message: newMessage.trim(),
        source: newSource.trim() || "manual",
      })
      mutate("/api/v1/alerts")
      mutate("/api/v1/incidents")
      setDialogOpen(false)
      setNewService("")
      setNewMessage("")
      setNewSource("manual")
      setNewSeverity("medium")
    } catch (err) {
      console.error("Failed to ingest alert:", err)
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Alerts</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Raw alerts ingested from monitoring systems — correlated into incidents
          </p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="gap-1.5">
              <Plus className="h-4 w-4" />
              Ingest Alert
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Ingest New Alert</DialogTitle>
              <DialogDescription>
                Manually send an alert to the ingestion service. It will be
                deduplicated and correlated to an incident automatically.
              </DialogDescription>
            </DialogHeader>
            <div className="flex flex-col gap-4 py-2">
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
                <label className="text-sm font-medium text-foreground">Message</label>
                <Textarea
                  placeholder="e.g. HTTP 5xx error rate > 10%"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                />
              </div>
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-medium text-foreground">Source</label>
                <Input
                  placeholder="e.g. prometheus, grafana, manual"
                  value={newSource}
                  onChange={(e) => setNewSource(e.target.value)}
                />
              </div>
            </div>
            <DialogFooter>
              <Button variant="outline" onClick={() => setDialogOpen(false)}>
                Cancel
              </Button>
              <Button
                onClick={handleIngest}
                disabled={isSubmitting || !newService.trim() || !newMessage.trim()}
                className="gap-1.5"
              >
                <Send className="h-4 w-4" />
                Ingest
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load alerts. Make sure the API Gateway and Alert Ingestion service are running.
        </div>
      )}

      {/* Severity Summary */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(["critical", "high", "medium", "low"] as const).map((sev) => (
          <Card
            key={sev}
            className={`cursor-pointer border-border bg-card transition-colors hover:bg-secondary/50 ${
              severityFilter === sev ? "ring-2 ring-primary" : ""
            }`}
            onClick={() => setSeverityFilter(severityFilter === sev ? "all" : sev)}
          >
            <CardContent className="flex items-center gap-3 py-3">
              <SeverityBadge severity={sev} />
              <span className="text-xl font-semibold text-foreground">{severityCounts[sev]}</span>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Search */}
      <div className="relative w-full sm:w-72">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder="Search alerts..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="bg-secondary pl-9"
        />
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading alerts...</span>
        </div>
      ) : (
        <div className="rounded-xl border border-border bg-card">
          <Table>
            <TableHeader>
              <TableRow className="border-border hover:bg-transparent">
                <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Alert
                </TableHead>
                <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Severity
                </TableHead>
                <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Service
                </TableHead>
                <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Source
                </TableHead>
                <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Incident
                </TableHead>
                <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                  Time
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((alert) => (
                <TableRow key={alert.id} className="border-border transition-colors hover:bg-secondary/50">
                  <TableCell>
                    <p className="text-sm font-medium text-foreground">{alert.message}</p>
                    <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                      {alert.id.slice(0, 8)}
                      {alert.fingerprint && <span className="ml-2">fp:{alert.fingerprint}</span>}
                    </p>
                  </TableCell>
                  <TableCell>
                    <SeverityBadge severity={alert.severity} />
                  </TableCell>
                  <TableCell>
                    <span className="rounded-md bg-secondary px-2 py-1 font-mono text-xs text-secondary-foreground">
                      {alert.service}
                    </span>
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">{alert.source}</TableCell>
                  <TableCell>
                    {alert.incident_id ? (
                      <Link
                        href={`/incidents/${alert.incident_id}`}
                        className="flex items-center gap-1 text-xs text-primary hover:underline"
                      >
                        <LinkIcon className="h-3 w-3" />
                        {alert.incident_id.slice(0, 8)}
                      </Link>
                    ) : (
                      <span className="text-xs text-muted-foreground">—</span>
                    )}
                  </TableCell>
                  <TableCell className="text-sm text-muted-foreground">
                    {timeAgo(alert.created_at)}
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="py-12 text-center text-muted-foreground">
                    No alerts found.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      )}
    </div>
  )
}
