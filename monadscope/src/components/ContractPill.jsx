import { useState } from 'react'
import { Copy, Check, ExternalLink } from 'lucide-react'

function shortAddr(addr) {
  if (!addr) return ''
  return `${addr.slice(0, 6)}…${addr.slice(-4)}`
}

export default function ContractPill({ address, label = 'Contract' }) {
  const [copied, setCopied] = useState(false)

  function copy(e) {
    e.preventDefault()
    e.stopPropagation()
    navigator.clipboard.writeText(address).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1400)
    })
  }

  return (
    <div className="relative group inline-flex">
      <button
        type="button"
        className="flex items-center gap-1.5 px-3 py-1 rounded-full border border-white/15 bg-white/5 hover:bg-white/10 text-white/60 hover:text-white text-[11px] font-medium transition-colors"
      >
        <span className="w-1.5 h-1.5 rounded-full bg-cyan-400" />
        <span className="uppercase tracking-wider text-[10px] text-white/40 group-hover:text-white/60 transition-colors">
          {label}
        </span>
        <span className="font-mono">{shortAddr(address)}</span>
      </button>

      {/* Hover popover */}
      <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-[260px] opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all duration-150 z-50 pointer-events-none group-hover:pointer-events-auto">
        <div
          className="rounded-xl border border-white/10 p-3 backdrop-blur-md shadow-2xl"
          style={{ background: 'rgba(15,15,17,0.95)' }}
        >
          <div className="text-[10px] uppercase tracking-widest text-white/40 mb-1.5">
            {label} address
          </div>
          <div className="font-mono text-[11px] text-white/90 break-all leading-relaxed mb-2.5">
            {address}
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={copy}
              className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 text-[11px] transition-colors"
            >
              {copied ? <Check size={11} /> : <Copy size={11} />}
              {copied ? 'Copied' : 'Copy'}
            </button>
            <a
              href={`https://monadexplorer.com/address/${address}`}
              target="_blank"
              rel="noreferrer"
              className="flex-1 flex items-center justify-center gap-1.5 px-2 py-1.5 rounded-md bg-white/5 hover:bg-white/10 border border-white/10 text-white/80 text-[11px] transition-colors"
            >
              <ExternalLink size={11} />
              Explorer
            </a>
          </div>
        </div>
        {/* Arrow */}
        <div
          className="absolute left-1/2 -translate-x-1/2 -bottom-1 w-2 h-2 rotate-45 border-r border-b border-white/10"
          style={{ background: 'rgba(15,15,17,0.95)' }}
        />
      </div>
    </div>
  )
}
