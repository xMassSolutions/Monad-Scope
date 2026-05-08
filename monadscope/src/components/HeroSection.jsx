import { motion } from 'motion/react'
import { ArrowRight, Activity } from 'lucide-react'
import { Link } from 'react-router-dom'

export default function HeroSection() {
  return (
    <section className="relative w-full min-h-screen flex flex-col items-center justify-center overflow-hidden">
      {/* Hero shares the page-wide fluid backdrop — no local overlay, so the
          section blends seamlessly into the rest of the landing page. */}

      {/* Navbar */}
      <nav className="absolute top-0 left-0 right-0 z-30 flex items-center justify-between px-6 md:px-12 py-6">
        <Link to="/" className="flex items-center gap-3">
          <img src="/logo.png" alt="MonadScope" decoding="async" className="w-9 h-9 object-contain" />
          <span className="text-white font-semibold text-lg tracking-tight">MonadScope</span>
        </Link>
        <div className="hidden md:flex items-center gap-8">
          {[
            { label: 'Features', href: '#features' },
            { label: 'App Shell', href: '#app-shell' },
            { label: 'Screens', href: '#screens' },
            { label: 'Findings', href: '#findings' },
          ].map(({ label, href }) => (
            <a
              key={label}
              href={href}
              className="text-white/70 hover:text-white text-sm font-medium transition-colors duration-200"
            >
              {label}
            </a>
          ))}
        </div>
        <div className="w-[120px]" />
      </nav>

      {/* Hero Content */}
      <div className="relative z-20 flex flex-col items-center justify-center text-center px-6 max-w-4xl mx-auto">
        {/* Badge */}
        <motion.div
          initial={{ opacity: 0, y: -10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.6, ease: 'easeOut' }}
          className="inline-flex items-center gap-2 px-4 py-2 mb-8 rounded-full border border-white/15 backdrop-blur-sm"
          style={{ background: 'rgba(255,255,255,0.06)' }}
        >
          <Activity size={14} className="text-cyan-400" />
          <span className="text-white/80 text-xs font-medium tracking-wide uppercase">Live on Monad Mainnet</span>
        </motion.div>

        {/* Main headline */}
        <motion.h1
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.15 }}
          className="text-5xl md:text-7xl lg:text-8xl font-bold text-white tracking-tight leading-[1.05] mb-6"
        >
          Smart Contract
          <br />
          <span style={{ background: 'linear-gradient(135deg, #60D5FA 0%, #A78BFA 50%, #F472B6 100%)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', backgroundClip: 'text' }}>
            Intelligence
          </span>
        </motion.h1>

        {/* Subheadline */}
        <motion.p
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.25 }}
          className="text-white/60 text-lg md:text-xl max-w-xl mx-auto leading-relaxed mb-10"
        >
          Deep analysis and real-time risk scoring for every contract on Monad. Understand what you're interacting with before you sign.
        </motion.p>

        {/* CTA buttons */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.35 }}
          className="flex flex-col sm:flex-row items-center gap-4"
        >
          <Link
            to="/app"
            className="group flex items-center gap-2 px-8 py-4 rounded-full text-black font-semibold text-base hover:scale-[1.02] transition-transform duration-200"
            style={{ background: 'linear-gradient(135deg, #60D5FA 0%, #A78BFA 100%)' }}
          >
            Launch App
            <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform duration-200" />
          </Link>
          <Link
            to="/app/library/recent"
            className="flex items-center gap-2 px-8 py-4 rounded-full text-white/80 hover:text-white font-medium text-base border border-white/15 hover:border-white/30 backdrop-blur-sm transition-all duration-200"
            style={{ background: 'rgba(255,255,255,0.05)' }}
          >
            Browse Library
          </Link>
        </motion.div>

        {/* Stats row */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: 'easeOut', delay: 0.5 }}
          className="flex items-center gap-10 mt-16"
        >
          {[
            { value: '143', label: 'Monad Mainnet · chain id' },
            { value: 'Voted', label: 'block finality · no reorgs' },
            { value: 'WSS', label: 'streaming ingest' },
          ].map(({ value, label }) => (
            <div key={label} className="flex flex-col items-center gap-1">
              <span className="text-white font-bold text-2xl tracking-tight">{value}</span>
              <span className="text-white/40 text-xs font-medium tracking-wide">{label}</span>
            </div>
          ))}
        </motion.div>
      </div>

      {/* Scroll indicator */}
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 1, delay: 1 }}
        className="absolute bottom-8 left-1/2 -translate-x-1/2 z-20 flex flex-col items-center gap-2"
      >
        <span className="text-white/30 text-xs tracking-widest uppercase">Scroll</span>
        <motion.div
          animate={{ y: [0, 6, 0] }}
          transition={{ duration: 1.5, repeat: Infinity, ease: 'easeInOut' }}
          className="w-px h-8 bg-gradient-to-b from-white/30 to-transparent"
        />
      </motion.div>
    </section>
  )
}
