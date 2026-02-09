import { cn } from "@/lib/utils"
import type { Severity } from "@/lib/types"

const severityConfig: Record<Severity, { bg: string; text: string; dot: string }> = {
  critical: { bg: "bg-red-500/10", text: "text-red-600 dark:text-red-400", dot: "bg-red-500 dark:bg-red-400" },
  high: { bg: "bg-orange-500/10", text: "text-orange-600 dark:text-orange-400", dot: "bg-orange-500 dark:bg-orange-400" },
  medium: { bg: "bg-amber-500/10", text: "text-amber-600 dark:text-amber-400", dot: "bg-amber-500 dark:bg-amber-400" },
  low: { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", dot: "bg-blue-500 dark:bg-blue-400" },
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const config = severityConfig[severity]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-2.5 py-0.5 text-xs font-medium",
        config.bg,
        config.text
      )}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      {severity.charAt(0).toUpperCase() + severity.slice(1)}
    </span>
  )
}
