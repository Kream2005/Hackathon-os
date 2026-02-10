import { useState, useEffect, useMemo } from 'react'
import { fetchIncidents, fetchIncidentSummary, createIncident } from '../api-client'
import type { Incident, IncidentSummaryStats } from '../types'
import IncidentsTable from '../components/IncidentsTable'
import { AlertTriangle, Clock, CheckCircle2, Timer, Loader2, Plus, Send, X } from 'lucide-react'

function fmtSec(s: number): string {
  if (s < 60) return `${Math.round(s)}s`
  if (s < 3600) return `${Math.round(s / 60)}m`
  return `${(s / 3600).toFixed(1)}h`
}

export default function Dashboard() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [summary, setSummary] = useState<IncidentSummaryStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('all')
  const [createOpen, setCreateOpen] = useState(false)
  const [creating, setCreating] = useState(false)
  const [form, setForm] = useState({ title: '', service: '', severity: 'medium', assigned_to: '' })

  async function load() {
    try {
      const [inc, sum] = await Promise.all([fetchIncidents(), fetchIncidentSummary()])
      setIncidents(inc)
      setSummary(sum)
      setError(null)
    } catch (e: any) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(); const id = setInterval(load, 10000); return () => clearInterval(id) }, [])

  const openCount = summary?.open ?? incidents.filter(i => i.status === 'open').length
  const ackedCount = summary?.acknowledged ?? incidents.filter(i => i.status === 'acknowledged').length
  const inProgressCount = summary?.in_progress ?? incidents.filter(i => i.status === 'in_progress').length
  const resolvedCount = summary?.resolved ?? incidents.filter(i => i.status === 'resolved').length
  const avgMtta = summary?.avg_mtta_seconds ?? 0
  const avgMttr = summary?.avg_mttr_seconds ?? 0

  const filtered = useMemo(() => {
    if (statusFilter === 'all') return incidents
    return incidents.filter(i => i.status === statusFilter)
  }, [incidents, statusFilter])

  async function handleCreate() {
    if (!form.title.trim() || !form.service.trim()) return
    setCreating(true)
    try {
      await createIncident({ title: form.title.trim(), service: form.service.trim(), severity: form.severity, assigned_to: form.assigned_to.trim() || undefined })
      setCreateOpen(false)
      setForm({ title: '', service: '', severity: 'medium', assigned_to: '' })
      load()
    } catch (e) { console.error(e) }
    finally { setCreating(false) }
  }

  const filters = [
    { value: 'all', label: 'All', count: incidents.length },
    { value: 'open', label: 'Open', count: openCount },
    { value: 'acknowledged', label: 'Acknowledged', count: ackedCount },
    { value: 'in_progress', label: 'In Progress', count: inProgressCount },
    { value: 'resolved', label: 'Resolved', count: resolvedCount },
  ]

  const cards = [
    { title: 'Open Incidents', value: openCount, sub: `${ackedCount} acknowledged`, icon: AlertTriangle, variant: openCount > 2 ? 'border-red-500/30 bg-red-500/5' : '' },
    { title: 'In Progress', value: inProgressCount, sub: 'Being investigated', icon: Clock, variant: 'border-yellow-500/30 bg-yellow-500/5' },
    { title: 'Avg MTTA', value: avgMtta > 0 ? fmtSec(avgMtta) : '--', sub: 'Mean Time to Acknowledge', icon: Timer, variant: '' },
    { title: 'Resolved', value: resolvedCount, sub: `Avg MTTR: ${avgMttr > 0 ? fmtSec(avgMttr) : '--'}`, icon: CheckCircle2, variant: 'border-emerald-500/30 bg-emerald-500/5' },
  ]

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Dashboard</h1>
          <p className="mt-1 text-sm text-muted-foreground">Real-time incident overview and SRE metrics</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => setCreateOpen(true)} className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
            <Plus className="h-4 w-4" /> New Incident
          </button>
          <span className="flex items-center gap-1.5 rounded-full bg-primary/10 px-3 py-1 text-xs font-medium text-primary">
            <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-primary" /> Live
          </span>
        </div>
      </div>

      {error && <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /><span className="ml-2 text-sm text-muted-foreground">Loading…</span></div>
      ) : (
        <>
          {/* Metric Cards */}
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
            {cards.map(c => (
              <div key={c.title} className={`rounded-xl border border-border bg-card p-5 ${c.variant}`}>
                <div className="flex items-center justify-between">
                  <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">{c.title}</p>
                  <c.icon className="h-4 w-4 text-muted-foreground" />
                </div>
                <p className="mt-2 text-3xl font-bold text-foreground">{c.value}</p>
                <p className="mt-1 text-xs text-muted-foreground">{c.sub}</p>
              </div>
            ))}
          </div>

          {/* Filters */}
          <div className="flex items-center gap-2">
            {filters.map(f => (
              <button key={f.value} onClick={() => setStatusFilter(f.value)}
                className={`inline-flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                  statusFilter === f.value ? 'bg-primary text-primary-foreground' : 'border border-border text-muted-foreground hover:bg-secondary'
                }`}>
                {f.label} <span className="rounded-full bg-background/20 px-1.5 py-0.5 text-[10px] font-mono">{f.count}</span>
              </button>
            ))}
          </div>

          <IncidentsTable incidents={filtered} />
        </>
      )}

      {/* Create Dialog */}
      {createOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setCreateOpen(false)}>
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-foreground">Create Incident</h2>
              <button onClick={() => setCreateOpen(false)} className="text-muted-foreground hover:text-foreground"><X className="h-5 w-5" /></button>
            </div>
            <div className="flex flex-col gap-4">
              <div>
                <label className="text-sm font-medium text-foreground">Title</label>
                <input placeholder="e.g. API Gateway 5xx spike" value={form.title} onChange={e => setForm({...form, title: e.target.value})}
                  className="mt-1 flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground">Service</label>
                <input placeholder="e.g. frontend-api" value={form.service} onChange={e => setForm({...form, service: e.target.value})}
                  className="mt-1 flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground">Severity</label>
                <select value={form.severity} onChange={e => setForm({...form, severity: e.target.value})}
                  className="mt-1 flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                  <option value="critical">Critical</option>
                  <option value="high">High</option>
                  <option value="medium">Medium</option>
                  <option value="low">Low</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground">Assigned To (optional)</label>
                <input placeholder="e.g. alice@example.com" value={form.assigned_to} onChange={e => setForm({...form, assigned_to: e.target.value})}
                  className="mt-1 flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button onClick={() => setCreateOpen(false)} className="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-secondary">Cancel</button>
              <button onClick={handleCreate} disabled={creating || !form.title.trim() || !form.service.trim()}
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                <Send className="h-4 w-4" /> Create
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
