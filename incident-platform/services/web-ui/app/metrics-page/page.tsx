"use client"

import useSWR from "swr"
import { incidentsFetcher } from "@/lib/api-client"
import type { Incident } from "@/lib/types"
import { useMemo } from "react"
import {
  Line,
  LineChart,
  Bar,
  BarChart,
  Area,
  AreaChart,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Cell,
  Pie,
  PieChart,
} from "recharts"
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card"
import {
  ChartContainer,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import { MetricCard } from "@/components/metric-card"
import { Timer, Clock, TrendingDown, AlertTriangle, Loader2 } from "lucide-react"

const INDIGO = "#818cf8"
const BLUE = "#60a5fa"
const ORANGE = "#fb923c"
const RED = "#f87171"
const YELLOW = "#facc15"
const VIOLET = "#a78bfa"

const severityColors: Record<string, string> = {
  critical: RED,
  high: ORANGE,
  medium: YELLOW,
  low: BLUE,
}

export default function SREMetricsPage() {
  const { data: incidents, error, isLoading } = useSWR<Incident[]>(
    "/api/v1/incidents",
    incidentsFetcher,
    { refreshInterval: 15000 },
  )

  const stats = useMemo(() => {
    if (!incidents) return null

    const withMtta = incidents.filter((i) => i.mtta_seconds !== null)
    const withMttr = incidents.filter((i) => i.mttr_seconds !== null)

    const avgMtta = withMtta.length > 0
      ? withMtta.reduce((a, i) => a + (i.mtta_seconds || 0), 0) / withMtta.length
      : 0
    const avgMttr = withMttr.length > 0
      ? withMttr.reduce((a, i) => a + (i.mttr_seconds || 0), 0) / withMttr.length
      : 0

    const totalIncidents = incidents.length
    const openIncidents = incidents.filter((i) => i.status !== "resolved").length

    // Derive incidents-by-service counts
    const serviceMap = new Map<string, number>()
    for (const inc of incidents) {
      serviceMap.set(inc.service, (serviceMap.get(inc.service) ?? 0) + 1)
    }
    const incidentsByService = Array.from(serviceMap.entries())
      .map(([service, count]) => ({ service, count }))
      .sort((a, b) => b.count - a.count)

    // Derive severity distribution
    const sevMap = new Map<string, number>()
    for (const inc of incidents) {
      sevMap.set(inc.severity, (sevMap.get(inc.severity) ?? 0) + 1)
    }
    const severityDistribution = Array.from(sevMap.entries()).map(([severity, count]) => ({
      severity,
      count,
    }))

    // Derive incidents over time by day
    const dayMap = new Map<string, { open: number; acknowledged: number; resolved: number }>()
    for (const inc of incidents) {
      const day = new Date(inc.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })
      if (!dayMap.has(day)) dayMap.set(day, { open: 0, acknowledged: 0, resolved: 0 })
      const entry = dayMap.get(day)!
      if (inc.status === "resolved") entry.resolved++
      else if (inc.status === "acknowledged") entry.acknowledged++
      else entry.open++
    }
    const incidentsOverTime = Array.from(dayMap.entries()).map(([date, vals]) => ({
      date,
      ...vals,
    }))

    // MTTA trend by day (averages per day from incidents that have mtta)
    const mttaByDay = new Map<string, number[]>()
    const mttrByDay = new Map<string, number[]>()
    for (const inc of incidents) {
      const day = new Date(inc.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })
      if (inc.mtta_seconds !== null) {
        if (!mttaByDay.has(day)) mttaByDay.set(day, [])
        mttaByDay.get(day)!.push(inc.mtta_seconds)
      }
      if (inc.mttr_seconds !== null) {
        if (!mttrByDay.has(day)) mttrByDay.set(day, [])
        mttrByDay.get(day)!.push(inc.mttr_seconds)
      }
    }
    const mttaTrend = Array.from(mttaByDay.entries()).map(([date, vals]) => ({
      date,
      value: Math.round(vals.reduce((a, b) => a + b, 0) / vals.length),
    }))
    const mttrTrend = Array.from(mttrByDay.entries()).map(([date, vals]) => ({
      date,
      value: Math.round(vals.reduce((a, b) => a + b, 0) / vals.length),
    }))

    return {
      avgMtta,
      avgMttr,
      totalIncidents,
      openIncidents,
      incidentsByService,
      severityDistribution,
      incidentsOverTime,
      mttaTrend,
      mttrTrend,
    }
  }, [incidents])

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
        <span className="ml-2 text-sm text-muted-foreground">Loading metrics...</span>
      </div>
    )
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load metrics. Make sure the API Gateway and Incident Management service are running.
        </div>
      </div>
    )
  }

  if (!stats) return null

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">SRE Performance Metrics</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          MTTA and MTTR trends, incident volume, and response time distribution
        </p>
      </div>

      {/* Top Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          title="Avg MTTA"
          value={stats.avgMtta > 0 ? `${Math.round(stats.avgMtta / 60)}m` : "--"}
          subtitle="Mean Time to Acknowledge"
          icon={Timer}
          variant="default"
        />
        <MetricCard
          title="Avg MTTR"
          value={stats.avgMttr > 0 ? `${(stats.avgMttr / 3600).toFixed(1)}h` : "--"}
          subtitle="Mean Time to Resolve"
          icon={Clock}
          variant="default"
        />
        <MetricCard
          title="Total Incidents"
          value={stats.totalIncidents}
          subtitle="All time"
          icon={AlertTriangle}
          variant="warning"
        />
        <MetricCard
          title="Active Incidents"
          value={stats.openIncidents}
          subtitle="Not yet resolved"
          icon={TrendingDown}
          variant={stats.openIncidents > 3 ? "critical" : "default"}
        />
      </div>

      {/* Charts Row 1: MTTA and MTTR Trends */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* MTTA Trend */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-foreground">
              MTTA Trend (seconds)
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              Mean Time to Acknowledge per day
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats.mttaTrend.length > 0 ? (
              <ChartContainer
                config={{ value: { label: "MTTA (s)", color: INDIGO } }}
                className="h-[250px]"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={stats.mttaTrend}>
                    <defs>
                      <linearGradient id="mttaGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={INDIGO} stopOpacity={0.2} />
                        <stop offset="100%" stopColor={INDIGO} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="hsl(220 14% 14%)" />
                    <XAxis dataKey="date" tick={{ fill: "hsl(215 15% 55%)", fontSize: 12 }} />
                    <YAxis tick={{ fill: "hsl(215 15% 55%)", fontSize: 12 }} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Area type="monotone" dataKey="value" stroke={INDIGO} fill="url(#mttaGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </ChartContainer>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">No MTTA data yet.</p>
            )}
          </CardContent>
        </Card>

        {/* MTTR Trend */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-foreground">
              MTTR Trend (seconds)
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              Mean Time to Resolve per day
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats.mttrTrend.length > 0 ? (
              <ChartContainer
                config={{ value: { label: "MTTR (s)", color: BLUE } }}
                className="h-[250px]"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <AreaChart data={stats.mttrTrend}>
                    <defs>
                      <linearGradient id="mttrGrad" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor={BLUE} stopOpacity={0.2} />
                        <stop offset="100%" stopColor={BLUE} stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="date" className="fill-muted-foreground text-xs" />
                    <YAxis className="fill-muted-foreground text-xs" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Area type="monotone" dataKey="value" stroke={BLUE} fill="url(#mttrGrad)" strokeWidth={2} />
                  </AreaChart>
                </ResponsiveContainer>
              </ChartContainer>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">No MTTR data yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Charts Row 2: Incidents by Service + Over Time */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Incidents by Service */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-foreground">
              Incidents by Service
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              Top noisy services
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats.incidentsByService.length > 0 ? (
              <ChartContainer
                config={{ count: { label: "Incidents", color: INDIGO } }}
                className="h-[250px]"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.incidentsByService} layout="vertical">
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis type="number" className="fill-muted-foreground text-xs" />
                    <YAxis dataKey="service" type="category" className="fill-muted-foreground text-[11px]" width={110} />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Bar dataKey="count" fill={INDIGO} radius={[0, 4, 4, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </ChartContainer>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">No incidents yet.</p>
            )}
          </CardContent>
        </Card>

        {/* Incidents Over Time */}
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-foreground">
              Incidents Over Time
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              Created incidents by status per day
            </CardDescription>
          </CardHeader>
          <CardContent>
            {stats.incidentsOverTime.length > 0 ? (
              <ChartContainer
                config={{
                  open: { label: "Open", color: RED },
                  acknowledged: { label: "Acknowledged", color: YELLOW },
                  resolved: { label: "Resolved", color: INDIGO },
                }}
                className="h-[250px]"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={stats.incidentsOverTime}>
                    <CartesianGrid strokeDasharray="3 3" className="stroke-border" />
                    <XAxis dataKey="date" className="fill-muted-foreground text-xs" />
                    <YAxis className="fill-muted-foreground text-xs" />
                    <ChartTooltip content={<ChartTooltipContent />} />
                    <Line type="monotone" dataKey="open" stroke={RED} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="acknowledged" stroke={YELLOW} strokeWidth={2} dot={false} />
                    <Line type="monotone" dataKey="resolved" stroke={INDIGO} strokeWidth={2} dot={false} />
                  </LineChart>
                </ResponsiveContainer>
              </ChartContainer>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">No incidents yet.</p>
            )}
          </CardContent>
        </Card>
      </div>

      {/* Severity Distribution */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="border-border bg-card">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-foreground">
              Severity Distribution
            </CardTitle>
            <CardDescription className="text-xs text-muted-foreground">
              Breakdown of incidents by severity
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center justify-center">
            {stats.severityDistribution.length > 0 ? (
              <ChartContainer
                config={{ count: { label: "Count" } }}
                className="h-[200px] w-[200px]"
              >
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={stats.severityDistribution}
                      dataKey="count"
                      nameKey="severity"
                      cx="50%"
                      cy="50%"
                      innerRadius={50}
                      outerRadius={80}
                      strokeWidth={2}
                      stroke="hsl(var(--background))"
                    >
                      {stats.severityDistribution.map((entry) => (
                        <Cell key={entry.severity} fill={severityColors[entry.severity] ?? BLUE} />
                      ))}
                    </Pie>
                    <ChartTooltip content={<ChartTooltipContent />} />
                  </PieChart>
                </ResponsiveContainer>
              </ChartContainer>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">No data yet.</p>
            )}
          </CardContent>
        </Card>

        {/* Legend card */}
        <Card className="border-border bg-card lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-foreground">
              Severity Breakdown
            </CardTitle>
          </CardHeader>
          <CardContent>
            {stats.severityDistribution.length > 0 ? (
              <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
                {stats.severityDistribution.map((entry) => (
                  <div
                    key={entry.severity}
                    className="flex flex-col items-center gap-2 rounded-lg border border-border bg-secondary/30 p-4"
                  >
                    <div
                      className="h-3 w-3 rounded-full"
                      style={{ backgroundColor: severityColors[entry.severity] ?? BLUE }}
                    />
                    <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
                      {entry.severity}
                    </span>
                    <span className="text-2xl font-semibold text-foreground">{entry.count}</span>
                    <span className="text-xs text-muted-foreground">incidents</span>
                  </div>
                ))}
              </div>
            ) : (
              <p className="py-8 text-center text-sm text-muted-foreground">No data yet.</p>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
