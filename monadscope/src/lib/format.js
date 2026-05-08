export function shortAddr(addr) {
  if (!addr) return '—'
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`
}

export function tierColor(tier) {
  switch ((tier || '').toLowerCase()) {
    case 'critical':
      return 'text-red-400 bg-red-500/15 border-red-500/30'
    case 'high':
      return 'text-orange-400 bg-orange-500/15 border-orange-500/30'
    case 'medium':
      return 'text-amber-400 bg-amber-500/15 border-amber-500/30'
    case 'low':
      return 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30'
    case 'info':
      return 'text-sky-400 bg-sky-500/15 border-sky-500/30'
    default:
      return 'text-white/50 bg-white/5 border-white/15'
  }
}

export function actionColor(action) {
  switch ((action || '').toLowerCase()) {
    case 'escalate':
      return 'text-red-400 bg-red-500/15 border-red-500/30'
    case 'monitor':
      return 'text-amber-400 bg-amber-500/15 border-amber-500/30'
    case 'allow':
      return 'text-emerald-400 bg-emerald-500/15 border-emerald-500/30'
    default:
      return 'text-white/50 bg-white/5 border-white/15'
  }
}

export function formatTime(iso) {
  if (!iso) return '—'
  try {
    return new Date(iso).toLocaleString()
  } catch {
    return iso
  }
}
