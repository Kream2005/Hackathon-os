import { ReactNode, useEffect, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { useAuth } from '../App'
import { fetchServicesHealth } from '../api-client'
import type { ServiceHealth } from '../types'
import {
  Activity, LayoutDashboard, AlertTriangle, Zap, Calendar,
  BarChart3, Bell, User, LogOut,
} from 'lucide-react'

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/incidents', label: 'Incidents', icon: AlertTriangle },
  { href: '/alerts', label: 'Alerts', icon: Zap },
  { href: '/oncall', label: 'On-Call', icon: Calendar },
  { href: '/metrics', label: 'SRE Metrics', icon: BarChart3 },
  { href: '/notifications', label: 'Notifications', icon: Bell },
]

const SERVICE_MAP: Record<string, { name: string; port: number }> = {
  'alert-ingestion': { name: 'Alert Ingestion', port: 8001 },
  'incident-management': { name: 'Incident Mgmt', port: 8002 },
  'oncall-service': { name: 'On-Call Service', port: 8003 },
  'notification-service': { name: 'Notification', port: 8004 },
}

export default function Layout({ children }: { children: ReactNode }) {
  const { pathname } = useLocation()
  const { username, logout } = useAuth()
  const [health, setHealth] = useState<ServiceHealth | null>(null)

  useEffect(() => {
    let mounted = true
    const poll = async () => {
      try {
        const h = await fetchServicesHealth()
        if (mounted) setHealth(h)
      } catch { /* ignore */ }
    }
    poll()
    const id = setInterval(poll, 30000)
    return () => { mounted = false; clearInterval(id) }
  }, [])

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside className="flex h-screen w-64 flex-col border-r border-border bg-card sticky top-0">
        {/* Logo */}
        <div className="flex items-center gap-3 border-b border-border px-6 py-5">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
            <Activity className="h-4 w-4 text-primary-foreground" />
          </div>
          <div>
            <h1 className="text-sm font-semibold text-foreground">Incident Platform</h1>
            <p className="text-xs text-muted-foreground">On-Call &amp; SRE</p>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 px-3 py-4">
          <ul className="flex flex-col gap-1">
            {navItems.map(item => {
              const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href))
              return (
                <li key={item.href}>
                  <Link
                    to={item.href}
                    className={`flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors ${
                      isActive ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-secondary hover:text-foreground'
                    }`}
                  >
                    <item.icon className="h-4 w-4" />
                    {item.label}
                  </Link>
                </li>
              )
            })}
          </ul>
        </nav>

        {/* User */}
        <div className="border-t border-border px-4 py-3">
          <div className="flex items-center gap-3 rounded-lg px-3 py-2 text-sm">
            <User className="h-4 w-4 text-muted-foreground" />
            <span className="flex-1 truncate font-medium text-foreground">{username ?? 'user'}</span>
            <button onClick={logout} title="Sign out" className="rounded-md p-1 text-muted-foreground hover:bg-destructive/10 hover:text-destructive">
              <LogOut className="h-4 w-4" />
            </button>
          </div>
        </div>

        {/* Service Health */}
        <div className="border-t border-border px-4 py-4">
          <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">Services</p>
          <div className="flex flex-col gap-1.5">
            {Object.entries(SERVICE_MAP).map(([key, svc]) => {
              const status = health?.[key]?.status
              return (
                <div key={key} className="flex items-center gap-2 text-xs">
                  <span className={`h-1.5 w-1.5 rounded-full ${
                    status === 'up' ? 'bg-green-500' : status === 'down' ? 'bg-destructive' : 'bg-muted-foreground/40'
                  }`} />
                  <span className="text-muted-foreground">{svc.name}</span>
                  <span className="ml-auto font-mono text-muted-foreground">:{svc.port}</span>
                </div>
              )
            })}
          </div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  )
}
