import type { ReactNode } from 'react'

export type KpiCardTone = 'neutral' | 'positive' | 'warning' | 'critical'

export interface KpiCardProps {
  label: string
  value: string
  hint?: string
  tone?: KpiCardTone
}

const TONE_CLASS: Record<KpiCardTone, string> = {
  neutral: 'text-gray-900',
  positive: 'text-green-700',
  warning: 'text-amber-700',
  critical: 'text-red-700',
}

/**
 * A single headline number for the app shell (architecture section 4.2).
 *
 * The value is a string on purpose. Amounts arrive from the API as
 * fixed 2-decimal strings (R-05), and passing them through unchanged
 * keeps the exact value the backend sent.
 */
export function KpiCard({ label, value, hint, tone = 'neutral' }: KpiCardProps) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
      <div className="text-sm text-gray-500">{label}</div>
      <div className={`mt-1 text-2xl font-semibold tabular-nums ${TONE_CLASS[tone]}`}>{value}</div>
      {hint ? <div className="mt-1 text-xs text-gray-400">{hint}</div> : null}
    </div>
  )
}

export interface KpiCardContentProps {
  children: ReactNode
}

/** Lays a row of KPI cards out. */
export function KpiRow({ children }: KpiCardContentProps) {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">{children}</div>
  )
}
