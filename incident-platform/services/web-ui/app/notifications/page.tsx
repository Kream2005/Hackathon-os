"use client"

import useSWR from "swr"
import { notificationsFetcher } from "@/lib/api-client"
import type { NotificationLog } from "@/lib/types"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Bell, CheckCircle, XCircle, Clock, Loader2 } from "lucide-react"

function formatDate(dateStr: string) {
  return new Date(dateStr).toLocaleString("en-US", {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  })
}

export default function NotificationsPage() {
  const { data: notifications, error, isLoading } = useSWR<NotificationLog[]>(
    "/api/v1/notifications",
    notificationsFetcher,
    { refreshInterval: 10000 },
  )

  const sent = notifications?.filter((n) => n.status === "sent").length ?? 0
  const failed = notifications?.filter((n) => n.status === "failed").length ?? 0

  return (
    <div className="flex flex-col gap-6 p-6">
      <div>
        <h1 className="text-2xl font-semibold text-foreground">Notifications</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Notification delivery log for incident alerts and escalations
        </p>
      </div>

      {error && (
        <div className="rounded-lg border border-destructive/50 bg-destructive/10 p-4 text-sm text-destructive">
          Failed to load notifications. Make sure the API Gateway and Notification Service are running.
        </div>
      )}

      {isLoading && (
        <div className="flex items-center justify-center py-12">
          <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
          <span className="ml-2 text-sm text-muted-foreground">Loading notifications...</span>
        </div>
      )}

      {!isLoading && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <Card className="border-border bg-card">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-primary/10">
                  <Bell className="h-5 w-5 text-primary" />
                </div>
                <div>
                  <p className="text-2xl font-semibold text-foreground">{notifications?.length ?? 0}</p>
                  <p className="text-xs text-muted-foreground">Total Sent</p>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border bg-card">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-indigo-500/10">
                  <CheckCircle className="h-5 w-5 text-indigo-500 dark:text-indigo-400" />
                </div>
                <div>
                  <p className="text-2xl font-semibold text-foreground">{sent}</p>
                  <p className="text-xs text-muted-foreground">Delivered</p>
                </div>
              </CardContent>
            </Card>
            <Card className="border-border bg-card">
              <CardContent className="flex items-center gap-4 py-4">
                <div className="flex h-10 w-10 items-center justify-center rounded-lg bg-red-500/10">
                  <XCircle className="h-5 w-5 text-red-500 dark:text-red-400" />
                </div>
                <div>
                  <p className="text-2xl font-semibold text-foreground">{failed}</p>
                  <p className="text-xs text-muted-foreground">Failed</p>
                </div>
              </CardContent>
            </Card>
          </div>

          <Card className="border-border bg-card">
            <CardHeader>
              <CardTitle className="text-sm font-medium text-foreground">Delivery Log</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="flex flex-col gap-3">
                {notifications && notifications.length > 0 ? (
                  notifications.map((notif) => (
                    <div
                      key={notif.id}
                      className="flex items-center gap-4 rounded-lg border border-border bg-secondary/30 p-4"
                    >
                      <div className="flex h-8 w-8 items-center justify-center rounded-full bg-secondary">
                        {notif.status === "sent" ? (
                          <CheckCircle className="h-4 w-4 text-indigo-500 dark:text-indigo-400" />
                        ) : (
                          <XCircle className="h-4 w-4 text-red-500 dark:text-red-400" />
                        )}
                      </div>
                      <div className="flex-1">
                        <p className="text-sm text-foreground">{notif.message}</p>
                        <div className="mt-1 flex items-center gap-3 text-xs text-muted-foreground">
                          <span>To: {notif.recipient}</span>
                          <span>Incident: {notif.incident_id}</span>
                        </div>
                      </div>
                      <div className="flex flex-col items-end gap-1">
                        <Badge
                          variant="outline"
                          className={
                            notif.channel === "webhook" ? "text-blue-400" : "text-muted-foreground"
                          }
                        >
                          {notif.channel}
                        </Badge>
                        <span className="flex items-center gap-1 text-xs text-muted-foreground">
                          <Clock className="h-3 w-3" />
                          {formatDate(notif.created_at)}
                        </span>
                      </div>
                    </div>
                  ))
                ) : (
                  <p className="py-8 text-center text-muted-foreground">
                    No notifications have been sent yet.
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        </>
      )}
    </div>
  )
}
