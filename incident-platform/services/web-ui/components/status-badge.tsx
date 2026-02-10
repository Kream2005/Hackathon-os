import { cn } from "@/lib/utils"
import type { IncidentStatus } from "@/lib/types"

const statusConfig: Record<IncidentStatus, { bg: string; text: string; label: string }> = {
  open: { bg: "bg-red-500/10", text: "text-red-600 dark:text-red-400", label: "Open" },
  acknowledged: { bg: "bg-amber-500/10", text: "text-amber-600 dark:text-amber-400", label: "Acknowledged" },
  in_progress: { bg: "bg-blue-500/10", text: "text-blue-600 dark:text-blue-400", label: "In Progress" },
  resolved: { bg: "bg-indigo-500/10", text: "text-indigo-600 dark:text-indigo-400", label: "Resolved" },
}

export function StatusBadge({ status }: { status: IncidentStatus }) {
  const config = statusConfig[status]
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-md px-2 py-1 text-xs font-medium",
        config.bg,
        config.text
      )}
    >
      {config.label}
    </span>
  )
}
