import { useState, useEffect } from 'react'
import {
  fetchSchedules, createSchedule, deleteSchedule,
  fetchCurrentOnCall, setOverride, removeOverride,
  triggerEscalation, fetchEscalations,
} from '../api-client'
import type { OnCallSchedule, CurrentOnCall, EscalationLog } from '../types'
import { Phone, User, Users, Calendar, Shield, Loader2, Plus, Trash2, UserCog, AlertTriangle, X } from 'lucide-react'

function timeAgo(d: string) {
  const m = Math.floor((Date.now() - new Date(d).getTime()) / 60000)
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  return `${Math.floor(h / 24)}d ago`
}

export default function OnCall() {
  const [schedules, setSchedules] = useState<OnCallSchedule[]>([])
  const [escalations, setEscalations] = useState<EscalationLog[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<'current' | 'schedules' | 'escalations'>('current')
  const [createOpen, setCreateOpen] = useState(false)

  async function load() {
    try {
      const [s, e] = await Promise.all([fetchSchedules(), fetchEscalations()])
      setSchedules(s); setEscalations(e); setError(null)
    } catch (e: any) { setError(e.message) }
    finally { setLoading(false) }
  }

  useEffect(() => { load(); const id = setInterval(load, 30000); return () => clearInterval(id) }, [])

  const teams = schedules.map(s => s.team)

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">On-Call</h1>
          <p className="mt-1 text-sm text-muted-foreground">Manage rotations, overrides, and escalations</p>
        </div>
        <button onClick={() => setCreateOpen(true)} className="inline-flex items-center gap-1.5 rounded-md bg-primary px-3 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90">
          <Plus className="h-4 w-4" /> New Schedule
        </button>
      </div>

      {error && <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">{error}</div>}

      {loading ? (
        <div className="flex items-center justify-center py-12"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>
      ) : (
        <>
          {/* Tabs */}
          <div className="flex items-center gap-1 border-b border-border">
            {([
              { key: 'current', label: 'Currently On-Call' },
              { key: 'schedules', label: `Schedules (${schedules.length})` },
              { key: 'escalations', label: `Escalations (${escalations.length})` },
            ] as const).map(t => (
              <button key={t.key} onClick={() => setTab(t.key)}
                className={`px-4 py-2 text-sm font-medium transition-colors ${
                  tab === t.key ? 'border-b-2 border-primary text-primary' : 'text-muted-foreground hover:text-foreground'
                }`}>{t.label}</button>
            ))}
          </div>

          {tab === 'current' && (
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {teams.map(team => <CurrentOnCallCard key={team} team={team} onRefresh={load} />)}
              {teams.length === 0 && <p className="col-span-full py-12 text-center text-muted-foreground">No schedules yet. Create one to get started.</p>}
            </div>
          )}

          {tab === 'schedules' && (
            <div className="flex flex-col gap-4">
              {schedules.map(s => <ScheduleCard key={s.team} schedule={s} onRefresh={load} />)}
              {schedules.length === 0 && <p className="py-12 text-center text-muted-foreground">No schedules configured yet.</p>}
            </div>
          )}

          {tab === 'escalations' && <EscalationHistory escalations={escalations} />}
        </>
      )}

      {/* Create Schedule Dialog */}
      {createOpen && <CreateScheduleDialog onClose={() => setCreateOpen(false)} onCreated={load} />}
    </div>
  )
}

function CurrentOnCallCard({ team, onRefresh }: { team: string; onRefresh: () => void }) {
  const [current, setCurrent] = useState<CurrentOnCall | null>(null)
  const [loading, setLoading] = useState(true)
  const [overrideOpen, setOverrideOpen] = useState(false)
  const [escalateOpen, setEscalateOpen] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', reason: '' })
  const [escForm, setEscForm] = useState({ incident_id: '', reason: '' })
  const [submitting, setSubmitting] = useState(false)

  async function load() {
    try { setCurrent(await fetchCurrentOnCall(team)) } catch { /* ignore */ }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [team])

  async function handleOverride() {
    if (!form.name.trim() || !form.email.trim()) return
    setSubmitting(true)
    try { await setOverride({ team, user_name: form.name.trim(), user_email: form.email.trim(), reason: form.reason.trim() || undefined }); setOverrideOpen(false); load() }
    catch (e) { console.error(e) } finally { setSubmitting(false) }
  }

  async function handleRemoveOverride() {
    setSubmitting(true)
    try { await removeOverride(team); load() } catch (e) { console.error(e) } finally { setSubmitting(false) }
  }

  async function handleEscalate() {
    if (!escForm.incident_id.trim()) return
    setSubmitting(true)
    try { await triggerEscalation({ team, incident_id: escForm.incident_id.trim(), reason: escForm.reason.trim() || undefined }); setEscalateOpen(false); onRefresh() }
    catch (e) { console.error(e) } finally { setSubmitting(false) }
  }

  if (loading) return <div className="rounded-xl border border-border bg-card p-8 flex items-center justify-center"><Loader2 className="h-5 w-5 animate-spin text-muted-foreground" /></div>
  if (!current) return null

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-medium text-foreground">{team.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</h3>
        <div className="flex gap-1">
          <button onClick={() => setOverrideOpen(true)} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary" title="Set override"><UserCog className="h-3.5 w-3.5" /></button>
          <button onClick={() => setEscalateOpen(true)} className="rounded-md p-1.5 text-muted-foreground hover:bg-secondary" title="Escalate"><AlertTriangle className="h-3.5 w-3.5" /></button>
        </div>
      </div>

      {/* Primary */}
      <div className="flex items-center gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3 mb-2">
        <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10"><Shield className="h-4 w-4 text-primary" /></div>
        <div className="flex-1">
          <span className="text-xs font-medium uppercase tracking-wider text-primary">
            Primary {current.primary.override && <span className="ml-1 rounded border border-yellow-500/30 px-1 text-[10px] text-yellow-400">Override</span>}
          </span>
          <p className="text-sm font-medium text-foreground">{current.primary.name}</p>
          <p className="text-xs text-muted-foreground">{current.primary.email}</p>
          {current.primary.reason && <p className="mt-0.5 text-xs italic text-muted-foreground">{current.primary.reason}</p>}
        </div>
        <div className="flex flex-col items-end gap-1">
          <Phone className="h-4 w-4 text-muted-foreground" />
          {current.primary.override && (
            <button onClick={handleRemoveOverride} disabled={submitting} className="rounded-md p-1 text-destructive hover:bg-destructive/10" title="Remove override"><X className="h-3 w-3" /></button>
          )}
        </div>
      </div>

      {/* Secondary */}
      {current.secondary && (
        <div className="flex items-center gap-3 rounded-lg border border-border bg-secondary/50 p-3">
          <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary"><User className="h-4 w-4 text-muted-foreground" /></div>
          <div>
            <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Secondary</span>
            <p className="text-sm font-medium text-foreground">{current.secondary.name}</p>
            <p className="text-xs text-muted-foreground">{current.secondary.email}</p>
          </div>
        </div>
      )}

      {/* Override Dialog */}
      {overrideOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setOverrideOpen(false)}>
          <div className="w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="mb-3 text-lg font-semibold text-foreground">Set On-Call Override</h3>
            <p className="mb-4 text-sm text-muted-foreground">Temporarily replace the primary on-call for {team}.</p>
            <div className="flex flex-col gap-3">
              <input placeholder="Name" value={form.name} onChange={e => setForm({...form, name: e.target.value})}
                className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              <input placeholder="Email" value={form.email} onChange={e => setForm({...form, email: e.target.value})}
                className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              <input placeholder="Reason (optional)" value={form.reason} onChange={e => setForm({...form, reason: e.target.value})}
                className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setOverrideOpen(false)} className="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-secondary">Cancel</button>
              <button onClick={handleOverride} disabled={submitting} className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">Apply Override</button>
            </div>
          </div>
        </div>
      )}

      {/* Escalate Dialog */}
      {escalateOpen && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={() => setEscalateOpen(false)}>
          <div className="w-full max-w-sm rounded-xl border border-border bg-card p-6 shadow-xl" onClick={e => e.stopPropagation()}>
            <h3 className="mb-3 text-lg font-semibold text-foreground">Trigger Escalation</h3>
            <p className="mb-4 text-sm text-muted-foreground">Escalate an incident to the next responder on {team}.</p>
            <div className="flex flex-col gap-3">
              <input placeholder="Incident ID" value={escForm.incident_id} onChange={e => setEscForm({...escForm, incident_id: e.target.value})}
                className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
              <input placeholder="Reason (optional)" value={escForm.reason} onChange={e => setEscForm({...escForm, reason: e.target.value})}
                className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>
            <div className="mt-4 flex justify-end gap-2">
              <button onClick={() => setEscalateOpen(false)} className="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-secondary">Cancel</button>
              <button onClick={handleEscalate} disabled={submitting || !escForm.incident_id.trim()}
                className="rounded-md bg-destructive px-4 py-2 text-sm font-medium text-destructive-foreground hover:bg-destructive/90 disabled:opacity-50">Escalate</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function ScheduleCard({ schedule, onRefresh }: { schedule: OnCallSchedule; onRefresh: () => void }) {
  const [deleting, setDeleting] = useState(false)

  async function handleDelete() {
    if (!confirm('Delete schedule for ' + schedule.team + '?')) return
    setDeleting(true)
    try { await deleteSchedule(schedule.team); onRefresh() } catch (e) { console.error(e) }
    finally { setDeleting(false) }
  }

  return (
    <div className="rounded-xl border border-border bg-card p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary"><Users className="h-4 w-4 text-muted-foreground" /></div>
        <div className="flex-1">
          <h3 className="text-sm font-medium text-foreground">{schedule.team.replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}</h3>
          <p className="flex items-center gap-1 text-xs text-muted-foreground"><Calendar className="h-3 w-3" />{schedule.rotation_type} rotation</p>
        </div>
        <button onClick={handleDelete} disabled={deleting} className="rounded-md p-2 text-destructive hover:bg-destructive/10" title="Delete schedule">
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
      <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
        {schedule.members.map(m => (
          <div key={m.email} className="flex items-center gap-3 rounded-lg border border-border bg-secondary/30 px-3 py-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-medium text-foreground">
              {m.name.split(' ').map(n => n[0]).join('')}
            </div>
            <div className="flex-1">
              <p className="text-sm text-foreground">{m.name}</p>
              <p className="text-xs text-muted-foreground">{m.email}</p>
            </div>
            <span className={`rounded-full border border-border px-2 py-0.5 text-xs font-medium ${m.role === 'primary' ? 'text-primary' : 'text-muted-foreground'}`}>{m.role}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

function CreateScheduleDialog({ onClose, onCreated }: { onClose: () => void; onCreated: () => void }) {
  const [submitting, setSubmitting] = useState(false)
  const [team, setTeam] = useState('')
  const [rotationType, setRotationType] = useState('weekly')
  const [members, setMembers] = useState([{ name: '', email: '', role: 'primary' }, { name: '', email: '', role: 'secondary' }])

  function updateMember(i: number, field: string, value: string) {
    setMembers(prev => prev.map((m, idx) => idx === i ? { ...m, [field]: value } : m))
  }

  async function handleCreate() {
    const valid = members.filter(m => m.name.trim() && m.email.trim())
    if (!team.trim() || valid.length === 0) return
    setSubmitting(true)
    try {
      await createSchedule({ team: team.trim(), rotation_type: rotationType, members: valid.map(m => ({ name: m.name.trim(), email: m.email.trim(), role: m.role })) })
      onCreated(); onClose()
    } catch (e) { console.error(e) }
    finally { setSubmitting(false) }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={onClose}>
      <div className="w-full max-w-lg rounded-xl border border-border bg-card p-6 shadow-xl" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold text-foreground">Create On-Call Schedule</h2>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground"><X className="h-5 w-5" /></button>
        </div>
        <div className="flex flex-col gap-4">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium text-foreground">Team Name</label>
              <input placeholder="e.g. platform-team" value={team} onChange={e => setTeam(e.target.value)}
                className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
            </div>
            <div className="w-40">
              <label className="mb-1 block text-sm font-medium text-foreground">Rotation</label>
              <select value={rotationType} onChange={e => setRotationType(e.target.value)}
                className="h-10 w-full rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                <option value="daily">Daily</option><option value="weekly">Weekly</option><option value="biweekly">Biweekly</option>
              </select>
            </div>
          </div>
          <div>
            <label className="mb-2 block text-sm font-medium text-foreground">Members</label>
            <div className="flex flex-col gap-2">
              {members.map((m, i) => (
                <div key={i} className="flex items-center gap-2">
                  <input placeholder="Name" value={m.name} onChange={e => updateMember(i, 'name', e.target.value)}
                    className="h-10 flex-1 rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
                  <input placeholder="Email" value={m.email} onChange={e => updateMember(i, 'email', e.target.value)}
                    className="h-10 flex-1 rounded-md border border-border bg-background px-3 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary" />
                  <select value={m.role} onChange={e => updateMember(i, 'role', e.target.value)}
                    className="h-10 w-28 rounded-md border border-border bg-background px-2 text-sm text-foreground focus:outline-none focus:ring-2 focus:ring-primary">
                    <option value="primary">Primary</option><option value="secondary">Secondary</option>
                  </select>
                  {members.length > 1 && (
                    <button onClick={() => setMembers(prev => prev.filter((_, idx) => idx !== i))} className="rounded-md p-2 text-destructive hover:bg-destructive/10">
                      <X className="h-3.5 w-3.5" />
                    </button>
                  )}
                </div>
              ))}
              <button onClick={() => setMembers(prev => [...prev, { name: '', email: '', role: 'secondary' }])}
                className="mt-1 inline-flex w-fit items-center gap-1 rounded-md border border-border px-3 py-1.5 text-sm text-muted-foreground hover:bg-secondary">
                <Plus className="h-3.5 w-3.5" /> Add Member
              </button>
            </div>
          </div>
        </div>
        <div className="mt-6 flex justify-end gap-2">
          <button onClick={onClose} className="rounded-md border border-border px-4 py-2 text-sm text-muted-foreground hover:bg-secondary">Cancel</button>
          <button onClick={handleCreate} disabled={submitting || !team.trim()}
            className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground hover:bg-primary/90 disabled:opacity-50">Create Schedule</button>
        </div>
      </div>
    </div>
  )
}

function EscalationHistory({ escalations }: { escalations: EscalationLog[] }) {
  if (escalations.length === 0) return <p className="py-12 text-center text-muted-foreground">No escalations recorded yet.</p>

  return (
    <div className="rounded-xl border border-border bg-card overflow-x-auto">
      <table className="w-full text-left">
        <thead>
          <tr className="border-b border-border">
            {['Team', 'Incident', 'Escalated To', 'Reason', 'When'].map(h => (
              <th key={h} className="px-4 py-3 text-xs font-medium uppercase tracking-wider text-muted-foreground">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {escalations.map(esc => (
            <tr key={esc.escalation_id} className="border-b border-border hover:bg-secondary/50">
              <td className="px-4 py-3 text-sm font-medium text-foreground">{esc.team}</td>
              <td className="px-4 py-3 font-mono text-xs text-muted-foreground">{esc.incident_id.slice(0, 8)}</td>
              <td className="px-4 py-3 text-sm text-foreground">{esc.escalated_to ? esc.escalated_to.name : '—'}</td>
              <td className="px-4 py-3 max-w-[200px] truncate text-sm text-muted-foreground">{esc.reason || '—'}</td>
              <td className="px-4 py-3 text-sm text-muted-foreground">{timeAgo(esc.timestamp)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
