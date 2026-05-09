import { useEffect, useRef, useState } from 'react'
import { api } from '../../lib/api'

function fmtNumber(n) {
  if (n == null) return '—'
  return Number(n).toLocaleString('en-US')
}

function fmtLag(seconds) {
  if (seconds == null) return '—'
  if (seconds < 1) return '<1s'
  if (seconds < 60) return `${seconds.toFixed(1)}s`
  const m = Math.floor(seconds / 60)
  const s = Math.round(seconds % 60)
  return `${m}m ${s}s`
}

function lagSeverity(lagSeconds) {
  if (lagSeconds == null) return 'red'
  if (lagSeconds < 30) return 'green'
  if (lagSeconds < 120) return 'amber'
  return 'red'
}

const DOT_COLORS = {
  green: { dot: 'bg-emerald-400', text: 'text-emerald-400/80', label: 'Live' },
  amber: { dot: 'bg-amber-400', text: 'text-amber-400/80', label: 'Lagging' },
  red: { dot: 'bg-red-400', text: 'text-red-400/80', label: 'Offline' },
}

export default function LiveStatusBar() {
  const [status, setStatus] = useState(null)
  const [err, setErr] = useState(false)
  const mounted = useRef(true)

  useEffect(() => {
    mounted.current = true
    let timer
    const tick = async () => {
      try {
        const s = await api.liveStatus()
        if (!mounted.current) return
        setStatus(s)
        setErr(false)
      } catch {
        if (!mounted.current) return
        setErr(true)
      } finally {
        if (mounted.current) timer = setTimeout(tick, 5000)
      }
    }
    tick()
    return () => {
      mounted.current = false
      if (timer) clearTimeout(timer)
    }
  }, [])

  const sev = err ? 'red' : lagSeverity(status?.lag_seconds)
  const palette = DOT_COLORS[sev]

  return (
    <div
      className="border-t border-white/8 px-5 py-3 flex items-center justify-between"
      style={{ background: 'rgba(0,0,0,0.35)' }}
    >
      <div className="flex items-center gap-6">
        <div className="flex flex-col">
          <span className="text-white/30 text-[9px] uppercase tracking-wide">Last block</span>
          <span className="text-white/70 text-xs font-mono font-semibold">
            {fmtNumber(status?.last_processed)}
          </span>
        </div>
        <div className="flex flex-col">
          <span className="text-white/30 text-[9px] uppercase tracking-wide">Queue lag</span>
          <span className="text-white/70 text-xs font-mono font-semibold">
            {fmtLag(status?.lag_seconds)}
            {status?.lag_blocks != null && (
              <span className="text-white/30 ml-1.5 font-normal">
                · {status.lag_blocks} block{status.lag_blocks === 1 ? '' : 's'}
              </span>
            )}
          </span>
        </div>
        <div className="hidden md:flex flex-col">
          <span className="text-white/30 text-[9px] uppercase tracking-wide">Recent txs</span>
          <span className="text-white/70 text-xs font-mono font-semibold">
            {fmtNumber(status?.tx_count_recent)}
          </span>
        </div>
        <div className="hidden md:flex flex-col">
          <span className="text-white/30 text-[9px] uppercase tracking-wide">New contracts</span>
          <span className="text-white/70 text-xs font-mono font-semibold">
            {fmtNumber(status?.contracts_created_recent)}
          </span>
        </div>
      </div>
      <div className="flex items-center gap-1.5">
        <div className={`w-1.5 h-1.5 rounded-full ${palette.dot} ${sev === 'green' ? 'animate-pulse' : ''}`} />
        <span className={`${palette.text} text-[10px] font-medium`}>{palette.label}</span>
      </div>
    </div>
  )
}
