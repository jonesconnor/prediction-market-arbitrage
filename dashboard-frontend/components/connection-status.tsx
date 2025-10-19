"use client"

import type { ConnectionStatus } from "@/lib/types"

type ConnectionStatusProps = {
  status: ConnectionStatus
}

export function ConnectionStatusIndicator({ status }: ConnectionStatusProps) {
  return (
    <div className="flex items-center gap-2 text-sm">
      <div className="relative flex h-2 w-2">
        {status === "connected" && (
          <>
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-success opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-success" />
          </>
        )}
        {status === "reconnecting" && (
          <>
            <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-warning opacity-75" />
            <span className="relative inline-flex h-2 w-2 rounded-full bg-warning" />
          </>
        )}
        {status === "disconnected" && <span className="relative inline-flex h-2 w-2 rounded-full bg-destructive" />}
      </div>
      <span className="text-muted-foreground">
        {status === "connected" && "Live"}
        {status === "reconnecting" && "Reconnecting..."}
        {status === "disconnected" && "Disconnected"}
      </span>
    </div>
  )
}
