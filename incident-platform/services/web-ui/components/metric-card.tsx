import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

interface MetricCardProps {
  title: string
  value: string | number
  subtitle?: string
  icon: LucideIcon
  trend?: "up" | "down" | "neutral"
  trendValue?: string
  variant?: "default" | "critical" | "warning" | "success"
}

const variantStyles = {
  default: "border-border",
  critical: "border-red-500/20",
  warning: "border-amber-500/20",
  success: "border-indigo-500/20",
}

const iconVariantStyles = {
  default: "bg-secondary text-muted-foreground",
  critical: "bg-red-500/10 text-red-500 dark:text-red-400",
  warning: "bg-amber-500/10 text-amber-500 dark:text-amber-400",
  success: "bg-indigo-500/10 text-indigo-500 dark:text-indigo-400",
}

export function MetricCard({
  title,
  value,
  subtitle,
  icon: Icon,
  trend,
  trendValue,
  variant = "default",
}: MetricCardProps) {
  return (
    <div
      className={cn(
        "rounded-xl border bg-card p-5",
        variantStyles[variant]
      )}
    >
      <div className="flex items-start justify-between">
        <div className="flex flex-col gap-1">
          <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
            {title}
          </p>
          <p className="text-2xl font-semibold text-foreground">{value}</p>
          {subtitle && (
            <p className="text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>
        <div className={cn("rounded-lg p-2.5", iconVariantStyles[variant])}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      {trend && trendValue && (
        <div className="mt-3 flex items-center gap-1 text-xs">
          <span
            className={cn(
              trend === "down" ? "text-indigo-500 dark:text-indigo-400" : trend === "up" ? "text-red-500 dark:text-red-400" : "text-muted-foreground"
            )}
          >
            {trend === "up" ? "+" : trend === "down" ? "-" : ""}
            {trendValue}
          </span>
          <span className="text-muted-foreground">vs last period</span>
        </div>
      )}
    </div>
  )
}
