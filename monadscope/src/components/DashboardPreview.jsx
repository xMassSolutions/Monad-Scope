import { motion } from 'motion/react'
import { TrendingUp, AlertTriangle, CheckCircle, Globe, MessageCircle, X } from 'lucide-react'

function RiskBadge({ level }) {
  const styles = {
    Critical: 'bg-red-500/20 text-red-400 border border-red-500/30',
    Info: 'bg-blue-500/20 text-blue-400 border border-blue-500/30',
    Success: 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30',
  }
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold ${styles[level]}`}>
      {level}
    </span>
  )
}

function FindingCard({ title, summary, risk, color }) {
  const borderColors = {
    red: 'border-l-red-500',
    teal: 'border-l-teal-400',
    green: 'border-l-emerald-400',
  }
  return (
    <div className={`flex-shrink-0 w-48 rounded-xl p-3 border border-white/8 border-l-2 ${borderColors[color]}`} style={{ background: 'rgba(255,255,255,0.04)' }}>
      <p className="text-white/80 text-[11px] font-medium leading-snug mb-2">{title}</p>
      <p className="text-white/40 text-[10px] leading-snug mb-3">{summary}</p>
      <RiskBadge level={risk} />
    </div>
  )
}

export default function DashboardPreview() {
  const chartData = [320, 480, 290, 610, 520, 780, 690, 820, 750, 910]

  return (
    <section id="app-shell" className="w-full py-24 px-6 md:px-12 overflow-hidden scroll-mt-16">
      <motion.div
        initial={{ opacity: 0, y: 30 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true }}
        transition={{ duration: 0.8, ease: 'easeOut' }}
        className="max-w-5xl mx-auto"
      >
        {/* Section label */}
        <div className="text-center mb-12">
          <span className="inline-block px-3 py-1 mb-4 text-xs font-medium tracking-widest uppercase text-white/40 border border-white/10 rounded-full">
            App Shell
          </span>
          <h2 className="text-3xl md:text-4xl font-bold text-white tracking-tight mb-4">
            Contract Intelligence Dashboard
          </h2>
          <p className="text-white/40 text-base max-w-md mx-auto">
            Risk score, findings, and prime status — every Monad contract in one unified view.
          </p>
          <div className="mt-4 inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full border border-white/10 text-[10px] uppercase tracking-widest text-white/40">
            <span className="w-1 h-1 rounded-full bg-amber-400" /> Demo · sample contract
          </div>
        </div>

        {/* Dashboard mockup */}
        <div
          className="relative rounded-3xl overflow-hidden border border-white/10"
          style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.04) 0%, rgba(255,255,255,0.02) 100%)' }}
        >
          {/* Glow accent */}
          <div className="absolute top-0 left-1/2 -translate-x-1/2 w-96 h-px bg-gradient-to-r from-transparent via-white/20 to-transparent" />

          <div className="flex">
            {/* Sidebar */}
            <div className="hidden md:flex flex-col w-52 border-r border-white/8 p-4 gap-1" style={{ background: 'rgba(0,0,0,0.3)' }}>
              <div className="flex items-center gap-2 mb-6 px-2">
                <img src="/logo.png" alt="MonadScope" decoding="async" loading="lazy" className="w-6 h-6 object-contain" />
                <span className="text-white/80 text-sm font-semibold">MonadScope</span>
              </div>
              {['Contract intelligence', 'Project graph', 'Public library'].map((item, i) => (
                <div
                  key={item}
                  className={`flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm cursor-pointer transition-colors ${i === 0 ? 'bg-white/10 text-white' : 'text-white/40 hover:text-white/70 hover:bg-white/5'}`}
                >
                  <div className="w-1.5 h-1.5 rounded-full bg-current opacity-60" />
                  {item}
                </div>
              ))}
            </div>

            {/* Main content */}
            <div className="flex-1 p-5 overflow-hidden">
              {/* Contract header */}
              <div className="flex items-start justify-between mb-5 flex-wrap gap-3">
                <div className="flex items-center gap-3">
                  <div className="w-10 h-10 rounded-xl flex items-center justify-center text-lg" style={{ background: 'linear-gradient(135deg, #FF6B35, #F7C59F)' }}>
                    🔥
                  </div>
                  <div>
                    <h3 className="text-white font-semibold text-sm">NovaBurn Token (NBRN)</h3>
                    <div className="flex items-center gap-3 mt-1">
                      {[Globe, X, MessageCircle].map((Icon, i) => (
                        <Icon key={i} size={11} className="text-white/30 hover:text-white/60 cursor-pointer transition-colors" />
                      ))}
                    </div>
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1">
                  <div className="text-white/40 text-[10px]">Action</div>
                  <div className="flex items-center gap-2">
                    <span className="text-white/80 text-xs font-medium">ESCALATE</span>
                    <RiskBadge level="Critical" />
                  </div>
                  <div className="text-white/40 text-[10px] mt-1">Confidence</div>
                  <div className="flex items-center gap-2">
                    <span className="text-white/80 text-xs font-medium">68%</span>
                    <RiskBadge level="Info" />
                  </div>
                </div>
              </div>

              {/* Chart */}
              <div className="h-28 mb-5 relative">
                <svg viewBox="0 0 400 100" className="w-full h-full" preserveAspectRatio="none">
                  <defs>
                    <linearGradient id="line1" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#3B82F6" />
                      <stop offset="100%" stopColor="#06B6D4" />
                    </linearGradient>
                    <linearGradient id="line2" x1="0" y1="0" x2="1" y2="0">
                      <stop offset="0%" stopColor="#F59E0B" />
                      <stop offset="100%" stopColor="#EF4444" />
                    </linearGradient>
                    <linearGradient id="fill1" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.2" />
                      <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
                    </linearGradient>
                  </defs>
                  <path d="M0 80 C40 70, 80 30, 120 40 C160 50, 200 20, 240 15 C280 10, 320 25, 360 10 L400 5 L400 100 L0 100Z" fill="url(#fill1)" />
                  <path d="M0 80 C40 70, 80 30, 120 40 C160 50, 200 20, 240 15 C280 10, 320 25, 360 10 L400 5" fill="none" stroke="url(#line1)" strokeWidth="2" />
                  <path d="M0 90 C40 85, 80 60, 120 65 C160 70, 200 50, 240 55 C280 60, 320 45, 360 35 L400 30" fill="none" stroke="url(#line2)" strokeWidth="1.5" strokeDasharray="4 2" />
                </svg>
                <div className="absolute bottom-0 left-0 right-0 flex justify-between text-white/20 text-[9px] px-1">
                  {['Jan', 'Mar', 'May', 'Jul', 'Aug', 'Sep'].map(m => <span key={m}>{m}</span>)}
                </div>
              </div>

              {/* Risk metrics row */}
              <div id="screens" className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-5 scroll-mt-24">
                {[
                  { label: 'Risk score', value: '82', badge: 'Critical' },
                  { label: 'Weighted findings', value: '4 flags', badge: 'Critical' },
                  { label: 'Prime state', value: 'Visible', badge: 'Success' },
                  { label: 'Related contracts', value: '6 linked', badge: 'Info' },
                ].map(({ label, value, badge }) => (
                  <div key={label} className="rounded-xl p-3 border border-white/8" style={{ background: 'rgba(255,255,255,0.03)' }}>
                    <div className="text-white/40 text-[10px] mb-1">{label}</div>
                    <div className="flex items-center gap-1.5 flex-wrap">
                      <span className="text-white text-sm font-semibold">{value}</span>
                      <RiskBadge level={badge} />
                    </div>
                  </div>
                ))}
              </div>

              {/* Findings */}
              <div id="findings" className="scroll-mt-24">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-white/60 text-xs font-medium">Findings</span>
                  <div className="flex gap-2 text-[10px]">
                    {['Most at risk', 'Least risk', 'Higher confidence'].map((tab, i) => (
                      <span key={tab} className={`cursor-pointer transition-colors ${i === 0 ? 'text-white/80 border-b border-white/40' : 'text-white/30 hover:text-white/60'}`}>{tab}</span>
                    ))}
                  </div>
                </div>
                <div className="flex gap-3 overflow-x-auto pb-1 scrollbar-none">
                  <FindingCard
                    title="Contract reentrancy detected in transfer logic"
                    summary="Recursive call pattern found in withdraw function allows state manipulation."
                    risk="Critical"
                    color="red"
                  />
                  <FindingCard
                    title="Token inflation mechanism lacks supply cap"
                    summary="Mint function callable by owner without hard cap enforcement."
                    risk="Critical"
                    color="red"
                  />
                  <FindingCard
                    title="Ownership not renounced — admin keys active"
                    summary="Contract deployer retains full upgrade and pause authority."
                    risk="Info"
                    color="teal"
                  />
                  <FindingCard
                    title="Liquidity lock verified on-chain"
                    summary="LP tokens locked for 180 days via third-party locker."
                    risk="Success"
                    color="green"
                  />
                </div>
              </div>
            </div>
          </div>

          {/* Bottom bar */}
          <div className="border-t border-white/8 px-5 py-3 flex items-center justify-between" style={{ background: 'rgba(0,0,0,0.2)' }}>
            <div className="flex items-center gap-6">
              <div className="flex flex-col">
                <span className="text-white/30 text-[9px] uppercase tracking-wide">Last block</span>
                <span className="text-white/70 text-xs font-mono font-semibold">58,291,114</span>
              </div>
              <div className="flex flex-col">
                <span className="text-white/30 text-[9px] uppercase tracking-wide">Queue lag</span>
                <span className="text-white/70 text-xs font-mono font-semibold">0.7s</span>
              </div>
            </div>
            <div className="flex items-center gap-1.5">
              <div className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
              <span className="text-emerald-400/80 text-[10px] font-medium">Live</span>
            </div>
          </div>
        </div>
      </motion.div>
    </section>
  )
}
