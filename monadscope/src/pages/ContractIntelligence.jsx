import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { motion } from 'motion/react'
import { Search, RefreshCw, ExternalLink, AlertTriangle, ShieldCheck, Globe, Sparkles, Skull } from 'lucide-react'
import { api } from '../lib/api'
import { actionColor, formatTime, formatUsd, shortAddr, tierColor } from '../lib/format'

function Badge({ children, className = '' }) {
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold border ${className}`}>
      {children}
    </span>
  )
}

function Stat({ label, value, badge, badgeClass }) {
  return (
    <div className="rounded-xl p-4 border border-white/8" style={{ background: 'rgba(255,255,255,0.03)' }}>
      <div className="text-white/40 text-[11px] uppercase tracking-wide mb-1.5">{label}</div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-white text-base font-semibold">{value ?? '—'}</span>
        {badge && <Badge className={badgeClass}>{badge}</Badge>}
      </div>
    </div>
  )
}

function FindingItem({ f, calib }) {
  return (
    <div className="rounded-xl p-4 border border-white/8 hover:border-white/20 transition-colors" style={{ background: 'rgba(255,255,255,0.03)' }}>
      <div className="flex items-start justify-between gap-3 mb-2">
        <h4 className="text-white text-sm font-medium leading-snug">{f.title || f.code}</h4>
        <Badge className={tierColor(f.severity || f.tier)}>{f.severity || f.tier || 'info'}</Badge>
      </div>
      {f.description && (
        <p className="text-white/50 text-xs leading-relaxed mb-2">{f.description}</p>
      )}
      <div className="flex items-center gap-3 text-[10px] text-white/30">
        {f.code && <span className="font-mono">{f.code}</span>}
        {typeof f.weight === 'number' && <span>weight {f.weight.toFixed(2)}</span>}
        {typeof f.confidence === 'number' && <span>confidence {(f.confidence * 100).toFixed(0)}%</span>}
      </div>
      {calib && calib.incident_count > 0 && (
        <div className="mt-2 pt-2 border-t border-white/8 flex items-center gap-2 text-[10px]">
          <Skull size={10} className="text-rose-400" />
          <span className="text-rose-400/90">
            {calib.incident_count} historical exploit{calib.incident_count === 1 ? '' : 's'} ·{' '}
            {formatUsd(calib.total_loss_usd)} lost
          </span>
          <span className="text-white/40">→ +{(calib.bonus ?? 0).toFixed(2)} pts</span>
        </div>
      )}
    </div>
  )
}

function ExploitCalibration({ calibration }) {
  if (!calibration) return null
  const perCode = calibration.per_code || {}
  const codes = Object.values(perCode).sort((a, b) => (b.bonus ?? 0) - (a.bonus ?? 0))
  if (codes.length === 0) return null
  const totalLoss = codes.reduce((acc, c) => acc + (c.total_loss_usd || 0), 0)
  const totalIncidents = codes.reduce((acc, c) => acc + (c.incident_count || 0), 0)
  return (
    <div className="rounded-2xl border border-rose-500/20 p-5" style={{ background: 'rgba(255,61,119,0.04)' }}>
      <div className="flex items-center justify-between gap-3 flex-wrap mb-3">
        <div className="flex items-center gap-2">
          <Skull size={14} className="text-rose-400" />
          <h3 className="text-white text-sm font-semibold">Historical-exploit calibration</h3>
        </div>
        <div className="flex items-center gap-3 text-[11px] text-white/50">
          <span>+{(calibration.total_bonus ?? 0).toFixed(2)} risk pts</span>
          <span>·</span>
          <span>{totalIncidents} incidents</span>
          <span>·</span>
          <span className="text-rose-400">{formatUsd(totalLoss)} losses</span>
        </div>
      </div>
      <p className="text-white/50 text-xs leading-relaxed mb-3">
        Findings on this contract overlap with patterns from past exploits. The calibrated bonus is
        added to the risk score; click a code to see the matching incidents.
      </p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {codes.map((c) => (
          <Link
            key={c.code}
            to={`/app/exploits?code=${encodeURIComponent(c.code)}`}
            className="flex items-center justify-between gap-3 rounded-lg border border-white/8 hover:border-rose-500/40 transition-colors p-3"
            style={{ background: 'rgba(255,255,255,0.02)' }}
          >
            <div className="min-w-0">
              <div className="text-white text-xs font-mono truncate">{c.code}</div>
              <div className="text-white/40 text-[10px] mt-0.5">
                {c.incident_count} incident{c.incident_count === 1 ? '' : 's'} ·{' '}
                <span className="text-rose-400">{formatUsd(c.total_loss_usd)}</span>
              </div>
            </div>
            <div className="text-rose-400 text-xs font-semibold tabular-nums shrink-0">
              +{(c.bonus ?? 0).toFixed(2)}
            </div>
          </Link>
        ))}
      </div>
    </div>
  )
}

function ContractView({ data, refresh, refreshing }) {
  const c = data.contract
  const calibration = data.latest_analysis?.summary_json?.exploit_calibration
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      {/* Header */}
      <div className="rounded-2xl border border-white/10 p-6" style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02))' }}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-2xl flex items-center justify-center text-xl shrink-0" style={{ background: 'linear-gradient(135deg, #60D5FA, #A78BFA)' }}>
              <Globe size={20} className="text-black/70" />
            </div>
            <div>
              <h2 className="text-white text-xl font-semibold tracking-tight">
                {c.contract_name || 'Unnamed contract'}
                {c.symbol && <span className="text-white/40 ml-2 text-base">({c.symbol})</span>}
              </h2>
              <div className="text-white/50 text-xs font-mono mt-1">{c.address}</div>
              <div className="flex flex-wrap items-center gap-2 mt-3">
                <Badge className="text-white/60 bg-white/5 border-white/15">{c.kind || 'unknown'}</Badge>
                {c.verified ? (
                  <Badge className="text-emerald-400 bg-emerald-500/15 border-emerald-500/30">
                    <ShieldCheck size={10} className="mr-1" /> verified
                  </Badge>
                ) : (
                  <Badge className="text-amber-400 bg-amber-500/15 border-amber-500/30">
                    <AlertTriangle size={10} className="mr-1" /> unverified
                  </Badge>
                )}
                {c.is_proxy && <Badge className="text-violet-400 bg-violet-500/15 border-violet-500/30">proxy</Badge>}
                {c.prime_available && (
                  <Badge className="text-cyan-300 bg-cyan-500/15 border-cyan-500/30">
                    <Sparkles size={10} className="mr-1" /> prime
                  </Badge>
                )}
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={refresh}
              disabled={refreshing}
              className="flex items-center gap-1.5 px-3 py-2 text-xs text-white/80 hover:text-white border border-white/15 hover:border-white/30 rounded-lg transition disabled:opacity-50"
            >
              <RefreshCw size={12} className={refreshing ? 'animate-spin' : ''} /> Re-analyze
            </button>
            <a
              href={`https://monadexplorer.com/address/${c.address}`}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-1.5 px-3 py-2 text-xs text-white/80 hover:text-white border border-white/15 hover:border-white/30 rounded-lg transition"
            >
              Explorer <ExternalLink size={12} />
            </a>
          </div>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat
          label="Risk score"
          value={c.risk_score != null ? c.risk_score.toFixed(1) : '—'}
          badge={c.risk_tier}
          badgeClass={tierColor(c.risk_tier)}
        />
        <Stat
          label="Confidence"
          value={c.confidence_score != null ? `${(c.confidence_score * 100).toFixed(0)}%` : '—'}
        />
        <Stat
          label="Findings"
          value={`${data.findings.length} flag${data.findings.length === 1 ? '' : 's'}`}
        />
        <Stat
          label="Action"
          value={c.action || '—'}
          badge={c.action}
          badgeClass={actionColor(c.action)}
        />
      </div>

      {/* Prime status block */}
      {data.prime && (
        <div className="rounded-2xl border border-white/8 p-5" style={{ background: 'rgba(255,255,255,0.02)' }}>
          <div className="flex items-center gap-2 mb-3">
            <Sparkles size={14} className="text-cyan-300" />
            <h3 className="text-white text-sm font-semibold">Prime status</h3>
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 text-xs">
            {Object.entries(data.prime).map(([k, v]) => (
              <div key={k} className="flex flex-col gap-1">
                <span className="text-white/30 uppercase tracking-wide text-[10px]">{k.replace(/_/g, ' ')}</span>
                <span className="text-white/80 break-words">{typeof v === 'object' ? JSON.stringify(v) : String(v ?? '—')}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Historical-exploit calibration */}
      <ExploitCalibration calibration={calibration} />

      {/* Findings */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-white text-sm font-semibold">Findings</h3>
          <span className="text-white/40 text-xs">{data.findings.length} total</span>
        </div>
        {data.findings.length === 0 ? (
          <div className="text-white/40 text-sm border border-white/8 rounded-xl p-6 text-center">
            No findings yet — pipeline may still be enriching this contract.
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {data.findings.map((f, i) => {
              const calib = calibration?.per_code?.[f.code?.toUpperCase?.()]
              return <FindingItem key={f.id || i} f={f} calib={calib} />
            })}
          </div>
        )}
      </div>

      {/* Meta */}
      <div className="rounded-xl border border-white/8 p-4 text-[11px] text-white/40 grid grid-cols-2 md:grid-cols-4 gap-3">
        <div>First seen<br /><span className="text-white/70">{formatTime(c.first_seen_at)}</span></div>
        <div>Last refreshed<br /><span className="text-white/70">{formatTime(c.last_refreshed_at)}</span></div>
        <div>Next refresh<br /><span className="text-white/70">{formatTime(c.next_refresh_at)}</span></div>
        <div>Creator<br /><span className="text-white/70 font-mono">{shortAddr(c.creator_address)}</span></div>
      </div>
    </motion.div>
  )
}

export default function ContractIntelligence() {
  const { address: routeAddr } = useParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState(routeAddr || '')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)

  async function load(addr) {
    setLoading(true)
    setError(null)
    try {
      const result = await api.getContract(addr)
      setData(result)
    } catch (e) {
      setError(e.status === 404 ? 'Contract not found in case library yet.' : e.message)
      setData(null)
    } finally {
      setLoading(false)
    }
  }

  async function onSubmit(e) {
    e.preventDefault()
    const addr = query.trim().toLowerCase()
    if (!/^0x[a-f0-9]{40}$/.test(addr)) {
      setError('Enter a valid 0x address (40 hex chars).')
      return
    }
    navigate(`/app/contract/${addr}`)
    load(addr)
  }

  async function refresh() {
    if (!data) return
    setRefreshing(true)
    try {
      const next = await api.analyzeNow(data.contract.address)
      setData(next)
    } catch (e) {
      setError(e.message)
    } finally {
      setRefreshing(false)
    }
  }

  // Auto-load if address in URL
  useState(() => {
    if (routeAddr) load(routeAddr)
  }, [])

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-white text-2xl md:text-3xl font-bold tracking-tight mb-1">
          Contract intelligence
        </h1>
        <p className="text-white/40 text-sm">
          Look up any Monad contract — verification, classification, findings, risk score, prime status.
        </p>
      </div>

      <form onSubmit={onSubmit} className="flex gap-2">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="0x… contract address"
            className="w-full bg-white/5 border border-white/10 focus:border-white/30 rounded-xl pl-9 pr-3 py-3 text-sm text-white font-mono placeholder:text-white/30 outline-none transition"
            spellCheck={false}
          />
        </div>
        <button
          type="submit"
          disabled={loading}
          className="px-5 py-3 bg-white text-black rounded-xl font-semibold text-sm hover:bg-white/90 disabled:opacity-50 transition"
        >
          {loading ? 'Loading…' : 'Analyze'}
        </button>
      </form>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-sm p-4">
          {error}
        </div>
      )}

      {!data && !loading && !error && (
        <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center">
          <p className="text-white/40 text-sm mb-4">Try a recent contract from the public case library:</p>
          <Link
            to="/app/library/recent"
            className="inline-flex items-center gap-2 px-4 py-2 text-xs text-white/80 hover:text-white border border-white/15 hover:border-white/30 rounded-lg transition"
          >
            <Search size={12} /> Browse recent
          </Link>
        </div>
      )}

      {data && <ContractView data={data} refresh={refresh} refreshing={refreshing} />}
    </div>
  )
}
