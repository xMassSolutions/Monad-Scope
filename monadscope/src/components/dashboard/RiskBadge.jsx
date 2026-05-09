// Shared between the landing demo and the live /app dashboard so the two
// surfaces never visually drift.

const STYLES = {
  Critical: 'bg-red-500/20 text-red-400 border border-red-500/30',
  High: 'bg-orange-500/20 text-orange-400 border border-orange-500/30',
  Medium: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
  Low: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  Info: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
  Success: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  Warn: 'bg-amber-500/20 text-amber-400 border border-amber-500/30',
}

function normalize(level) {
  if (!level) return 'Info'
  const s = String(level).toLowerCase()
  if (s === 'critical') return 'Critical'
  if (s === 'high' || s === 'high_risk' || s === 'high-risk') return 'High'
  if (s === 'medium' || s === 'med' || s === 'monitor') return 'Medium'
  if (s === 'low' || s === 'allow') return 'Low'
  if (s === 'success' || s === 'ok' || s === 'pass' || s === 'verified') return 'Success'
  if (s === 'warn' || s === 'warning') return 'Warn'
  if (s === 'info' || s === 'note') return 'Info'
  // Fallback: Title-case the input.
  return s.charAt(0).toUpperCase() + s.slice(1)
}

export default function RiskBadge({ level, children, className = '' }) {
  const key = normalize(level)
  const style = STYLES[key] || STYLES.Info
  return (
    <span
      className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${style} ${className}`}
    >
      {children ?? key}
    </span>
  )
}
