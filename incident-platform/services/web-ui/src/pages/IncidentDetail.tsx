import { useState, useEffect } from 'react'
import { useParams, Link } from 'react-router-dom'
import { fetchIncident, updateIncident } from '../api-client'
import type { Incident, IncidentStatus } from '../types'
import { ArrowLeft, CheckCircle, Clock, User, AlertTriangle, MessageSquare, Activity, Loader2, XCircle } from 'lucide-react'

const sevColors: Record<string, string> = {
  critical: 'bg-red-500/10 text-red-400 border-red-500/20',
  high: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  medium: 'bg-yellow-500/10 text-yellow-400 border-yellow-500/20',
  low: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
}
const statusColors: Record<string, string> = {
  open: 'bg-red-500/10 text-red-400',
  acknowledged: 'bg-yellow-500/10 text-yellow-400',
  in_progress: 'bg-blue-500/10 text-blue-400',
  resolved: 'bg-emerald-500/10 text-emerald-400',
}

function fmtDate(d: string) { return new Date(d).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' }) }
function fmtSec(s: number | null) {
  if (s === null) return '--'
  if (s < 60) return `${Math.round(s)}s`
  if (s < 3600) return `${Math.round(s / 60)}m ${Math.round(s % 60)}s`
  return `${Math.floor(s / 3600)}h ${Math.round((s % 3600) / 60)}m`
}

export default function IncidentDetail() {
  const { id } = useParams<{ id: string }>()
  const [incident, setIncident] = useState<Incident | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [noteText, setNoteText] = useState('')
  const [updating, setUpdating] = useState(false)

  async function load() {
    try {
      const data = await fetchIncident(id!)
      setIncident(data)
      setError(null)
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load(); const t = setInterval(load, 5000); return () => clearInterval(t) }, [id])

  async function handleStatus(status: IncidentStatus) {
    setUpdating(true)
    try { await updateIncident(id!, { status }); await load() } catch (e) { console.error(e) }
    finally { setUpdating(false) }
  }

  async function handleNote() {
    if (!noteText.trim()) return
    setUpdating(true)
    try { await updateIncident(id!, { note: { author: 'Operator', content: noteText.trim() } }); setNoteText(''); await load() }
    catch (e) { console.error(e) }
    finally { setUpdating(false) }
  }

  if (loading) return <div className="flex items-center justify-center py-20"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /><span className="ml-2 text-sm text-muted-foreground">Loading…</span></div>

  if (error || !incident) return (
    <div className="flex flex-col items-center justify-center gap-4 p-12">
      <AlertTriangle className="h-12 w-12 text-muted-foreground" />
      <h2 className="text-lg font-semibold text-foreground">{error ? 'Failed to load incident' : 'Incident not found'}</h2>
      <Link to="/incidents" className="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-secondary">Back to incidents</Link>
    </div>
  )

  const notes = incident.notes ?? []
  const timeline = [
    { time: incident.created_at, label: 'Incident created', icon: AlertTriangle, color: 'text-red-400' },
    ...(incident.acknowledged_at ? [{ time: incident.acknowledged_at, label: 'Acknowledged', icon: CheckCircle, color: 'text-yellow-400' }] : []),
    ...(incident.resolved_at ? [{ time: incident.resolved_at, label: 'Resolved', icon: CheckCircle, color: 'text-emerald-400' }] : []),
    ...notes.map(n => ({ time: n.created_at, label: `${n.author}: ${n.content}`, icon: MessageSquare, color: 'text-blue-400' })),
  ].sort((a, b) => new Date(a.time).getTime() - new Date(b.time).getTime())

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Back + Header */}
      <div className="flex flex-col gap-4">
        <Link to="/incidents" className="flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
          <ArrowLeft className="h-4 w-4" /> Back to incidents
        </Link>
        <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex flex-col gap-2">
            <h1 className="text-xl font-semibold text-foreground">{incident.title}</h1>
            <div className="flex items-center gap-3 flex-wrap">
              <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${sevColors[incident.severity]}`}>{incident.severity}</span>
              <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[incident.status]}`}>{incident.status.replace('_', ' ')}</span>
              <span className="rounded-md bg-secondary px-2 py-1 font-mono text-xs text-secondary-foreground">{incident.service}</span>
              <span className="font-mono text-xs text-muted-foreground">{incident.id}</span>
            </div>
          </div>
          <div className="flex items-center gap-2">
            {incident.status === 'open' && (
              <button onClick={() => handleStatus('acknowledged')} disabled={updating}
                className="inline-flex items-center gap-1.5 rounded-md border border-yellow-500/30 bg-yellow-500/10 px-3 py-2 text-sm font-medium text-yellow-400 hover:bg-yellow-500/20 disabled:opacity-50">
                <CheckCircle className="h-4 w-4" /> Acknowledge
              </button>
            )}
            {(incident.status === 'acknowledged' || incident.status === 'in_progress') && (
              <button onClick={() => handleStatus('resolved')} disabled={updating}
                className="inline-flex items-center gap-1.5 rounded-md border border-emerald-500/30 bg-emerald-500/10 px-3 py-2 text-sm font-medium text-emerald-400 hover:bg-emerald-500/20 disabled:opacity-50">
                <CheckCircle className="h-4 w-4" /> Resolve
              </button>
            )}
            {incident.status === 'acknowledged' && (
              <button onClick={() => handleStatus('in_progress')} disabled={updating}
                className="inline-flex items-center gap-1.5 rounded-md border border-border px-3 py-2 text-sm font-medium text-muted-foreground hover:bg-secondary disabled:opacity-50">
                <Activity className="h-4 w-4" /> In Progress
              </button>
            )}
          </div>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <div className="flex flex-col gap-6 lg:col-span-2">
          {/* Timeline */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="mb-4 text-sm font-medium text-foreground">Timeline</h3>
            <div className="flex flex-col gap-4">
              {timeline.map((evt, i) => (
                <div key={i} className="flex items-start gap-3">
                  <div className="mt-0.5 flex flex-col items-center">
                    <evt.icon className={`h-4 w-4 ${evt.color}`} />
                    {i < timeline.length - 1 && <div className="mt-1 h-8 w-px bg-border" />}
                  </div>
                  <div>
                    <p className="text-sm text-foreground">{evt.label}</p>
                    <p className="text-xs text-muted-foreground">{fmtDate(evt.time)}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Add Note */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="mb-3 text-sm font-medium text-foreground">Add Note</h3>
            <textarea placeholder="Add investigation notes…" value={noteText} onChange={e => setNoteText(e.target.value)}
              className="min-h-[80px] w-full rounded-md border border-border bg-secondary px-3 py-2 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
            <div className="mt-3 flex justify-end">
              <button onClick={handleNote} disabled={updating || !noteText.trim()}
                className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">
                <MessageSquare className="h-4 w-4" /> Add Note
              </button>
            </div>
          </div>

          {/* Linked Alerts */}
          {incident.alerts && incident.alerts.length > 0 && (
            <div className="rounded-xl border border-border bg-card p-5">
              <h3 className="mb-3 text-sm font-medium text-foreground">Linked Alerts ({incident.alerts.length})</h3>
              <div className="flex flex-col gap-2">
                {incident.alerts.map(alert => (
                  <div key={alert.id} className="flex items-center justify-between rounded-lg border border-border bg-secondary/50 px-4 py-3">
                    <div>
                      <p className="text-sm text-foreground">{alert.message}</p>
                      <p className="mt-0.5 font-mono text-xs text-muted-foreground">{alert.id}</p>
                    </div>
                    <div className="flex items-center gap-2">
                      <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${sevColors[alert.severity]}`}>{alert.severity}</span>
                      <span className="text-xs text-muted-foreground">{fmtDate(alert.timestamp)}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Right sidebar */}
        <div className="flex flex-col gap-4">
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="mb-3 text-sm font-medium text-foreground">Details</h3>
            <dl className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <dt className="flex items-center gap-1.5 text-xs text-muted-foreground"><User className="h-3.5 w-3.5" />Assigned to</dt>
                <dd className="text-sm text-foreground">{incident.assigned_to || 'Unassigned'}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="flex items-center gap-1.5 text-xs text-muted-foreground"><Clock className="h-3.5 w-3.5" />Created</dt>
                <dd className="text-sm text-foreground">{fmtDate(incident.created_at)}</dd>
              </div>
              {incident.acknowledged_at && (
                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-1.5 text-xs text-muted-foreground"><CheckCircle className="h-3.5 w-3.5" />Acknowledged</dt>
                  <dd className="text-sm text-foreground">{fmtDate(incident.acknowledged_at)}</dd>
                </div>
              )}
              {incident.resolved_at && (
                <div className="flex items-center justify-between">
                  <dt className="flex items-center gap-1.5 text-xs text-muted-foreground"><XCircle className="h-3.5 w-3.5" />Resolved</dt>
                  <dd className="text-sm text-foreground">{fmtDate(incident.resolved_at)}</dd>
                </div>
              )}
            </dl>
          </div>

          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="mb-3 text-sm font-medium text-foreground">Response Metrics</h3>
            <dl className="flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <dt className="text-xs text-muted-foreground">MTTA</dt>
                <dd className="font-mono text-lg font-semibold text-foreground">{fmtSec(incident.mtta_seconds)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-xs text-muted-foreground">MTTR</dt>
                <dd className="font-mono text-lg font-semibold text-foreground">{fmtSec(incident.mttr_seconds)}</dd>
              </div>
              <div className="flex items-center justify-between">
                <dt className="text-xs text-muted-foreground">Linked Alerts</dt>
                <dd className="font-mono text-lg font-semibold text-foreground">{incident.alerts?.length ?? 0}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  )
}
