"use client"

import { useEffect, useState } from "react"
import Link from "next/link"
import { usePathname } from "next/navigation"
import { useTheme } from "next-themes"
import { cn } from "@/lib/utils"
import { getServicesHealth } from "@/lib/api-client"
import type { ServiceHealth } from "@/lib/types"
import {
  AlertTriangle,
  LayoutDashboard,
  Calendar,
  BarChart3,
  Bell,
  Activity,
  Sun,
  Moon,
  Zap,
} from "lucide-react"

const navItems = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/incidents", label: "Incidents", icon: AlertTriangle },
  { href: "/alerts", label: "Alerts", icon: Zap },
  { href: "/oncall", label: "On-Call", icon: Calendar },
  { href: "/metrics-page", label: "SRE Metrics", icon: BarChart3 },
  { href: "/notifications", label: "Notifications", icon: Bell },
]

const SERVICE_MAP: Record<string, { name: string; port: number }> = {
  "alert-ingestion": { name: "Alert Ingestion", port: 8001 },
  "incident-management": { name: "Incident Mgmt", port: 8002 },
  "oncall-service": { name: "On-Call Service", port: 8003 },
  "notification-service": { name: "Notification", port: 8004 },
}

export function AppSidebar() {
  const pathname = usePathname()
  const { theme, setTheme } = useTheme()
  const [health, setHealth] = useState<ServiceHealth | null>(null)

  useEffect(() => {
    let mounted = true
    async function poll() {
      try {
        const h = await getServicesHealth()
        if (mounted) setHealth(h)
      } catch {
        // ignore – show unknown state
      }
    }
    poll()
    const id = setInterval(poll, 30000)
    return () => { mounted = false; clearInterval(id) }
  }, [])

  return (
    <aside className="flex h-screen w-64 flex-col border-r border-border bg-card">
      {/* Logo */}
      <div className="flex items-center gap-3 border-b border-border px-6 py-5">
        <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary">
          <Activity className="h-4 w-4 text-primary-foreground" />
        </div>
        <div>
          <h1 className="text-sm font-semibold text-foreground">Incident Platform</h1>
          <p className="text-xs text-muted-foreground">On-Call & SRE</p>
        </div>
      </div>

      {/* Navigation */}
      <nav className="flex-1 px-3 py-4">
        <ul className="flex flex-col gap-1">
          {navItems.map((item) => {
            const isActive =
              pathname === item.href ||
              (item.href !== "/" && pathname.startsWith(item.href))
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium transition-colors",
                    isActive
                      ? "bg-primary/10 text-primary"
                      : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                  )}
                >
                  <item.icon className="h-4 w-4" />
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>

      {/* Theme Toggle */}
      <div className="border-t border-border px-4 py-3">
        <button
          onClick={() => setTheme(theme === "dark" ? "light" : "dark")}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm font-medium text-muted-foreground transition-colors hover:bg-secondary hover:text-foreground"
        >
          <Sun className="h-4 w-4 rotate-0 scale-100 transition-transform dark:-rotate-90 dark:scale-0" />
          <Moon className="absolute h-4 w-4 rotate-90 scale-0 transition-transform dark:rotate-0 dark:scale-100" />
          <span className="ml-4">Toggle theme</span>
        </button>
      </div>

      {/* Service Status */}
      <div className="border-t border-border px-4 py-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
          Services
        </p>
        <div className="flex flex-col gap-1.5">
          {Object.entries(SERVICE_MAP).map(([key, svc]) => {
            const status = health?.[key]?.status
            return (
              <div key={key} className="flex items-center gap-2 text-xs">
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    status === "up"
                      ? "bg-green-500"
                      : status === "down"
                        ? "bg-destructive"
                        : "bg-muted-foreground/40",
                  )}
                />
                <span className="text-muted-foreground">{svc.name}</span>
                <span className="ml-auto font-mono text-muted-foreground">:{svc.port}</span>
              </div>
            )
          })}
        </div>
      </div>
    </aside>
  )
}
