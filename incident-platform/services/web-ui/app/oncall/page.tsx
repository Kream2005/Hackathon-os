"use client"

import { useState } from "react"
import useSWR, { mutate } from "swr"
import {
  fetcher,
  createSchedule,
  deleteSchedule,
  setOverride,
  removeOverride,
  triggerEscalation,
} from "@/lib/api-client"
import type {
  OnCallSchedule,
  CurrentOnCall,
  EscalationLog,
} from "@/lib/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import {
  Phone,
  User,
  Users,
  Calendar,
  Shield,
  Loader2,
  Plus,
  Trash2,
  UserCog,
  AlertTriangle,
  X,
} from "lucide-react"

function timeAgo(dateStr: string) {
  const now = new Date()
  const date = new Date(dateStr)
  const diffMs = now.getTime() - date.getTime()
  const diffMin = Math.floor(diffMs / 60000)
  if (diffMin < 60) return diffMin + "m ago"
  const diffHr = Math.floor(diffMin / 60)
  if (diffHr < 24) return diffHr + "h ago"
  return Math.floor(diffHr / 24) + "d ago"
}

export default function OnCallPage() {
  const {
    data: schedules,
    error: schedError,
    isLoading: schedLoading,
  } = useSWR<OnCallSchedule[]>("/api/v1/schedules", fetcher, {
    refreshInterval: 30000,
  })

  const { data: escalations } = useSWR<EscalationLog[]>(
    "/api/v1/escalations",
    fetcher,
    { refreshInterval: 30000 },
  )

  const teams = schedules?.map((s) => s.team) ?? []

  return (
    <div className="flex flex-col gap-6 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-foreground">On-Call</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Manage rotations, overrides, and escalations
          </p>
        </div>
        <CreateScheduleDialog />
      </div>

      {schedError && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load schedules. Make sure the API Gateway and On-Call Service are running.
        </div>
      )}

      {schedLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading schedules...</span>
        </div>
      )}

      {schedules && (
        <Tabs defaultValue="current" className="w-full">
          <TabsList>
            <TabsTrigger value="current">Currently On-Call</TabsTrigger>
            <TabsTrigger value="schedules">Schedules ({schedules.length})</TabsTrigger>
            <TabsTrigger value="escalations">
              Escalations ({escalations?.length ?? 0})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="current" className="mt-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-3">
              {teams.map((team) => (
                <CurrentOnCallCard key={team} team={team} />
              ))}
              {teams.length === 0 && (
                <p className="col-span-full py-12 text-center text-muted-foreground">
                  No schedules yet. Create one to get started.
                </p>
              )}
            </div>
          </TabsContent>

          <TabsContent value="schedules" className="mt-4 flex flex-col gap-4">
            {schedules.map((sched) => (
              <ScheduleCard key={sched.team} schedule={sched} />
            ))}
            {schedules.length === 0 && (
              <p className="py-12 text-center text-muted-foreground">
                No schedules configured yet.
              </p>
            )}
          </TabsContent>

          <TabsContent value="escalations" className="mt-4">
            <EscalationHistory escalations={escalations ?? []} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  )
}

function CurrentOnCallCard({ team }: { team: string }) {
  const { data: current, isLoading } = useSWR<CurrentOnCall>(
    "/api/v1/oncall/current?team=" + encodeURIComponent(team),
    fetcher,
    { refreshInterval: 30000 },
  )

  const [overrideOpen, setOverrideOpen] = useState(false)
  const [overrideName, setOverrideName] = useState("")
  const [overrideEmail, setOverrideEmail] = useState("")
  const [overrideReason, setOverrideReason] = useState("")
  const [submitting, setSubmitting] = useState(false)

  const [escalateOpen, setEscalateOpen] = useState(false)
  const [escalateIncident, setEscalateIncident] = useState("")
  const [escalateReason, setEscalateReason] = useState("")

  async function handleOverride() {
    if (!overrideName.trim() || !overrideEmail.trim()) return
    setSubmitting(true)
    try {
      await setOverride({
        team,
        user_name: overrideName.trim(),
        user_email: overrideEmail.trim(),
        reason: overrideReason.trim() || undefined,
      })
      mutate("/api/v1/oncall/current?team=" + encodeURIComponent(team))
      setOverrideOpen(false)
      setOverrideName("")
      setOverrideEmail("")
      setOverrideReason("")
    } catch (err) {
      console.error("Override failed:", err)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleRemoveOverride() {
    setSubmitting(true)
    try {
      await removeOverride(team)
      mutate("/api/v1/oncall/current?team=" + encodeURIComponent(team))
    } catch (err) {
      console.error("Remove override failed:", err)
    } finally {
      setSubmitting(false)
    }
  }

  async function handleEscalate() {
    if (!escalateIncident.trim()) return
    setSubmitting(true)
    try {
      await triggerEscalation({
        team,
        incident_id: escalateIncident.trim(),
        reason: escalateReason.trim() || undefined,
      })
      mutate("/api/v1/escalations")
      setEscalateOpen(false)
      setEscalateIncident("")
      setEscalateReason("")
    } catch (err) {
      console.error("Escalation failed:", err)
    } finally {
      setSubmitting(false)
    }
  }

  if (isLoading) {
    return (
      <Card className="border-border bg-card">
        <CardContent className="flex items-center justify-center py-8">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    )
  }

  if (!current) return null

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-sm font-medium text-foreground">
            {team.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
          </CardTitle>
          <div className="flex gap-1">
            <Dialog open={overrideOpen} onOpenChange={setOverrideOpen}>
              <DialogTrigger asChild>
                <Button variant="ghost" size="icon" className="h-7 w-7" title="Set override">
                  <UserCog className="h-3.5 w-3.5" />
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Set On-Call Override</DialogTitle>
                  <DialogDescription>
                    Temporarily replace the primary on-call for {team}.
                  </DialogDescription>
                </DialogHeader>
                <div className="flex flex-col gap-3 py-2">
                  <Input placeholder="Name" value={overrideName} onChange={(e) => setOverrideName(e.target.value)} />
                  <Input placeholder="Email" value={overrideEmail} onChange={(e) => setOverrideEmail(e.target.value)} />
                  <Input placeholder="Reason (optional)" value={overrideReason} onChange={(e) => setOverrideReason(e.target.value)} />
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setOverrideOpen(false)}>Cancel</Button>
                  <Button onClick={handleOverride} disabled={submitting}>Apply Override</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>

            <Dialog open={escalateOpen} onOpenChange={setEscalateOpen}>
              <DialogTrigger asChild>
                <Button variant="ghost" size="icon" className="h-7 w-7" title="Escalate">
                  <AlertTriangle className="h-3.5 w-3.5" />
                </Button>
              </DialogTrigger>
              <DialogContent>
                <DialogHeader>
                  <DialogTitle>Trigger Escalation</DialogTitle>
                  <DialogDescription>
                    Escalate an incident to the next responder on {team}.
                  </DialogDescription>
                </DialogHeader>
                <div className="flex flex-col gap-3 py-2">
                  <Input placeholder="Incident ID" value={escalateIncident} onChange={(e) => setEscalateIncident(e.target.value)} />
                  <Input placeholder="Reason (optional)" value={escalateReason} onChange={(e) => setEscalateReason(e.target.value)} />
                </div>
                <DialogFooter>
                  <Button variant="outline" onClick={() => setEscalateOpen(false)}>Cancel</Button>
                  <Button variant="destructive" onClick={handleEscalate} disabled={submitting || !escalateIncident.trim()}>Escalate</Button>
                </DialogFooter>
              </DialogContent>
            </Dialog>
          </div>
        </div>
      </CardHeader>
      <CardContent>
        <div className="flex flex-col gap-3">
          <div className="flex items-center gap-3 rounded-lg border border-primary/20 bg-primary/5 p-3">
            <div className="flex h-9 w-9 items-center justify-center rounded-full bg-primary/10">
              <Shield className="h-4 w-4 text-primary" />
            </div>
            <div className="flex flex-col">
              <span className="text-xs font-medium uppercase tracking-wider text-primary">
                Primary
                {current.primary.override && (
                  <Badge variant="outline" className="ml-2 text-[10px] text-yellow-600 dark:text-yellow-400">Override</Badge>
                )}
              </span>
              <span className="text-sm font-medium text-foreground">{current.primary.name}</span>
              <span className="text-xs text-muted-foreground">{current.primary.email}</span>
              {current.primary.reason && (
                <span className="mt-0.5 text-xs italic text-muted-foreground">{current.primary.reason}</span>
              )}
            </div>
            <div className="ml-auto flex flex-col items-end gap-1">
              <Phone className="h-4 w-4 text-muted-foreground" />
              {current.primary.override && (
                <Button variant="ghost" size="icon" className="h-6 w-6 text-destructive hover:text-destructive" title="Remove override" onClick={handleRemoveOverride} disabled={submitting}>
                  <X className="h-3 w-3" />
                </Button>
              )}
            </div>
          </div>

          {current.secondary && (
            <div className="flex items-center gap-3 rounded-lg border border-border bg-secondary/50 p-3">
              <div className="flex h-9 w-9 items-center justify-center rounded-full bg-secondary">
                <User className="h-4 w-4 text-muted-foreground" />
              </div>
              <div className="flex flex-col">
                <span className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Secondary</span>
                <span className="text-sm font-medium text-foreground">{current.secondary.name}</span>
                <span className="text-xs text-muted-foreground">{current.secondary.email}</span>
              </div>
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

function ScheduleCard({ schedule }: { schedule: OnCallSchedule }) {
  const [deleting, setDeleting] = useState(false)

  async function handleDelete() {
    if (!confirm("Delete schedule for " + schedule.team + "?")) return
    setDeleting(true)
    try {
      await deleteSchedule(schedule.team)
      mutate("/api/v1/schedules")
    } catch (err) {
      console.error("Delete failed:", err)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <Card className="border-border bg-card">
      <CardHeader className="pb-3">
        <div className="flex items-center gap-3">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary">
            <Users className="h-4 w-4 text-muted-foreground" />
          </div>
          <div className="flex-1">
            <CardTitle className="text-sm font-medium text-foreground">
              {schedule.team.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
            </CardTitle>
            <p className="flex items-center gap-1 text-xs text-muted-foreground">
              <Calendar className="h-3 w-3" />
              {schedule.rotation_type} rotation
            </p>
          </div>
          <Button variant="ghost" size="icon" className="h-8 w-8 text-destructive hover:text-destructive" onClick={handleDelete} disabled={deleting} title="Delete schedule">
            <Trash2 className="h-4 w-4" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2 lg:grid-cols-3">
          {schedule.members.map((member) => (
            <div key={member.email} className="flex items-center gap-3 rounded-lg border border-border bg-secondary/30 px-3 py-2.5">
              <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary text-xs font-medium text-foreground">
                {member.name.split(" ").map((n) => n[0]).join("")}
              </div>
              <div className="flex flex-col">
                <span className="text-sm text-foreground">{member.name}</span>
                <span className="text-xs text-muted-foreground">{member.email}</span>
              </div>
              <Badge variant="outline" className={member.role === "primary" ? "ml-auto text-primary" : "ml-auto text-muted-foreground"}>
                {member.role}
              </Badge>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}

function CreateScheduleDialog() {
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [team, setTeam] = useState("")
  const [rotationType, setRotationType] = useState("weekly")
  const [members, setMembers] = useState([
    { name: "", email: "", role: "primary" },
    { name: "", email: "", role: "secondary" },
  ])

  function updateMember(idx: number, field: string, value: string) {
    setMembers((prev) => prev.map((m, i) => (i === idx ? { ...m, [field]: value } : m)))
  }

  function addMember() {
    setMembers((prev) => [...prev, { name: "", email: "", role: "secondary" }])
  }

  function removeMember(idx: number) {
    setMembers((prev) => prev.filter((_, i) => i !== idx))
  }

  async function handleCreate() {
    const validMembers = members.filter((m) => m.name.trim() && m.email.trim())
    if (!team.trim() || validMembers.length === 0) return
    setSubmitting(true)
    try {
      await createSchedule({
        team: team.trim(),
        rotation_type: rotationType,
        members: validMembers.map((m) => ({ name: m.name.trim(), email: m.email.trim(), role: m.role })),
      })
      mutate("/api/v1/schedules")
      setOpen(false)
      setTeam("")
      setRotationType("weekly")
      setMembers([
        { name: "", email: "", role: "primary" },
        { name: "", email: "", role: "secondary" },
      ])
    } catch (err) {
      console.error("Create schedule failed:", err)
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button className="gap-1.5">
          <Plus className="h-4 w-4" />
          New Schedule
        </Button>
      </DialogTrigger>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Create On-Call Schedule</DialogTitle>
          <DialogDescription>Set up a new rotation for a team.</DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-4 py-2">
          <div className="flex gap-3">
            <div className="flex-1">
              <label className="mb-1 block text-sm font-medium">Team Name</label>
              <Input placeholder="e.g. platform-team" value={team} onChange={(e) => setTeam(e.target.value)} />
            </div>
            <div className="w-40">
              <label className="mb-1 block text-sm font-medium">Rotation</label>
              <Select value={rotationType} onValueChange={setRotationType}>
                <SelectTrigger><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="daily">Daily</SelectItem>
                  <SelectItem value="weekly">Weekly</SelectItem>
                  <SelectItem value="biweekly">Biweekly</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <label className="mb-2 block text-sm font-medium">Members</label>
            <div className="flex flex-col gap-2">
              {members.map((m, idx) => (
                <div key={idx} className="flex items-center gap-2">
                  <Input placeholder="Name" value={m.name} onChange={(e) => updateMember(idx, "name", e.target.value)} className="flex-1" />
                  <Input placeholder="Email" value={m.email} onChange={(e) => updateMember(idx, "email", e.target.value)} className="flex-1" />
                  <Select value={m.role} onValueChange={(v) => updateMember(idx, "role", v)}>
                    <SelectTrigger className="w-28"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="primary">Primary</SelectItem>
                      <SelectItem value="secondary">Secondary</SelectItem>
                    </SelectContent>
                  </Select>
                  {members.length > 1 && (
                    <Button variant="ghost" size="icon" className="h-8 w-8 shrink-0 text-destructive" onClick={() => removeMember(idx)}>
                      <X className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              ))}
              <Button variant="outline" size="sm" onClick={addMember} className="mt-1 w-fit gap-1">
                <Plus className="h-3.5 w-3.5" />
                Add Member
              </Button>
            </div>
          </div>
        </div>
        <DialogFooter>
          <Button variant="outline" onClick={() => setOpen(false)}>Cancel</Button>
          <Button onClick={handleCreate} disabled={submitting || !team.trim()}>Create Schedule</Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

function EscalationHistory({ escalations }: { escalations: EscalationLog[] }) {
  if (escalations.length === 0) {
    return (
      <p className="py-12 text-center text-muted-foreground">No escalations recorded yet.</p>
    )
  }

  return (
    <div className="rounded-xl border border-border bg-card">
      <Table>
        <TableHeader>
          <TableRow className="border-border hover:bg-transparent">
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Team</TableHead>
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Incident</TableHead>
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Escalated To</TableHead>
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">Reason</TableHead>
            <TableHead className="text-xs font-medium uppercase tracking-wider text-muted-foreground">When</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {escalations.map((esc) => (
            <TableRow key={esc.escalation_id} className="border-border hover:bg-secondary/50">
              <TableCell className="text-sm font-medium text-foreground">{esc.team}</TableCell>
              <TableCell className="font-mono text-xs text-muted-foreground">{esc.incident_id.slice(0, 8)}</TableCell>
              <TableCell className="text-sm text-foreground">{esc.escalated_to ? esc.escalated_to.name : "\u2014"}</TableCell>
              <TableCell className="max-w-[200px] truncate text-sm text-muted-foreground">{esc.reason || "\u2014"}</TableCell>
              <TableCell className="text-sm text-muted-foreground">{timeAgo(esc.timestamp)}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  )
}
