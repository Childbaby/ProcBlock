interface HubNode {
  id: string
  name: string
  status: 'online' | 'offline' | 'degraded'
  stockLevel: number
  transactionCount: number
  lastUpdate: string
}

interface GeospatialMapperPanelProps {
  hubs: HubNode[]
  isLoading?: boolean
}

export function GeospatialMapperPanel({ hubs, isLoading = false }: GeospatialMapperPanelProps) {
  const statusIndicator = (status: HubNode['status']) => {
    switch (status) {
      case 'online':
        return <span className="badge-online">Online</span>
      case 'offline':
        return <span className="badge-offline">Offline</span>
      case 'degraded':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-xs font-semibold bg-amber-50 text-amber-700">
            <span className="w-2 h-2 rounded-full bg-amber-500" />
            Degraded
          </span>
        )
    }
  }

  return (
    <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-navy-800">
            Hub Network Status
          </h3>
          <p className="text-sm text-navy-500 mt-0.5">
            AI-powered regional distribution analysis
          </p>
        </div>
        <span className="text-xs text-navy-400">
          {isLoading ? 'Loading...' : `${hubs.length} hubs monitored`}
        </span>
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-navy-400">
          <div className="w-8 h-8 mx-auto mb-3 border-2 border-navy-300 border-t-teal-medical rounded-full animate-spin" />
          <p className="text-sm">Loading hub data...</p>
        </div>
      ) : hubs.length === 0 ? (
        <div className="text-center py-16 text-navy-400">
          <p className="text-sm">No hub data available</p>
        </div>
      ) : (
        <>
          <div className="relative bg-clinical-100 rounded-medical p-6 mb-6 min-h-[200px] flex items-center justify-center">
            <div className="text-center">
              <svg width="240" height="200" viewBox="0 0 240 200" className="mx-auto" aria-hidden="true">
                <circle cx="120" cy="100" r="20" className="fill-navy-800" />
                <text x="120" y="104" textAnchor="middle" className="fill-clinical-50 text-[8px] font-semibold">LUSAKA</text>
                {[0, 72, 144, 216, 288].map((angle, idx) => {
                  const rad = (angle * Math.PI) / 180
                  const x = 120 + 90 * Math.cos(rad)
                  const y = 100 + 60 * Math.sin(rad)
                  return (
                    <g key={idx}>
                      <line x1="120" y1="100" x2={x} y2={y} className="stroke-clinical-300" strokeWidth="1.5" strokeDasharray="4 4" />
                      <circle cx={x} cy={y} r="8" className="fill-clinical-50 stroke-teal-medical" strokeWidth="2" />
                      <text x={x} y={y + 3} textAnchor="middle" className="fill-navy-600 text-[7px] font-medium">
                        {hubs[idx + 1]?.name?.split(' ')[0] || `HUB ${idx + 2}`}
                      </text>
                    </g>
                  )
                })}
              </svg>
              <p className="text-xs text-navy-400 mt-2">
                Schematic representation — AI-analyzed distribution
              </p>
            </div>
          </div>

          <div className="space-y-2 max-h-[300px] overflow-y-auto scrollbar-thin">
            {hubs.map((hub) => (
              <div key={hub.id} className="flex items-center justify-between py-3 px-4 rounded-medical bg-clinical-100 border border-clinical-200">
                <div className="flex items-center gap-3">
                  {statusIndicator(hub.status)}
                  <div>
                    <p className="text-sm font-medium text-navy-800">{hub.name}</p>
                    <p className="text-xs text-navy-400">{hub.transactionCount} transactions</p>
                  </div>
                </div>
                <div className="text-right">
                  <p className="text-sm font-semibold text-navy-700">{hub.stockLevel}%</p>
                  <p className="text-xs text-navy-400">Stock Level</p>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}
