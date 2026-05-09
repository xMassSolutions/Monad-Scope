import { useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { motion } from 'motion/react'
import {
  Search,
  RefreshCw,
  ExternalLink,
  AlertTriangle,
  ShieldCheck,
  Globe,
  Sparkles,
  Skull,
  Flame,
  X as XIcon,
  MessageCircle,
} from 'lucide-react'
import { api } from '../lib/api'
import { formatTime, formatUsd, shortAddr } from '../lib/format'
import RiskBadge from '../components/dashboard/RiskBadge'
import FindingCard from '../components/dashboard/FindingCard'
import ContractSparkline from '../components/dashboard/ContractSparkline'

// ---------- helpers ---------------------------------------------------------

const SEVERITY_RANK = { critical: 4, high: 3, medium: 2, low: 1, info: 0 }

function severityRank(s) {
  return SEVERITY_RANK[(s || '').toLowerCase()] ?? 0
}

function actionToBadge(action) {
  const a = (action || '').toLowerCase()
  if (a === 'escalate') return 'Critical'
  if (a === 'monitor') return 'Warn'
  if (a === 'allow') return 'Success'
  return 'Info'
}

function tierToBadge(tier) {
  const t = (tier || '').toLowerCase()
  if (t === 'critical') return 'Critical'
  if (t === 'high' || t === 'high_risk') return 'High'
  if (t === 'medium') return 'Medium'
  if (t === 'low') return 'Low'
  return 'Info'
}

function primeStateBadge(prime) {
  if (!prime) return { value: '—', badge: 'Info' }
  const visible = prime.visible ?? prime.is_visible ?? prime.available
  if (visible === true) return { value: 'Visible', badge: 'Success' }
  if (visible === false) return { value: 'Hidden', badge: 'Warn' }
  return { value: prime.status || 'Unknown', badge: 'Info' }
}

function relatedCount(data) {
  const cohort = data?.contract?.related_count
  if (typeof cohort === 'number') return cohort
  const dyn = data?.dynamic_features || {}
  if (typeof dyn.related_contracts === 'number') return dyn.related_contracts
  if (Array.isArray(dyn.related)) return dyn.related.length
  return null
}

// ---------- subcomponents ---------------------------------------------------

function MetricCard({ label, value, badge }) {
  return (
    <div
      className="rounded-xl p-3 border border-white/8"
      style={{ background: 'rgba(255,255,255,0.03)' }}
    >
      <div className="text-white/40 text-[10px] mb-1 uppercase tracking-wide">{label}</div>
      <div className="flex items-center gap-1.5 flex-wrap">
        <span className="text-white text-sm font-semibold">{value}</span>
        {badge && <RiskBadge level={badge} />}
      </div>
    </div>
  )
}

function ContractHeader({ contract, action, confidence, onRefresh, refreshing }) {
  const c = contract
  return (
    <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
      <div className="flex items-center gap-3">
        <div
          className="w-10 h-10 rounded-xl flex items-center justify-center text-lg shrink-0"
          style={{ background: 'linear-gradient(135deg, #FF6B35, #F7C59F)' }}
        >
          <Flame size={18} className="text-black/70" />
        </div>
        <div className="min-w-0">
          <h3 className="text-white font-semibold text-sm flex items-center gap-2 truncate">
            {c.contract_name || 'Unnamed contract'}
            {c.symbol && <span className="text-white/40 text-xs">({c.symbol})</span>}
          </h3>
          <div className="text-white/40 text-[11px] font-mono mt-0.5 truncate">{c.address}</div>
          <div className="flex items-center gap-3 mt-1">
            {[Globe, XIcon, MessageCircle].map((Icon, i) => (
              <Icon
                key={i}
                size={11}
                className="text-white/30 hover:text-white/60 cursor-pointer transition-colors"
              />
            ))}
            {c.verified ? (
              <span className="text-emerald-400/80 text-[10px] flex items-center gap-1">
                <ShieldCheck size={10} /> verified
              </span>
            ) : (
              <span className="text-amber-400/80 text-[10px] flex items-center gap-1">
                <AlertTriangle size={10} /> unverified
              </span>
            )}
            {c.is_proxy && <span className="text-violet-400/80 text-[10px]">proxy</span>}
            {c.prime_available && (
              <span className="text-cyan-300/80 text-[10px] flex items-center gap-1">
                <Sparkles size={10} /> prime
              </span>
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-3">
        <div className="flex flex-col items-end gap-1">
          <div className="text-white/40 text-[10px] uppercase tracking-wide">Action</div>
          <div className="flex items-center gap-2">
            <span className="text-white/85 text-xs font-medium">
              {(action || 'review').toUpperCase()}
            </span>
            <RiskBadge level={actionToBadge(action)} />
          </div>
          <div className="text-white/40 text-[10px] uppercase tracking-wide mt-1">Confidence</div>
          <div className="flex items-center gap-2">
            <span className="text-white/85 text-xs font-medium">
              {confidence != null ? `${(confidence * 100).toFixed(0)}%` : '—'}
            </span>
            <RiskBadge level="Info" />
          </div>
        </div>
        <div className="flex flex-col gap-1.5">
          <button
            onClick={onRefresh}
            disabled={refreshing}
            className="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-[11px] text-white/80 hover:text-white border border-white/15 hover:border-white/30 rounded-lg transition disabled:opacity-50"
          >
            <RefreshCw size={11} className={refreshing ? 'animate-spin' : ''} /> Re-analyze
          </button>
          <a
            href={`https://monadexplorer.com/address/${c.address}`}
            target="_blank"
            rel="noreferrer"
            className="flex items-center justify-center gap-1.5 px-2.5 py-1.5 text-[11px] text-white/80 hover:text-white border border-white/15 hover:border-white/30 rounded-lg transition"
          >
            Explorer <ExternalLink size={11} />
          </a>
        </div>
      </div>
    </div>
  )
}

function FindingsCarousel({ findings }) {
  const [tab, setTab] = useState('most')

  const sorted = useMemo(() => {
    const arr = (findings || []).slice()
    if (tab === 'most') {
      arr.sort(
        (a, b) =>
          severityRank(b.severity || b.tier) - severityRank(a.severity || a.tier) ||
          (b.weight || 0) - (a.weight || 0),
      )
    } else if (tab === 'least') {
      arr.sort(
        (a, b) =>
          severityRank(a.severity || a.tier) - severityRank(b.severity || b.tier) ||
          (a.weight || 0) - (b.weight || 0),
      )
    } else if (tab === 'confidence') {
      arr.sort((a, b) => (b.confidence || 0) - (a.confidence || 0))
    }
    return arr
  }, [findings, tab])

  const tabs = [
    { id: 'most', label: 'Most at risk' },
    { id: 'least', label: 'Least risk' },
    { id: 'confidence', label: 'Higher confidence' },
  ]

  return (
    <div id="findings" className="scroll-mt-24">
      <div className="flex items-center justify-between mb-3">
        <span className="text-white/70 text-xs font-medium">
          Findings <span className="text-white/30 ml-1">{sorted.length}</span>
        </span>
        <div className="flex gap-3 text-[10px]">
          {tabs.map((t) => (
            <button
              key={t.id}
              onClick={() => setTab(t.id)}
              className={`cursor-pointer transition-colors ${
                tab === t.id
                  ? 'text-white/85 border-b border-white/40'
                  : 'text-white/30 hover:text-white/60'
              }`}
            >
              {t.label}
            </button>
          ))}
        </div>
      </div>
      {sorted.length === 0 ? (
        <div className="text-white/40 text-xs border border-white/8 rounded-xl p-6 text-center">
          No findings yet — pipeline may still be enriching this contract.
        </div>
      ) : (
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-none">
          {sorted.map((f, i) => (
            <FindingCard
              key={f.id || f.code || i}
              title={f.title || f.code || 'Finding'}
              summary={f.description || f.evidence?.summary || ''}
              risk={f.severity || f.tier || 'info'}
              code={f.code}
            />
          ))}
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
    <div
      className="rounded-2xl border border-rose-500/20 p-5"
      style={{ background: 'rgba(255,61,119,0.04)' }}
    >
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

// ---------- dashboard view --------------------------------------------------

function ContractDashboard({ data, history, refresh, refreshing }) {
  const c = data.contract
  const latest = data.latest_analysis
  const calibration = latest?.summary_json?.exploit_calibration

  const action = c.action || latest?.action
  const confidence = c.confidence_score ?? latest?.confidence_score
  const prime = primeStateBadge(data.prime)
  const related = relatedCount(data)

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="relative rounded-3xl overflow-hidden border border-white/10"
      style={{
        background:
          'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%)',
      }}
    >
      {/* Glow accent — matches landing demo */}
      <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />

      <div className="p-5">
        <ContractHeader
          contract={c}
          action={action}
          confidence={confidence}
          onRefresh={refresh}
          refreshing={refreshing}
        />

        <ContractSparkline history={history} />

        <div id="screens" className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5 scroll-mt-24">
          <MetricCard
            label="Risk score"
            value={c.risk_score != null ? c.risk_score.toFixed(0) : '—'}
            badge={tierToBadge(c.risk_tier)}
          />
          <MetricCard
            label="Weighted findings"
            value={`${data.findings.length} flag${data.findings.length === 1 ? '' : 's'}`}
            badge={data.findings.length > 0 ? tierToBadge(c.risk_tier) : 'Info'}
          />
          <MetricCard label="Prime state" value={prime.value} badge={prime.badge} />
          <MetricCard
            label="Related contracts"
            value={related != null ? `${related} linked` : '—'}
            badge="Info"
          />
        </div>

        <FindingsCarousel findings={data.findings} />
      </div>

      <ExploitCalibration calibration={calibration} />

      {/* Meta row */}
      <div className="border-t border-white/8 px-5 py-3 grid grid-cols-2 md:grid-cols-4 gap-3 text-[11px] text-white/40">
        <div>
          First seen
          <br />
          <span className="text-white/70">{formatTime(c.first_seen_at)}</span>
        </div>
        <div>
          Last refreshed
          <br />
          <span className="text-white/70">{formatTime(c.last_refreshed_at)}</span>
        </div>
        <div>
          Next refresh
          <br />
          <span className="text-white/70">{formatTime(c.next_refresh_at)}</span>
        </div>
        <div>
          Creator
          <br />
          <span className="text-white/70 font-mono">{shortAddr(c.creator_address)}</span>
        </div>
      </div>
    </motion.div>
  )
}

// ---------- page ------------------------------------------------------------

export default function ContractIntelligence() {
  const { address: routeAddr } = useParams()
  const navigate = useNavigate()
  const [query, setQuery] = useState(routeAddr || '')
  const [data, setData] = useState(null)
  const [history, setHistory] = useState([])
  const [loading, setLoading] = useState(false)
  const [refreshing, setRefreshing] = useState(false)
  const [error, setError] = useState(null)
  const autoTriedRef = useRef(false)

  async function load(addr) {
    setLoading(true)
    setError(null)
    setQuery(addr)
    try {
      const result = await api.getContract(addr)
      setData(result)
      // History is best-effort — sparkline degrades gracefully when empty.
      try {
        const h = await api.getHistory(addr, 30)
        setHistory(h || [])
      } catch {
        setHistory([])
      }
    } catch (e) {
      setError(e.status === 404 ? 'Contract not found in case library yet.' : e.message)
      setData(null)
      setHistory([])
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
      try {
        const h = await api.getHistory(data.contract.address, 30)
        setHistory(h || [])
      } catch {
        /* keep prior history */
      }
    } catch (e) {
      setError(e.message)
    } finally {
      setRefreshing(false)
    }
  }

  // Address from URL → load directly. No address → auto-load a featured
  // contract (most-recent high-risk, fall back to most-recent overall).
  useEffect(() => {
    if (routeAddr) {
      autoTriedRef.current = false
      // eslint-disable-next-line react-hooks/set-state-in-effect
      load(routeAddr)
      return
    }
    if (autoTriedRef.current) return
    autoTriedRef.current = true
    ;(async () => {
      try {
        let pick = null
        try {
          const hr = await api.libraryHighRisk(1, 0)
          if (Array.isArray(hr) && hr.length > 0) pick = hr[0]
        } catch {
          /* ignore */
        }
        if (!pick) {
          const recent = await api.libraryRecent(1, 0)
          if (Array.isArray(recent) && recent.length > 0) pick = recent[0]
        }
        if (pick?.address) load(pick.address)
      } catch {
        /* leave empty state */
      }
    })()
  }, [routeAddr])

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div>
        <h1 className="text-white text-2xl md:text-3xl font-bold tracking-tight mb-1">
          Contract intelligence
        </h1>
        <p className="text-white/40 text-sm">
          Look up any Monad contract — verification, classification, findings, risk score, prime
          status.
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
          <p className="text-white/40 text-sm mb-4">
            No contracts indexed yet — the live ingestor is catching up. Try the public case
            library:
          </p>
          <Link
            to="/app/library/recent"
            className="inline-flex items-center gap-2 px-4 py-2 text-xs text-white/80 hover:text-white border border-white/15 hover:border-white/30 rounded-lg transition"
          >
            <Search size={12} /> Browse recent
          </Link>
        </div>
      )}

      {data && (
        <ContractDashboard
          data={data}
          history={history}
          refresh={refresh}
          refreshing={refreshing}
        />
      )}
    </div>
  )
}
