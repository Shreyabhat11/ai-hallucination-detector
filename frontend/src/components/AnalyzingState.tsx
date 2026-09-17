import { useEffect, useState } from "react"

// The backend is a single synchronous request/response -- it does not
// stream stage-by-stage progress events. So this rotates through a
// generic, honest label rather than claiming specific stages have
// completed (which would be fabricated). The real, measured per-stage
// breakdown is shown afterward in the Performance panel, from data the
// backend actually returned.
const labels = [
  "Contacting the verification service…",
  "This can take a few seconds, especially in Deep mode…",
  "Still working…",
]

export function AnalyzingState() {
  const [labelIndex, setLabelIndex] = useState(0)

  useEffect(() => {
    const interval = setInterval(() => {
      setLabelIndex((i) => Math.min(i + 1, labels.length - 1))
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  return (
    <div className="mt-6 flex items-center gap-3 rounded-[6px] border border-border bg-surface p-5" role="status">
      <span className="h-4 w-4 shrink-0 animate-spin rounded-full border-2 border-border-strong border-t-ink" />
      <span className="text-sm text-ink-muted">{labels[labelIndex]}</span>
    </div>
  )
}
