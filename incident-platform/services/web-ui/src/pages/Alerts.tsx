import { useState, useEffect, useMemo } from 'react'
import { Link } from 'react-router-dom'
import { fetchAlerts, ingestAlert, fetchSchedules } from '../api-client'
import type { Alert } from '../types'
import { Zap, Search, Loader2, Plus, Send, X, Link as LinkIcon } from 'lucide-react'

const sevColors: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  low: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
}

function timeAgo(d: string) {
  const m = Math.floor((Date.now() - new Date(d).getTime()) / 60000)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function Alerts() {
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [sevFilter, setSevFilter] = useState('all')
  const [dialogOpen, setDialogOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [form, setForm] = useState({ service: '', severity: 'medium', message: '', source: 'manual' })
  const [teams, setTeams] = useState<string[]>([])

  async function load() {
    try { const data = await fetchAlerts(); setAlerts(data); setError(null) }
    catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => {
    load()
    fetchSchedules().then(s => setTeams(s.map(x => x.team))).catch(() => {})
    const id = setInterval(load, 10000); return () => clearInterval(id)
  }, [])

  const filtered = useMemo(() => {
    let r = alerts
    if (sevFilter !== 'all') r = r.filter(a => a.severity === sevFilter)
    if (search.trim()) {
      const q = search.toLowerCase()
      r = r.filter(a => a.message.toLowerCase().includes(q) || a.service.toLowerCase().includes(q) || a.id.toLowerCase().includes(q))
    }
    return r
  }, [alerts, sevFilter, search])

  const counts = useMemo(() => ({
    critical: alerts.filter(a => a.severity === 'critical').length,
    high: alerts.filter(a => a.severity === 'high').length,
    medium: alerts.filter(a => a.severity === 'medium').length,
    low: alerts.filter(a => a.severity === 'low').length,
  }), [alerts])

  async function handleIngest() {
    if (!form.service.trim() || !form.message.trim()) return
    setSubmitting(true)
    try {
      await ingestAlert({ service: form.service.trim(), severity: form.severity, message: form.message.trim(), source: form.source.trim() || 'manual' })
      setDialogOpen(false)
      setForm({ service: '', severity: 'medium', message: '', source: 'manual' })
      load()
    } catch (e) { console.error(e) }
    finally { setSubmitting(false) }
  }

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">Alerts</h1>
          <p className="mt-1 text-sm text-muted-foreground">Raw alerts ingested from monitoring systems — correlated into incidents</p>
        </div>
        <button onClick={() => setDialogOpen(true)} className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
          <Plus className="h-4 w-4" /> Ingest Alert
        </button>
      </div>

      {error && <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}

      {/* Severity Summary */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        {(['critical', 'high', 'medium', 'low'] as const).map(sev => (
          <div key={sev} onClick={() => setSevFilter(sevFilter === sev ? 'all' : sev)}
            className={`cursor-pointer rounded-xl border border-border bg-card p-4 transition-colors hover:bg-secondary/50 ${sevFilter === sev ? 'ring-2 ring-primary' : ''}`}>
            <div className="flex items-center gap-3">
              <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${sevColors[sev]}`}>{sev}</span>
              <span className="text-xl font-semibold text-foreground">{counts[sev]}</span>
            </div>
          </div>
        ))}
      </div>

      {/* Search */}
      <div className="relative w-full sm:w-72">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <input placeholder="Search alerts…" value={search} onChange={e => setSearch(e.target.value)}
          className="h-10 w-full rounded-md border border-border bg-secondary pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /><span className="ml-2 text-sm text-muted-foreground">Loading…</span></div>
      ) : (
        <div className="rounded-xl border border-border bg-card overflow-x-auto">
          <table className="w-full text-left">
            <thead>
              <tr className="border-b border-border">
                {['Alert', 'Severity', 'Service', 'Source', 'Incident', 'Time'].map(h => (
                  <th key={h} className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map(alert => (
                <tr key={alert.id} className="border-b border-border hover:bg-secondary/50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="text-sm font-medium text-foreground">{alert.message}</p>
                    <p className="mt-0.5 font-mono text-xs text-muted-foreground">
                      {alert.id.slice(0, 8)}{alert.fingerprint && <span className="ml-2">fp:{alert.fingerprint}</span>}
                    </p>
                  </td>
                  <td className="px-4 py-3"><span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${sevColors[alert.severity]}`}>{alert.severity}</span></td>
                  <td className="px-4 py-3"><span className="rounded-md bg-secondary px-2 py-1 font-mono text-xs text-secondary-foreground">{alert.service}</span></td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{alert.source}</td>
                  <td className="px-4 py-3">
                    {alert.incident_id ? (
                      <Link to={`/incidents/${alert.incident_id}`} className="flex items-center gap-1 text-xs text-primary hover:underline">
                        <LinkIcon className="h-3 w-3" />{alert.incident_id.slice(0, 8)}
                      </Link>
                    ) : <span className="text-xs text-muted-foreground">—</span>}
                  </td>
                  <td className="px-4 py-3 text-sm text-muted-foreground">{timeAgo(alert.created_at)}</td>
                </tr>
              ))}
              {filtered.length === 0 && <tr><td colSpan={6} className="py-12 text-center text-muted-foreground">No alerts found.</td></tr>}
            </tbody>
          </table>
        </div>
      )}

      {/* Ingest Dialog */}
      {dialogOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setDialogOpen(false)}>
          <div className="w-full max-w-md rounded-xl border border-border bg-card p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-lg font-semibold text-foreground">Ingest New Alert</h2>
              <button onClick={() => setDialogOpen(false)} className="text-muted-foreground hover:text-foreground"><X className="h-5 w-5" /></button>
            </div>
            <p className="mb-4 text-sm text-muted-foreground">Manually send an alert to the ingestion service. It will be deduplicated and correlated to an incident automatically.</p>
            <div className="flex flex-col gap-4">
              <div>
                <label className="text-sm font-medium text-foreground">Service</label>
                <select value={form.service} onChange={e => setForm({...form, service: e.target.value})}
                  className="mt-1 flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                  <option value="">Select a service…</option>
                  {teams.map(t => <option key={t} value={t}>{t}</option>)}
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground">Severity</label>
                <select value={form.severity} onChange={e => setForm({...form, severity: e.target.value})}
                  className="mt-1 flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                  <option value="critical">Critical</option><option value="high">High</option><option value="medium">Medium</option><option value="low">Low</option>
                </select>
              </div>
              <div>
                <label className="text-sm font-medium text-foreground">Message</label>
                <textarea placeholder="e.g. HTTP 5xx error rate > 10%" value={form.message} onChange={e => setForm({...form, message: e.target.value})}
                  className="mt-1 min-h-[80px] w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              </div>
              <div>
                <label className="text-sm font-medium text-foreground">Source</label>
                <select value={form.source} onChange={e => setForm({...form, source: e.target.value})}
                  className="mt-1 flex h-10 w-full rounded-md border border-border bg-background px-3 py-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                  <option value="manual">Manual</option>
                  <option value="prometheus">Prometheus</option>
                  <option value="grafana">Grafana</option>
                  <option value="datadog">Datadog</option>
                  <option value="cloudwatch">CloudWatch</option>
                  <option value="pagerduty">PagerDuty</option>
                </select>
              </div>
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button onClick={() => setDialogOpen(false)} className="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-secondary">Cancel</button>
              <button onClick={handleIngest} disabled={submitting || !form.service.trim() || !form.message.trim()}
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                <Send className="h-4 w-4" /> Ingest
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
