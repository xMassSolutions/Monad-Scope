// Two-line SVG sparkline matching the landing demo:
//   - solid blue→cyan line: risk_score over time
//   - dashed amber→red line: confidence_score over time
//
// Falls back to a flat baseline when there's <2 history rows so the layout
// never collapses.

function buildPath(values, vbWidth, vbHeight, padTop = 5, padBottom = 5) {
  if (!values || values.length === 0) {
    return `M0 ${vbHeight - padBottom} L${vbWidth} ${vbHeight - padBottom}`
  }
  const n = values.length
  if (n === 1) {
    const y = vbHeight / 2
    return `M0 ${y} L${vbWidth} ${y}`
  }
  const min = Math.min(...values)
  const max = Math.max(...values)
  const span = max - min || 1
  const innerH = vbHeight - padTop - padBottom
  const xs = values.map((_, i) => (i / (n - 1)) * vbWidth)
  const ys = values.map((v) => padTop + (1 - (v - min) / span) * innerH)

  // Cubic-ish smooth path using midpoint Bezier handles.
  let d = `M${xs[0].toFixed(1)} ${ys[0].toFixed(1)}`
  for (let i = 1; i < n; i++) {
    const xPrev = xs[i - 1]
    const yPrev = ys[i - 1]
    const x = xs[i]
    const y = ys[i]
    const cx = (xPrev + x) / 2
    d += ` C${cx.toFixed(1)} ${yPrev.toFixed(1)}, ${cx.toFixed(1)} ${y.toFixed(1)}, ${x.toFixed(1)} ${y.toFixed(1)}`
  }
  return d
}

function buildAreaPath(values, vbWidth, vbHeight, padTop = 5, padBottom = 5) {
  const linePath = buildPath(values, vbWidth, vbHeight, padTop, padBottom)
  return `${linePath} L${vbWidth} ${vbHeight} L0 ${vbHeight} Z`
}

export default function ContractSparkline({ history, monthLabels }) {
  // Sort oldest → newest. Backend returns newest-first via history_for_contract.
  const sorted = (history || []).slice().reverse()
  const risk = sorted.map((r) => Number(r.risk_score) || 0)
  // Confidence is 0..1 — scale to 0..100 to share the visual range.
  const conf = sorted.map((r) => (Number(r.confidence_score) || 0) * 100)

  const VB_W = 400
  const VB_H = 100

  const riskPath = buildPath(risk, VB_W, VB_H)
  const riskArea = buildAreaPath(risk, VB_W, VB_H)
  const confPath = buildPath(conf, VB_W, VB_H)

  const labels = monthLabels || ['Jan', 'Mar', 'May', 'Jul', 'Aug', 'Sep']

  return (
    <div className="h-28 mb-5 relative">
      <svg viewBox={`0 0 ${VB_W} ${VB_H}`} className="w-full h-full" preserveAspectRatio="none">
        <defs>
          <linearGradient id="msc-line1" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#3B82F6" />
            <stop offset="100%" stopColor="#06B6D4" />
          </linearGradient>
          <linearGradient id="msc-line2" x1="0" y1="0" x2="1" y2="0">
            <stop offset="0%" stopColor="#F59E0B" />
            <stop offset="100%" stopColor="#EF4444" />
          </linearGradient>
          <linearGradient id="msc-fill1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3B82F6" stopOpacity="0.2" />
            <stop offset="100%" stopColor="#3B82F6" stopOpacity="0" />
          </linearGradient>
        </defs>
        <path d={riskArea} fill="url(#msc-fill1)" />
        <path d={riskPath} fill="none" stroke="url(#msc-line1)" strokeWidth="2" />
        <path
          d={confPath}
          fill="none"
          stroke="url(#msc-line2)"
          strokeWidth="1.5"
          strokeDasharray="4 2"
        />
      </svg>
      <div className="absolute bottom-0 left-0 right-0 flex justify-between text-white/20 text-[9px] px-1">
        {labels.map((m, i) => (
          <span key={`${m}-${i}`}>{m}</span>
        ))}
      </div>
    </div>
  )
}
