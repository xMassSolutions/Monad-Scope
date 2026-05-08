const API_BASE = import.meta.env.VITE_API_BASE || '/api'

async function request(path, opts = {}) {
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...opts,
  })
  if (!res.ok) {
    const text = await res.text().catch(() => '')
    const err = new Error(text || `HTTP ${res.status}`)
    err.status = res.status
    throw err
  }
  return res.json()
}

export const api = {
  health: () => request('/health'),

  getContract: (address) => request(`/contracts/${address}`),
  getFindings: (address) => request(`/contracts/${address}/findings`),
  getHistory: (address, limit = 50) => request(`/contracts/${address}/history?limit=${limit}`),
  analyzeNow: (address) => request(`/contracts/${address}/analyze`, { method: 'POST' }),

  getProject: (projectId) => request(`/projects/${projectId}`),

  libraryRecent: (limit = 50, offset = 0) =>
    request(`/library/recent?limit=${limit}&offset=${offset}`),
  libraryHighRisk: (limit = 50, offset = 0) =>
    request(`/library/high-risk?limit=${limit}&offset=${offset}`),
}
