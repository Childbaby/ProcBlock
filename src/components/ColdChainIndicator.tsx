interface ColdChainIndicatorProps {
  status: 'normal' | 'warning' | 'compromised'
  temperature?: number
}

export function ColdChainIndicator({ status, temperature }: ColdChainIndicatorProps) {
  const config = {
    normal: { icon: '✅', label: 'Cold Chain Intact', color: 'text-emerald-600 bg-emerald-50 border-emerald-200' },
    warning: { icon: '⚠️', label: 'Temperature Deviation', color: 'text-amber-600 bg-amber-50 border-amber-200' },
    compromised: { icon: '🚨', label: 'COLD CHAIN BROKEN', color: 'text-red-600 bg-red-50 border-red-200' },
  }

  const c = config[status]

  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-pill border text-xs font-semibold ${c.color}`}>
      {c.icon} {c.label}
      {temperature !== undefined && <span className="font-mono">{temperature}°C</span>}
    </div>
  )
}
