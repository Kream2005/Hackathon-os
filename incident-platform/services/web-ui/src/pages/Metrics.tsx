import { useState, useEffect, useMemo } from 'react'
import { fetchIncidents } from '../api-client'
import type { Incident } from '../types'
import {
  LineChart, Line, BarChart, Bar, AreaChart, Area, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, ResponsiveContainer, Tooltip, Legend,
} from 'recharts'
import { Timer, Clock, TrendingDown, AlertTriangle, Loader2 } from 'lucide-react'

const INDIGO = '#818cf8', BLUE = '#60a5fa', RED = '#f87171', YELLOW = '#facc15', ORANGE = '#fb923c'
const sevColors: Record<string, string> = { critical: RED, high: ORANGE, medium: YELLOW, low: BLUE }

export default function Metrics() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const load = async () => {
      try { const data = await fetchIncidents(); if (mounted) { setIncidents(data); setError(null) } }
      catch (e: any) { if (mounted) setError(e.message) }
      finally { if (mounted) setLoading(false) }
    }
    load(); const id = setInterval(load, 15000); return () => { mounted = false; clearInterval(id) }
  }, [])

  const stats = useMemo(() => {
    if (!incidents.length) return null
    const withMtta = incidents.filter(i => i.mtta_seconds !== null)
    const withMttr = incidents.filter(i => i.mttr_seconds !== null)
    const avgMtta = withMtta.length > 0 ? withMtta.reduce((a, i) => a + (i.mtta_seconds || 0), 0) / withMtta.length : 0
    const avgMttr = withMttr.length > 0 ? withMttr.reduce((a, i) => a + (i.mttr_seconds || 0), 0) / withMttr.length : 0
    const openIncidents = incidents.filter(i => i.status !== 'resolved').length

    // By service
    const svcMap = new Map<string, number>()
    for (const i of incidents) svcMap.set(i.service, (svcMap.get(i.service) ?? 0) + 1)
    const byService = Array.from(svcMap).map(([service, count]) => ({ service, count })).sort((a, b) => b.count - a.count)

    // Severity
    const sevMap = new Map<string, number>()
    for (const i of incidents) sevMap.set(i.severity, (sevMap.get(i.severity) ?? 0) + 1)
    const sevDist = Array.from(sevMap).map(([severity, count]) => ({ severity, count }))

    // Over time
    const dayMap = new Map<string, { open: number; acknowledged: number; resolved: number }>()
    for (const i of incidents) {
      const day = new Date(i.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      if (!dayMap.has(day)) dayMap.set(day, { open: 0, acknowledged: 0, resolved: 0 })
      const e = dayMap.get(day)!
      if (i.status === 'resolved') e.resolved++; else if (i.status === 'acknowledged') e.acknowledged++; else e.open++
    }
    const overTime = Array.from(dayMap).map(([date, v]) => ({ date, ...v }))

    // MTTA/MTTR trends
    const mttaByDay = new Map<string, number[]>()
    const mttrByDay = new Map<string, number[]>()
    for (const i of incidents) {
      const day = new Date(i.created_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
      if (i.mtta_seconds !== null) { if (!mttaByDay.has(day)) mttaByDay.set(day, []); mttaByDay.get(day)!.push(i.mtta_seconds) }
      if (i.mttr_seconds !== null) { if (!mttrByDay.has(day)) mttrByDay.set(day, []); mttrByDay.get(day)!.push(i.mttr_seconds) }
    }
    const mttaTrend = Array.from(mttaByDay).map(([date, v]) => ({ date, value: Math.round(v.reduce((a, b) => a + b, 0) / v.length) }))
    const mttrTrend = Array.from(mttrByDay).map(([date, v]) => ({ date, value: Math.round(v.reduce((a, b) => a + b, 0) / v.length) }))

    return { avgMtta, avgMttr, totalIncidents: incidents.length, openIncidents, byService, sevDist, overTime, mttaTrend, mttrTrend }
  }, [incidents])

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /><span className="ml-2 text-sm text-muted-foreground">Loading metrics…</span></div>
  if (error) return <div className="p-6"><div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">{error}</div></div>
  if (!stats) return null

  const cards = [
    { title: 'Avg MTTA', value: stats.avgMtta > 0 ? `${Math.round(stats.avgMtta / 60)}m` : '--', sub: 'Mean Time to Acknowledge', icon: Timer },
    { title: 'Avg MTTR', value: stats.avgMttr > 0 ? `${(stats.avgMttr / 3600).toFixed(1)}h` : '--', sub: 'Mean Time to Resolve', icon: Clock },
    { title: 'Total Incidents', value: stats.totalIncidents, sub: 'All time', icon: AlertTriangle },
    { title: 'Active Incidents', value: stats.openIncidents, sub: 'Not yet resolved', icon: TrendingDown },
  ]

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">SRE Performance Metrics</h1>
        <p className="mt-1 text-sm text-muted-foreground">MTTA and MTTR trends, incident volume, and response time distribution</p>
      </div>

      {/* Metric Cards */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {cards.map(c => (
          <div key={c.title} className="rounded-xl border border-border bg-card p-5">
            <div className="flex items-center justify-between">
              <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{c.title}</p>
              <c.icon className="h-4 w-4 text-muted-foreground" />
            </div>
            <p className="mt-2 text-3xl font-bold text-foreground">{c.value}</p>
            <p className="mt-1 text-xs text-muted-foreground">{c.sub}</p>
          </div>
        ))}
      </div>

      {/* MTTA + MTTR Trends */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard title="MTTA Trend (seconds)" sub="Mean Time to Acknowledge per day">
          {stats.mttaTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={stats.mttaTrend}>
                <defs><linearGradient id="mttaG" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={INDIGO} stopOpacity={0.2}/><stop offset="100%" stopColor={INDIGO} stopOpacity={0}/></linearGradient></defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,14%)" />
                <XAxis dataKey="date" tick={{ fill: 'hsl(215,15%,55%)', fontSize: 12 }} />
                <YAxis tick={{ fill: 'hsl(215,15%,55%)', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: 'hsl(220,15%,9%)', border: '1px solid hsl(220,13%,20%)', borderRadius: 8, color: '#fff' }} />
                <Area type="monotone" dataKey="value" stroke={INDIGO} fill="url(#mttaG)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <p className="py-8 text-center text-sm text-muted-foreground">No MTTA data yet.</p>}
        </ChartCard>

        <ChartCard title="MTTR Trend (seconds)" sub="Mean Time to Resolve per day">
          {stats.mttrTrend.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <AreaChart data={stats.mttrTrend}>
                <defs><linearGradient id="mttrG" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor={BLUE} stopOpacity={0.2}/><stop offset="100%" stopColor={BLUE} stopOpacity={0}/></linearGradient></defs>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,14%)" />
                <XAxis dataKey="date" tick={{ fill: 'hsl(215,15%,55%)', fontSize: 12 }} />
                <YAxis tick={{ fill: 'hsl(215,15%,55%)', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: 'hsl(220,15%,9%)', border: '1px solid hsl(220,13%,20%)', borderRadius: 8, color: '#fff' }} />
                <Area type="monotone" dataKey="value" stroke={BLUE} fill="url(#mttrG)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <p className="py-8 text-center text-sm text-muted-foreground">No MTTR data yet.</p>}
        </ChartCard>
      </div>

      {/* By Service + Over Time */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        <ChartCard title="Incidents by Service" sub="Top noisy services">
          {stats.byService.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <BarChart data={stats.byService} layout="vertical">
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,14%)" />
                <XAxis type="number" tick={{ fill: 'hsl(215,15%,55%)', fontSize: 12 }} />
                <YAxis dataKey="service" type="category" tick={{ fill: 'hsl(215,15%,55%)', fontSize: 11 }} width={110} />
                <Tooltip contentStyle={{ background: 'hsl(220,15%,9%)', border: '1px solid hsl(220,13%,20%)', borderRadius: 8, color: '#fff' }} />
                <Bar dataKey="count" fill={INDIGO} radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          ) : <p className="py-8 text-center text-sm text-muted-foreground">No incidents yet.</p>}
        </ChartCard>

        <ChartCard title="Incidents Over Time" sub="Created incidents by status per day">
          {stats.overTime.length > 0 ? (
            <ResponsiveContainer width="100%" height={250}>
              <LineChart data={stats.overTime}>
                <CartesianGrid strokeDasharray="3 3" stroke="hsl(220,14%,14%)" />
                <XAxis dataKey="date" tick={{ fill: 'hsl(215,15%,55%)', fontSize: 12 }} />
                <YAxis tick={{ fill: 'hsl(215,15%,55%)', fontSize: 12 }} />
                <Tooltip contentStyle={{ background: 'hsl(220,15%,9%)', border: '1px solid hsl(220,13%,20%)', borderRadius: 8, color: '#fff' }} />
                <Line type="monotone" dataKey="open" stroke={RED} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="acknowledged" stroke={YELLOW} strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="resolved" stroke={INDIGO} strokeWidth={2} dot={false} />
                <Legend />
              </LineChart>
            </ResponsiveContainer>
          ) : <p className="py-8 text-center text-sm text-muted-foreground">No incidents yet.</p>}
        </ChartCard>
      </div>

      {/* Severity Dist */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <ChartCard title="Severity Distribution" sub="Breakdown of incidents by severity">
          {stats.sevDist.length > 0 ? (
            <div className="flex items-center justify-center">
              <ResponsiveContainer width={200} height={200}>
                <PieChart>
                  <Pie data={stats.sevDist} dataKey="count" nameKey="severity" cx="50%" cy="50%" innerRadius={50} outerRadius={80} strokeWidth={2} stroke="hsl(220,16%,6%)">
                    {stats.sevDist.map(e => <Cell key={e.severity} fill={sevColors[e.severity] ?? BLUE} />)}
                  </Pie>
                  <Tooltip contentStyle={{ background: 'hsl(220,15%,9%)', border: '1px solid hsl(220,13%,20%)', borderRadius: 8, color: '#fff' }} />
                </PieChart>
              </ResponsiveContainer>
            </div>
          ) : <p className="py-8 text-center text-sm text-muted-foreground">No data yet.</p>}
        </ChartCard>

        <div className="rounded-xl border border-border bg-card p-5 lg:col-span-2">
          <h3 className="text-sm font-medium text-foreground">Severity Breakdown</h3>
          {stats.sevDist.length > 0 ? (
            <div className="mt-4 grid grid-cols-2 gap-4 sm:grid-cols-4">
              {stats.sevDist.map(e => (
                <div key={e.severity} className="flex flex-col items-center gap-2 rounded-lg border border-border bg-secondary/30 p-4">
                  <div className="h-3 w-3 rounded-full" style={{ backgroundColor: sevColors[e.severity] ?? BLUE }} />
                  <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{e.severity}</span>
                  <span className="text-2xl font-semibold text-foreground">{e.count}</span>
                  <span className="text-xs text-muted-foreground">incidents</span>
                </div>
              ))}
            </div>
          ) : <p className="py-8 text-center text-sm text-muted-foreground">No data yet.</p>}
        </div>
      </div>
    </div>
  )
}

function ChartCard({ title, sub, children }: { title: string; sub: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <h3 className="text-sm font-medium text-foreground">{title}</h3>
      <p className="mb-3 text-xs text-muted-foreground">{sub}</p>
      {children}
    </div>
  )
}
