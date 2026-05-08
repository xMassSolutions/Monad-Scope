import { Link, NavLink, Outlet } from 'react-router-dom'
import { useEffect, useState } from 'react'
import { api } from '../lib/api'
import { Activity, Search, Library, Network, ShieldAlert, Skull } from 'lucide-react'

function StatusPill() {
  const [health, setHealth] = useState(null)
  const [err, setErr] = useState(null)

  useEffect(() => {
    let mounted = true
    const tick = () =>
      api
        .health()
        .then((h) => mounted && (setHealth(h), setErr(null)))
        .catch((e) => mounted && setErr(e.message))
    tick()
    const id = setInterval(tick, 15000)
    return () => {
      mounted = false
      clearInterval(id)
    }
  }, [])

  const ok = !!health && !err
  return (
    <div
      className={`flex items-center gap-1.5 px-3 py-1 rounded-full border text-[11px] font-medium ${
        ok
          ? 'bg-emerald-500/10 border-emerald-500/30 text-emerald-300'
          : 'bg-red-500/10 border-red-500/30 text-red-300'
      }`}
    >
      <span
        className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-emerald-400 animate-pulse' : 'bg-red-400'}`}
      />
      {ok ? `${health.chain} · chain ${health.chain_id}` : 'API offline'}
    </div>
  )
}

export default function AppShell() {
  const linkBase =
    'flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm transition-colors'
  const linkIdle = 'text-white/50 hover:text-white hover:bg-white/5'
  const linkActive = 'bg-white/10 text-white'

  return (
    <div className="min-h-screen w-full bg-[#0A0A0B] text-white flex">
      {/* Sidebar */}
      <aside className="hidden md:flex w-60 shrink-0 flex-col border-r border-white/8 p-4 sticky top-0 h-screen" style={{ background: 'rgba(0,0,0,0.4)' }}>
        <Link to="/" className="flex items-center gap-2 mb-8 px-2">
          <img src="/logo.png" alt="MonadScope" className="w-7 h-7 object-contain" />
          <span className="text-white font-semibold text-sm tracking-tight">MonadScope</span>
        </Link>

        <nav className="flex flex-col gap-1">
          <NavLink
            to="/app"
            end
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <Search size={15} /> Contract intelligence
          </NavLink>
          <NavLink
            to="/app/library/recent"
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <Library size={15} /> Recent
          </NavLink>
          <NavLink
            to="/app/library/high-risk"
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <ShieldAlert size={15} /> High risk
          </NavLink>
          <NavLink
            to="/app/projects"
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <Network size={15} /> Projects
          </NavLink>
          <NavLink
            to="/app/exploits"
            className={({ isActive }) => `${linkBase} ${isActive ? linkActive : linkIdle}`}
          >
            <Skull size={15} /> Exploit registry
          </NavLink>
        </nav>

        <div className="mt-auto flex flex-col gap-2 px-1 text-[11px] text-white/30">
          <Link to="/" className="hover:text-white/60 transition-colors">← Back to landing</Link>
          <span>v0.1 · prototype</span>
        </div>
      </aside>

      {/* Main */}
      <main className="flex-1 min-w-0">
        <header className="sticky top-0 z-20 backdrop-blur-md border-b border-white/8 px-6 py-3 flex items-center justify-between gap-4" style={{ background: 'rgba(10,10,11,0.7)' }}>
          <div className="flex items-center gap-3 text-sm text-white/40">
            <Activity size={14} className="text-cyan-400" />
            <span>Live ingest · Monad mainnet</span>
          </div>
          <StatusPill />
        </header>
        <div className="p-6 md:p-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
