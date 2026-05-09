import { Link, NavLink, Outlet } from 'react-router-dom'
import { Activity, Search, Library, Network, ShieldAlert, Skull } from 'lucide-react'
import LiveStatusBar from './dashboard/LiveStatusBar'

const NAV_ITEMS = [
  { to: '/app', end: true, icon: Search, label: 'Contract intelligence' },
  { to: '/app/library/recent', icon: Library, label: 'Recent' },
  { to: '/app/library/high-risk', icon: ShieldAlert, label: 'High risk' },
  { to: '/app/projects', icon: Network, label: 'Projects' },
  { to: '/app/exploits', icon: Skull, label: 'Exploit registry' },
]

function SidebarLink({ item }) {
  return (
    <NavLink
      to={item.to}
      end={item.end}
      className={({ isActive }) =>
        `flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-sm cursor-pointer transition-colors ${
          isActive
            ? 'bg-white/10 text-white'
            : 'text-white/40 hover:text-white/80 hover:bg-white/5'
        }`
      }
    >
      {({ isActive }) => (
        <>
          <span
            className={`w-1.5 h-1.5 rounded-full ${
              isActive ? 'bg-white' : 'bg-current opacity-60'
            }`}
          />
          <item.icon size={14} className="opacity-70" />
          <span>{item.label}</span>
        </>
      )}
    </NavLink>
  )
}

export default function AppShell() {
  return (
    <div className="relative min-h-screen w-full bg-[#0A0A0B] text-white">
      {/* Shared fluid backdrop — same AVIF as the landing page so /app feels
          like the same product, not a separate dashboard. */}
      <div aria-hidden className="pointer-events-none fixed inset-0 z-0 overflow-hidden">
        <img
          src="/background.avif"
          alt=""
          aria-hidden
          decoding="async"
          className="bg-fluid absolute inset-0 w-full h-full object-cover opacity-20"
          style={{ animationDuration: '60s' }}
        />
        <div
          className="absolute inset-0"
          style={{
            background:
              'radial-gradient(ellipse at center, rgba(10,10,11,0.55) 0%, rgba(10,10,11,0.8) 70%, rgba(10,10,11,0.95) 100%)',
          }}
        />
      </div>

      <div className="relative z-10 flex">
        {/* Sidebar — matches DashboardPreview.jsx visual language */}
        <aside
          className="hidden md:flex w-60 shrink-0 flex-col border-r border-white/8 p-4 sticky top-0 h-screen"
          style={{ background: 'rgba(0,0,0,0.4)' }}
        >
          <Link to="/" className="flex items-center gap-2 mb-8 px-2">
            <img
              src="/logo.png"
              alt="MonadScope"
              decoding="async"
              className="w-7 h-7 object-contain"
            />
            <span className="text-white/90 font-semibold text-sm tracking-tight">MonadScope</span>
          </Link>

          <nav className="flex flex-col gap-1">
            {NAV_ITEMS.map((item) => (
              <SidebarLink key={item.to} item={item} />
            ))}
          </nav>

          <div className="mt-auto flex flex-col gap-2 px-1 text-[11px] text-white/30">
            <Link to="/" className="hover:text-white/60 transition-colors">
              ← Back to landing
            </Link>
          </div>
        </aside>

        {/* Main */}
        <main className="flex-1 min-w-0 flex flex-col min-h-screen">
          <header
            className="sticky top-0 z-20 backdrop-blur-md border-b border-white/8 px-6 py-3 flex items-center justify-between gap-4"
            style={{ background: 'rgba(10,10,11,0.7)' }}
          >
            <div className="flex items-center gap-3 text-sm text-white/40">
              <Activity size={14} className="text-cyan-400" />
              <span>Live ingest · Monad mainnet</span>
            </div>
          </header>

          <div className="flex-1 p-6 md:p-8">
            <Outlet />
          </div>

          {/* Bottom live status bar — single source of truth for liveness,
              mirrors DashboardPreview.jsx's bottom bar visually. */}
          <LiveStatusBar />
        </main>
      </div>
    </div>
  )
}
