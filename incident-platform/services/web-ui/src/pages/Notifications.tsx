import { useState, useEffect } from 'react'
import { fetchNotifications } from '../api-client'
import type { NotificationLog } from '../types'
import { Bell, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react'

function fmtDate(d: string) {
  return new Date(d).toLocaleString('en-US', { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })
}

export default function Notifications() {
  const [notifications, setNotifications] = useState<NotificationLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let mounted = true
    const load = async () => {
      try { const data = await fetchNotifications(); if (mounted) { setNotifications(data); setError(null) } }
      catch (e: any) { if (mounted) setError(e.message) }
      finally { if (mounted) setLoading(false) }
    }
    load()
    const id = setInterval(load, 10000)
    return () => { mounted = false; clearInterval(id) }
  }, [])

  const sent = notifications.filter(n => n.status === 'sent').length
  const failed = notifications.filter(n => n.status === 'failed').length

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Notifications</h1>
        <p className="mt-1 text-sm text-muted-foreground">Notification delivery log for incident alerts and escalations</p>
      </div>

      {error && <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /><span className="ml-2 text-sm text-muted-foreground">Loading…</span></div>
      ) : (
        <>
          {/* Stats */}
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10"><Bell className="h-5 w-5 text-primary" /></div>
              <div><p className="text-2xl font-semibold text-foreground">{notifications.length}</p><p className="text-xs text-muted-foreground">Total Sent</p></div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10"><CheckCircle className="h-5 w-5 text-indigo-400" /></div>
              <div><p className="text-2xl font-semibold text-foreground">{sent}</p><p className="text-xs text-muted-foreground">Delivered</p></div>
            </div>
            <div className="rounded-xl border border-border bg-card p-4 flex items-center gap-4">
              <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/10"><XCircle className="h-5 w-5 text-red-400" /></div>
              <div><p className="text-2xl font-semibold text-foreground">{failed}</p><p className="text-xs text-muted-foreground">Failed</p></div>
            </div>
          </div>

          {/* Log */}
          <div className="rounded-xl border border-border bg-card p-5">
            <h3 className="mb-3 text-sm font-medium text-foreground">Delivery Log</h3>
            <div className="flex flex-col gap-3">
              {notifications.length > 0 ? notifications.map(n => (
                <div key={n.id} className="flex items-center gap-4 rounded-lg border border-border bg-secondary/30 p-4">
                  <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary">
                    {n.status === 'sent' ? <CheckCircle className="h-4 w-4 text-indigo-400" /> : <XCircle className="h-4 w-4 text-red-400" />}
                  </div>
                  <div className="flex-1">
                    <p className="text-sm text-foreground">{n.message}</p>
                    <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                      <span>To: {n.recipient}</span>
                      <span>Incident: {n.incident_id}</span>
                    </div>
                  </div>
                  <div className="flex flex-col items-end gap-1">
                    <span className={`inline-flex rounded-full border border-border px-2 py-0.5 text-xs font-medium ${
                      n.channel === 'webhook' ? 'text-blue-400' : 'text-muted-foreground'
                    }`}>{n.channel}</span>
                    <span className="flex items-center gap-1 text-xs text-muted-foreground"><Clock className="h-3 w-3" />{fmtDate(n.created_at)}</span>
                  </div>
                </div>
              )) : (
                <p className="py-8 text-center text-muted-foreground">No notifications have been sent yet.</p>
              )}
            </div>
          </div>
        </>
      )}
    </div>
  )
}
