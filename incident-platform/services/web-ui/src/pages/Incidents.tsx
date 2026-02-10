import { useState, useEffect, useMemo } from 'react'
import { fetchIncidents } from '../api-client'
import type { Incident } from '../types'
import IncidentsTable from '../components/IncidentsTable'
import { Search, Loader2 } from 'lucide-react'

export default function Incidents() {
  const [incidents, setIncidents] = useState<Incident[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('all')
  const [search, setSearch] = useState('')

  useEffect(() => {
    let mounted = true
    const load = async () => {
      try {
        const data = await fetchIncidents()
        if (mounted) { setIncidents(data); setError(null) }
      } catch (e: any) { if (mounted) setError(e.message) }
      finally { if (mounted) setLoading(false) }
    }
    load()
    const id = setInterval(load, 10000)
    return () => { mounted = false; clearInterval(id) }
  }, [])

  const filtered = useMemo(() => {
    let r = incidents
    if (statusFilter !== 'all') r = r.filter(i => i.status === statusFilter)
    if (search.trim()) {
      const q = search.toLowerCase()
      r = r.filter(i => i.title.toLowerCase().includes(q) || i.service.toLowerCase().includes(q) || i.id.toLowerCase().includes(q))
    }
    return r
  }, [incidents, statusFilter, search])

  const statuses = ['all', 'open', 'acknowledged', 'in_progress', 'resolved']

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Incidents</h1>
        <p className="mt-1 text-sm text-muted-foreground">Manage and track all incidents across your services</p>
      </div>

      {error && <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}

      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
        <div className="flex items-center gap-2">
          {statuses.map(s => (
            <button key={s} onClick={() => setStatusFilter(s)}
              className={`rounded-md px-3 py-1.5 text-sm font-medium transition-colors ${
                statusFilter === s ? 'bg-primary text-primary-foreground' : 'border border-border text-muted-foreground hover:bg-secondary'
              }`}>
              {s === 'in_progress' ? 'In Progress' : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
        <div className="relative w-full sm:w-72">
          <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
          <input placeholder="Search incidents…" value={search} onChange={e => setSearch(e.target.value)}
            className="h-10 w-full rounded-md border border-border bg-secondary pl-9 pr-3 text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
        </div>
      </div>

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /><span className="ml-2 text-sm text-muted-foreground">Loading…</span></div>
      ) : (
        <IncidentsTable incidents={filtered} />
      )}
    </div>
  )
}
