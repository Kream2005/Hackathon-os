"use client"

import Link from "next/link"
import type { Incident } from "@/lib/types"
import { SeverityBadge } from "@/components/severity-badge"
import { StatusBadge } from "@/components/status-badge"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"

function timeAgo(dateStr: string) {
  const now = new Date()
  const date = new Date(dateStr)
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  const diffDay = Math.floor(diffHr / 24)
  return `${diffDay}d ago`
}

export function IncidentsTable({ incidents }: { incidents: Incident[] }) {
  return (
    <div className="rounded-xl border border-border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="border-border hover:bg-transparent">
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Incident
            </TableHead>
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Severity
            </TableHead>
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Status
            </TableHead>
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Service
            </TableHead>
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Assigned
            </TableHead>
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Created
            </TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {incidents.map((incident) => (
            <TableRow
              key={incident.id}
              className="border-border transition-colors hover:bg-secondary/50"
            >
              <TableCell>
                <Link
                  href={`/incidents/${incident.id}`}
                  className="font-medium text-foreground hover:text-primary"
                >
                  {incident.title}
                </Link>
                <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                  {incident.id}
                </p>
              </TableCell>
              <TableCell>
                <SeverityBadge severity={incident.severity} />
              </TableCell>
              <TableCell>
                <StatusBadge status={incident.status} />
              </TableCell>
              <TableCell>
                <span className="rounded-md bg-secondary px-2 py-1 font-mono text-xs text-secondary-foreground">
                  {incident.service}
                </span>
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {incident.assigned_to || "Unassigned"}
              </TableCell>
              <TableCell className="text-sm text-muted-foreground">
                {timeAgo(incident.created_at)}
              </TableCell>
            </TableRow>
          ))}
          {incidents.length === 0 && (
            <TableRow>
              <TableCell colSpan={6} className="py-12 text-center text-muted-foreground">
                No incidents found.
              </TableCell>
            </TableRow>
          )}
        </TableBody>
      </Table>
    </div>
  )
}
