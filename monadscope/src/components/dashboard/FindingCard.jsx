import RiskBadge from './RiskBadge'

const BORDER_COLORS = {
  red: 'border-l-red-500',
  orange: 'border-l-orange-500',
  amber: 'border-l-amber-400',
  teal: 'border-l-teal-400',
  green: 'border-l-emerald-400',
  blue: 'border-l-blue-400',
  gray: 'border-l-white/30',
}

function tierToColor(tier) {
  const s = String(tier || '').toLowerCase()
  if (s === 'critical') return 'red'
  if (s === 'high') return 'orange'
  if (s === 'medium') return 'amber'
  if (s === 'low' || s === 'success') return 'green'
  if (s === 'info') return 'teal'
  return 'gray'
}

export default function FindingCard({ title, summary, risk, color, code }) {
  const c = color || tierToColor(risk)
  const border = BORDER_COLORS[c] || BORDER_COLORS.gray
  return (
    <div
      className={`flex-shrink-0 w-56 rounded-xl p-3 border border-white/8 border-l-2 ${border}`}
      style={{ background: 'rgba(255,255,255,0.04)' }}
    >
      <p className="text-white/85 text-[11px] font-medium leading-snug mb-2 line-clamp-3">
        {title}
      </p>
      {summary && (
        <p className="text-white/40 text-[10px] leading-snug mb-3 line-clamp-3">{summary}</p>
      )}
      <div className="flex items-center justify-between gap-2">
        <RiskBadge level={risk} />
        {code && <span className="text-[9px] font-mono text-white/30">{code}</span>}
      </div>
    </div>
  )
}
