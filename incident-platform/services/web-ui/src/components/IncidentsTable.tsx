import { Link } from 'react-router-dom'
import type { Incident } from '../types'

function timeAgo(dateStr: string) {
  const diffMs = Date.now() - new Date(dateStr).getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 60) return `${diffMin}m ago`
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return `${diffHr}h ago`
  return `${Math.floor(diffHr / 24)}d ago`
}

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

export default function IncidentsTable({ incidents }: { incidents: Incident[] }) {
  return (
    <div className="rounded-xl border border-border bg-card overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border">
            {['Incident', 'Severity', 'Status', 'Service', 'Assigned', 'Created'].map(h => (
              <th key={h} className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {incidents.map(inc => (
            <tr key={inc.id} className="border-b border-border hover:bg-secondary/50 transition-colors">
              <td className="px-4 py-3">
                <Link to={`/incidents/${inc.id}`} className="font-medium text-foreground hover:text-primary">
                  {inc.title}
                </Link>
                <p className="mt-0.5 font-mono text-xs text-muted-foreground">{inc.id}</p>
              </td>
              <td className="px-4 py-3">
                <span className={`inline-flex rounded-full border px-2 py-0.5 text-xs font-medium ${sevColors[inc.severity] ?? ''}`}>
                  {inc.severity}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className={`inline-flex rounded-full px-2 py-0.5 text-xs font-medium ${statusColors[inc.status] ?? ''}`}>
                  {inc.status.replace('_', ' ')}
                </span>
              </td>
              <td className="px-4 py-3">
                <span className="rounded-md bg-secondary px-2 py-1 font-mono text-xs text-secondary-foreground">{inc.service}</span>
              </td>
              <td className="px-4 py-3 text-sm text-muted-foreground">{inc.assigned_to || 'Unassigned'}</td>
              <td className="px-4 py-3 text-sm text-muted-foreground">{timeAgo(inc.created_at)}</td>
            </tr>
          ))}
          {incidents.length === 0 && (
            <tr><td colSpan={6} className="py-12 text-center text-muted-foreground">No incidents found.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
