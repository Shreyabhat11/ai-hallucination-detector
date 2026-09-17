import { useEffect, useState } from "react"
import { getHealth } from "../api/detector"
import { StatusMarker } from "./StatusMarker"

type Status = "checking" | "online" | "offline"

const POLL_INTERVAL_MS = 30_000

export function BackendStatus() {
  const [status, setStatus] = useState<Status>("checking")

  useEffect(() => {
    let cancelled = false

    async function check() {
      try {
        await getHealth()
        if (!cancelled) setStatus("online")
      } catch {
        if (!cancelled) setStatus("offline")
      }
    }

    check()
    const interval = setInterval(check, POLL_INTERVAL_MS)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [])

  const label = status === "checking" ? "Checking API…" : status === "online" ? "API connected" : "API unavailable"
  const tone = status === "online" ? "verify" : status === "offline" ? "risk" : "neutral"

  return (
    <div className="flex items-center gap-2 text-sm text-ink-muted">
      <StatusMarker tone={tone} />
      <span>{label}</span>
    </div>
  )
}
