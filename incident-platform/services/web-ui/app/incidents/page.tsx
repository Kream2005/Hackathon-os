"use client"

import { useState, useMemo } from "react"
import useSWR from "swr"
import { incidentsFetcher } from "@/lib/api-client"
import type { Incident } from "@/lib/types"
import { IncidentsTable } from "@/components/incidents-table"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, Loader2 } from "lucide-react"

export default function IncidentsPage() {
  const [statusFilter, setStatusFilter] = useState<string>("all")
  const [search, setSearch] = useState("")

  const { data: incidents, error, isLoading } = useSWR<Incident[]>(
    "/api/v1/incidents",
    incidentsFetcher,
    { refreshInterval: 10000 },
  )

  const filteredIncidents = useMemo(() => {
    if (!incidents) return []
    let filtered = incidents
    if (statusFilter !== "all") {
      filtered = filtered.filter((i) => i.status === statusFilter)
    }
    if (search.trim()) {
      const q = search.toLowerCase()
      filtered = filtered.filter(
        (i) =>
          i.title.toLowerCase().includes(q) ||
          i.service.toLowerCase().includes(q) ||
          i.id.toLowerCase().includes(q),
      )
    }
    return filtered
  }, [incidents, statusFilter, search])

  const statuses = [
    { value: "all", label: "All" },
    { value: "open", label: "Open" },
    { value: "acknowledged", label: "Acknowledged" },
    { value: "in_progress", label: "In Progress" },
    { value: "resolved", label: "Resolved" },
  ]

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Incidents</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Manage and track all incidents across your services
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load incidents. Make sure the API Gateway and Incident Management service are running.
        </div>
      )}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          {statuses.map((s) => (
            <Button
              key={s.value}
              variant={statusFilter === s.value ? "default" : "outline"}
              size="sm"
              onClick={() => setStatusFilter(s.value)}
            >
              {s.label}
            </Button>
          ))}
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search incidents..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="bg-secondary pl-9"
          />
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading incidents...</span>
        </div>
      ) : (
        <IncidentsTable incidents={filteredIncidents} />
      )}
    </div>
  )
}
