'use client'

import { useState } from 'react'

interface CustodyEvent {
  timestamp: string
  from: string
  to: string
  location: string
  transactionHash: string
  verified: boolean
}

interface CNFTAsset {
  id: string
  cnfId: string
  commodity: string
  lotNumber: string
  manufacturer: string
  expiryDate: string
  mintedAt: string
  currentCustodian: string
  currentLocation: string
  status: 'active' | 'quarantined' | 'expired' | 'consumed'
  custodyChain: CustodyEvent[]
}

interface CNFTCustodyPanelProps {
  assets: CNFTAsset[]
  isLoading?: boolean
}

export function CNFTCustodyPanel({ assets, isLoading = false }: CNFTCustodyPanelProps) {
  const [selectedAsset, setSelectedAsset] = useState<CNFTAsset | null>(null)
  const [searchTerm, setSearchTerm] = useState('')

  const filteredAssets = assets.filter(
    (a) =>
      a.cnfId.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.commodity.toLowerCase().includes(searchTerm.toLowerCase()) ||
      a.lotNumber.toLowerCase().includes(searchTerm.toLowerCase())
  )

  const statusConfig = {
    active: {
      label: 'Active',
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      dot: 'bg-emerald-500',
    },
    quarantined: {
      label: 'Quarantined',
      badge: 'bg-red-50 text-red-700 border-red-200',
      dot: 'bg-red-500 animate-pulse',
    },
    expired: {
      label: 'Expired',
      badge: 'bg-slate-50 text-slate-600 border-slate-200',
      dot: 'bg-slate-400',
    },
    consumed: {
      label: 'Consumed',
      badge: 'bg-navy-50 text-navy-600 border-navy-200',
      dot: 'bg-navy-400',
    },
  }

  return (
    <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
        <div>
          <h3 className="text-lg font-semibold text-navy-800">cNFT Custody Tracking</h3>
          <p className="text-sm text-navy-500 mt-0.5">
            Digital twin certificates for every medical lot
          </p>
        </div>
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold bg-teal-light text-teal-dark border border-teal-medical">
            <span className="w-2 h-2 rounded-full bg-teal-medical" />
            Ledger Secured
          </span>
        </div>
      </div>

      {/* Search */}
      <div className="mb-6">
        <input
          type="text"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          placeholder="Search by cNFT ID, commodity, or lot number..."
          className="w-full px-4 py-3 bg-clinical-100 border border-clinical-300 rounded-medical text-navy-800 placeholder:text-navy-400 focus:border-teal-medical focus:ring-2 focus:ring-teal-light transition-all duration-200 outline-none text-sm"
        />
      </div>

      {isLoading ? (
        <div className="text-center py-16 text-navy-400">
          <div className="w-8 h-8 mx-auto mb-3 border-2 border-navy-300 border-t-teal-medical rounded-full animate-spin" />
          <p className="text-sm">Loading digital twins...</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Asset List */}
          <div className="lg:col-span-1 space-y-2 max-h-[500px] overflow-y-auto scrollbar-thin pr-2">
            {filteredAssets.length === 0 ? (
              <div className="text-center py-12 text-navy-400">
                <p className="text-sm">No cNFT assets found</p>
              </div>
            ) : (
              filteredAssets.map((asset) => (
                <button
                  key={asset.id}
                  onClick={() => setSelectedAsset(asset)}
                  className={`w-full text-left p-4 rounded-medical border transition-all duration-200 ${
                    selectedAsset?.id === asset.id
                      ? 'border-teal-medical bg-teal-light/30 shadow-medical'
                      : 'border-clinical-200 bg-clinical-100 hover:bg-clinical-200'
                  }`}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-xs font-mono text-navy-500">{asset.cnfId}</span>
                    <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-pill text-xs font-semibold border ${statusConfig[asset.status].badge}`}>
                      <span className={`w-1.5 h-1.5 rounded-full ${statusConfig[asset.status].dot}`} />
                      {statusConfig[asset.status].label}
                    </span>
                  </div>
                  <p className="text-sm font-semibold text-navy-800">{asset.commodity}</p>
                  <p className="text-xs text-navy-400 mt-0.5">Lot: {asset.lotNumber}</p>
                </button>
              ))
            )}
          </div>

          {/* Detail Panel */}
          <div className="lg:col-span-2">
            {selectedAsset ? (
              <div className="space-y-6">
                {/* Certificate Header */}
                <div className="bg-gradient-to-r from-navy-800 to-navy-700 rounded-medical p-6 text-white">
                  <div className="flex items-center justify-between mb-4">
                    <div>
                      <p className="text-xs text-navy-300 uppercase tracking-wide">Digital Twin Certificate</p>
                      <h4 className="text-xl font-bold mt-1">{selectedAsset.commodity}</h4>
                    </div>
                    <div className="text-right">
                      <span className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-pill text-xs font-semibold border ${
                        selectedAsset.status === 'active' ? 'bg-emerald-500/20 text-emerald-300 border-emerald-400/30' :
                        selectedAsset.status === 'quarantined' ? 'bg-red-500/20 text-red-300 border-red-400/30' :
                        'bg-slate-500/20 text-slate-300 border-slate-400/30'
                      }`}>
                        <span className={`w-1.5 h-1.5 rounded-full ${
                          selectedAsset.status === 'active' ? 'bg-emerald-400' :
                          selectedAsset.status === 'quarantined' ? 'bg-red-400' : 'bg-slate-400'
                        }`} />
                        {statusConfig[selectedAsset.status].label}
                      </span>
                    </div>
                  </div>

                  <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                    <div>
                      <p className="text-navy-400 text-xs">cNFT ID</p>
                      <p className="font-mono font-medium">{selectedAsset.cnfId}</p>
                    </div>
                    <div>
                      <p className="text-navy-400 text-xs">Lot Number</p>
                      <p className="font-medium">{selectedAsset.lotNumber}</p>
                    </div>
                    <div>
                      <p className="text-navy-400 text-xs">Manufacturer</p>
                      <p className="font-medium">{selectedAsset.manufacturer}</p>
                    </div>
                    <div>
                      <p className="text-navy-400 text-xs">Expiry Date</p>
                      <p className="font-medium">{selectedAsset.expiryDate}</p>
                    </div>
                  </div>

                  <div className="mt-4 pt-4 border-t border-navy-600/50 grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <p className="text-navy-400 text-xs">Minted</p>
                      <p className="font-medium">{selectedAsset.mintedAt}</p>
                    </div>
                    <div>
                      <p className="text-navy-400 text-xs">Current Custodian</p>
                      <p className="font-medium">{selectedAsset.currentCustodian}</p>
                    </div>
                  </div>
                </div>

                {/* Custody Chain Timeline */}
                <div>
                  <h4 className="text-sm font-semibold text-navy-700 mb-4 flex items-center gap-2">
                    <span>🔗</span> Custody Chain
                    <span className="text-xs text-navy-400 font-normal">
                      ({selectedAsset.custodyChain.length} hand-offs)
                    </span>
                  </h4>

                  <div className="space-y-0">
                    {selectedAsset.custodyChain.map((event, idx) => (
                      <div key={idx} className="flex gap-4">
                        {/* Timeline line + dot */}
                        <div className="flex flex-col items-center">
                          <div className={`w-3 h-3 rounded-full border-2 shrink-0 mt-1 ${
                            event.verified
                              ? 'bg-emerald-100 border-emerald-500'
                              : 'bg-amber-100 border-amber-500'
                          }`} />
                          {idx < selectedAsset.custodyChain.length - 1 && (
                            <div className="w-0.5 h-full bg-clinical-300" />
                          )}
                        </div>

                        {/* Event content */}
                        <div className={`pb-6 flex-1 ${idx === selectedAsset.custodyChain.length - 1 ? 'pb-0' : ''}`}>
                          <div className="bg-clinical-100 border border-clinical-200 rounded-medical p-4">
                            <div className="flex items-center justify-between mb-2">
                              <div className="flex items-center gap-2">
                                {event.verified ? (
                                  <span className="text-emerald-500 text-xs" title="Verified on ledger">✓</span>
                                ) : (
                                  <span className="text-amber-500 text-xs" title="Pending verification">⏳</span>
                                )}
                                <span className="text-xs font-semibold text-navy-700">
                                  {event.from} → {event.to}
                                </span>
                              </div>
                              <span className="text-xs text-navy-400">{event.timestamp}</span>
                            </div>
                            <div className="flex items-center justify-between">
                              <span className="text-xs text-navy-500">{event.location}</span>
                              <span className="text-xs font-mono text-navy-400" title="Ledger transaction hash">
                                {event.transactionHash}
                              </span>
                            </div>
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* Ledger verification footer */}
                  <div className="mt-4 p-3 bg-navy-50 border border-navy-200 rounded-medical flex items-center justify-between">
                    <div className="flex items-center gap-2 text-xs text-navy-600">
                      <span>🔒</span>
                      <span>All hand-offs recorded on ZAMMSA Ledger — immutable</span>
                    </div>
                    <span className="text-xs font-mono text-navy-500">
                      Last block: {selectedAsset.custodyChain[selectedAsset.custodyChain.length - 1]?.transactionHash || 'N/A'}
                    </span>
                  </div>
                </div>
              </div>
            ) : (
              <div className="flex items-center justify-center h-full min-h-[400px] text-navy-400">
                <div className="text-center">
                  <svg className="w-16 h-16 mx-auto mb-4 text-navy-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M20 7l-8-4-8 4m16 0l-8 4m8-4v10l-8 4m0-10L4 7m8 4v10M4 7v10l8 4" />
                  </svg>
                  <p className="text-sm font-medium">Select a cNFT asset</p>
                  <p className="text-xs mt-1">View its digital twin certificate and custody chain</p>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  )
}
