interface Anomaly {
  id: string
  type: 'counterfeit' | 'expiry' | 'stockout' | 'temperature' | 'custody'
  severity: 'high' | 'medium' | 'low'
  message: string
  location: string
  timestamp: string
  status: 'active' | 'resolved' | 'investigating'
  score?: number
}

interface AnomalyDetectorPanelProps {
  anomalies: Anomaly[]
  isLoading?: boolean
  onResolve?: (id: string) => void
  onInvestigate?: (id: string) => void
}

export function AnomalyDetectorPanel({ anomalies, isLoading = false, onResolve, onInvestigate }: AnomalyDetectorPanelProps) {
  const severityStyles = {
    high: { badge: 'bg-red-50 text-red-700 border-red-200', dot: 'bg-red-500' },
    medium: { badge: 'bg-amber-50 text-amber-700 border-amber-200', dot: 'bg-amber-500' },
    low: { badge: 'bg-sky-50 text-sky-700 border-sky-200', dot: 'bg-sky-500' },
  }

  const statusLabels = {
    active: 'Active',
    resolved: 'Resolved',
    investigating: 'Investigating',
  }

  const activeCount = anomalies.filter(a => a.status === 'active').length

  return (
    <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-navy-800">
            AI Anomaly Detection
          </h3>
          <p className="text-sm text-navy-500 mt-0.5">
            Isolation Forest · Real-time analysis
          </p>
        </div>
        {!isLoading && (
          <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold border ${activeCount > 0 ? 'bg-red-50 text-red-700 border-red-200' : 'bg-emerald-50 text-emerald-700 border-emerald-200'}`}>
            <span className={`w-2 h-2 rounded-full ${activeCount > 0 ? 'bg-red-500 animate-pulse-status' : 'bg-emerald-500'}`} />
            {activeCount} Active
          </span>
        )}
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-navy-400">
          <div className="w-8 h-8 mx-auto mb-3 border-2 border-navy-300 border-t-teal-medical rounded-full animate-spin" />
          <p className="text-sm">AI model analyzing supply chain data...</p>
        </div>
      ) : anomalies.length === 0 ? (
        <div className="text-center py-12 text-navy-400">
          <svg className="w-12 h-12 mx-auto mb-3 text-navy-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <p className="text-sm font-medium">No anomalies detected</p>
          <p className="text-xs mt-1">AI model confirms supply chain integrity</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[400px] overflow-y-auto scrollbar-thin">
          {anomalies.map((anomaly) => (
            <div key={anomaly.id} className="p-4 rounded-medical border border-clinical-200 bg-clinical-100 hover:bg-clinical-200 transition-colors duration-150">
              <div className="flex items-start justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className={`inline-flex items-center gap-1.5 px-2 py-0.5 rounded-pill text-xs font-semibold border ${severityStyles[anomaly.severity].badge}`}>
                    <span className={`w-1.5 h-1.5 rounded-full ${severityStyles[anomaly.severity].dot}`} />
                    {anomaly.severity.toUpperCase()}
                  </span>
                  <span className="text-xs text-navy-400">{anomaly.type.replace(/_/g, ' ').toUpperCase()}</span>
                  {anomaly.score && (
                    <span className="text-xs text-navy-400 font-mono">Score: {anomaly.score}</span>
                  )}
                </div>
                <span className="text-xs text-navy-400">{anomaly.timestamp}</span>
              </div>
              <p className="text-sm text-navy-700 mb-1">{anomaly.message}</p>
              <p className="text-xs text-navy-400 mb-3">Location: {anomaly.location}</p>
              <div className="flex items-center gap-2">
                <span className="text-xs font-medium text-navy-500">{statusLabels[anomaly.status]}</span>
                {anomaly.status === 'active' && (
                  <div className="flex gap-2 ml-auto">
                    <button onClick={() => onInvestigate?.(anomaly.id)} className="text-xs font-medium text-navy-600 px-3 py-1 rounded-medical hover:bg-navy-50 transition-colors">
                      Investigate
                    </button>
                    <button onClick={() => onResolve?.(anomaly.id)} className="text-xs font-medium text-status-verified px-3 py-1 rounded-medical hover:bg-emerald-50 transition-colors">
                      Resolve
                    </button>
                  </div>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
