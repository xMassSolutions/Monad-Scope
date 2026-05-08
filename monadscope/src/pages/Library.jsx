import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { motion } from 'motion/react'
import { ChevronRight, ShieldAlert, Library as LibraryIcon } from 'lucide-react'
import { api } from '../lib/api'
import { actionColor, formatTime, shortAddr, tierColor } from '../lib/format'

function ContractRow({ c }) {
  return (
    <Link
      to={`/app/contract/${c.address}`}
      className="group flex items-center justify-between gap-4 rounded-xl px-4 py-3 border border-white/8 hover:border-white/20 transition-colors"
      style={{ background: 'rgba(255,255,255,0.02)' }}
    >
      <div className="flex items-center gap-4 min-w-0 flex-1">
        <div className="w-9 h-9 rounded-lg bg-white/5 flex items-center justify-center text-[10px] font-mono text-white/50 shrink-0 border border-white/10">
          {c.symbol?.slice(0, 3) || '0x'}
        </div>
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <span className="text-white text-sm font-medium truncate">
              {c.contract_name || 'Unnamed contract'}
            </span>
            {c.symbol && <span className="text-white/40 text-xs">({c.symbol})</span>}
          </div>
          <div className="text-white/40 text-[11px] font-mono mt-0.5">
            {shortAddr(c.address)} · {c.kind || 'unknown'}
            {c.first_seen_at && <> · seen {formatTime(c.first_seen_at)}</>}
          </div>
        </div>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        {c.risk_score != null && (
          <span className="text-white/70 text-xs font-mono">{c.risk_score.toFixed(0)}</span>
        )}
        {c.risk_tier && (
          <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${tierColor(c.risk_tier)}`}>
            {c.risk_tier}
          </span>
        )}
        {c.action && (
          <span className={`hidden md:inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${actionColor(c.action)}`}>
            {c.action}
          </span>
        )}
        <ChevronRight size={14} className="text-white/30 group-hover:text-white/70 transition-colors" />
      </div>
    </Link>
  )
}

export default function Library({ kind }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)

  useEffect(() => {
    setItems(null)
    setError(null)
    const fn = kind === 'high-risk' ? api.libraryHighRisk : api.libraryRecent
    fn(50, 0)
      .then(setItems)
      .catch((e) => setError(e.message))
  }, [kind])

  const isHighRisk = kind === 'high-risk'

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="max-w-5xl mx-auto space-y-6"
    >
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center"
          style={{
            background: isHighRisk
              ? 'linear-gradient(135deg, #FF3D77, #FF9D3C)'
              : 'linear-gradient(135deg, #60D5FA, #A78BFA)',
          }}
        >
          {isHighRisk ? (
            <ShieldAlert size={18} className="text-white" />
          ) : (
            <LibraryIcon size={18} className="text-black/70" />
          )}
        </div>
        <div>
          <h1 className="text-white text-2xl md:text-3xl font-bold tracking-tight">
            {isHighRisk ? 'High-risk contracts' : 'Recent contracts'}
          </h1>
          <p className="text-white/40 text-sm">
            {isHighRisk
              ? 'Highest weighted-finding scores from the public case library.'
              : 'Latest contracts ingested from Monad mainnet.'}
          </p>
        </div>
      </div>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-sm p-4">
          Failed to load: {error}. Is the backend running on port 8000?
        </div>
      )}

      {!items && !error && (
        <div className="space-y-2">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="h-14 rounded-xl bg-white/3 border border-white/8 animate-pulse" />
          ))}
        </div>
      )}

      {items && items.length === 0 && (
        <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center">
          <p className="text-white/40 text-sm">
            No contracts in the library yet — start the listener to ingest from Monad mainnet.
          </p>
        </div>
      )}

      {items && items.length > 0 && (
        <div className="flex flex-col gap-2">
          {items.map((c) => (
            <ContractRow key={c.id} c={c} />
          ))}
        </div>
      )}
    </motion.div>
  )
}
