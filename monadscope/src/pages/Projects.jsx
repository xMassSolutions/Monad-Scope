import { useState } from 'react'
import { motion } from 'motion/react'
import { Link } from 'react-router-dom'
import { Network, Search } from 'lucide-react'
import { api } from '../lib/api'
import { shortAddr } from '../lib/format'

export default function Projects() {
  const [pid, setPid] = useState('')
  const [project, setProject] = useState(null)
  const [error, setError] = useState(null)
  const [loading, setLoading] = useState(false)

  async function lookup(e) {
    e.preventDefault()
    setLoading(true)
    setError(null)
    try {
      const data = await api.getProject(pid.trim())
      setProject(data)
    } catch (err) {
      setError(err.status === 404 ? 'Project not found.' : err.message)
      setProject(null)
    } finally {
      setLoading(false)
    }
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="max-w-5xl mx-auto space-y-6"
    >
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 rounded-xl flex items-center justify-center" style={{ background: 'linear-gradient(135deg, #4361EE, #F72585)' }}>
          <Network size={18} className="text-white" />
        </div>
        <div>
          <h1 className="text-white text-2xl md:text-3xl font-bold tracking-tight">Projects</h1>
          <p className="text-white/40 text-sm">Look up a project group and its linked contracts.</p>
        </div>
      </div>

      <form onSubmit={lookup} className="flex gap-2">
        <div className="flex-1 relative">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-white/40" />
          <input
            value={pid}
            onChange={(e) => setPid(e.target.value)}
            placeholder="project id"
            className="w-full bg-white/5 border border-white/10 focus:border-white/30 rounded-xl pl-9 pr-3 py-3 text-sm text-white font-mono placeholder:text-white/30 outline-none transition"
            spellCheck={false}
          />
        </div>
        <button
          type="submit"
          disabled={loading || !pid}
          className="px-5 py-3 bg-white text-black rounded-xl font-semibold text-sm hover:bg-white/90 disabled:opacity-50 transition"
        >
          {loading ? 'Loading…' : 'Lookup'}
        </button>
      </form>

      {error && (
        <div className="rounded-xl border border-red-500/30 bg-red-500/10 text-red-300 text-sm p-4">
          {error}
        </div>
      )}

      {project && (
        <div className="space-y-4">
          <div className="rounded-2xl border border-white/10 p-5" style={{ background: 'linear-gradient(135deg, rgba(255,255,255,0.04), rgba(255,255,255,0.02))' }}>
            <div className="text-white/40 text-[10px] uppercase tracking-widest mb-1">Project</div>
            <h2 className="text-white text-xl font-semibold">
              {project.project.name || project.project.id}
            </h2>
            <div className="text-white/40 text-xs font-mono mt-1">{project.project.id}</div>
          </div>

          <div>
            <div className="text-white/60 text-sm font-semibold mb-2">
              Linked contracts ({project.contract_ids.length})
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
              {project.contract_ids.map((id) => (
                <div key={id} className="rounded-lg border border-white/8 px-3 py-2 text-xs font-mono text-white/60">
                  {shortAddr(id)}
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {!project && !error && (
        <div className="rounded-2xl border border-dashed border-white/10 p-10 text-center text-white/40 text-sm">
          Enter a project id to view its linked contracts.
          <div className="mt-3">
            <Link to="/app/library/recent" className="text-white/70 hover:text-white text-xs underline underline-offset-4">
              Or start from a contract →
            </Link>
          </div>
        </div>
      )}
    </motion.div>
  )
}
