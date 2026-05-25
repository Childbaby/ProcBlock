'use client'

import { useState } from 'react'

interface Shipment {
  id: string
  commodity: string
  from: string
  to: string
  quantity: number
  dispatchedAt: string
  estimatedDelivery: string
  deliveredAt?: string
  status: 'pending' | 'in_transit' | 'delivered' | 'delayed'
  custodian?: string
  ledgerEntry?: string
}

interface ShipmentTrackerPanelProps {
  shipments: Shipment[]
  isLoading?: boolean
}

export function ShipmentTrackerPanel({ shipments, isLoading = false }: ShipmentTrackerPanelProps) {
  const [filter, setFilter] = useState<'all' | 'pending' | 'in_transit' | 'delivered' | 'delayed'>('all')

  const statusConfig = {
    pending: {
      label: 'Pending',
      badge: 'bg-amber-50 text-amber-700 border-amber-200',
      dot: 'bg-amber-500',
      icon: '⏳',
    },
    in_transit: {
      label: 'In Transit',
      badge: 'bg-sky-50 text-sky-700 border-sky-200',
      dot: 'bg-sky-500 animate-pulse',
      icon: '🚚',
    },
    delivered: {
      label: 'Delivered',
      badge: 'bg-emerald-50 text-emerald-700 border-emerald-200',
      dot: 'bg-emerald-500',
      icon: '✅',
    },
    delayed: {
      label: 'Delayed',
      badge: 'bg-red-50 text-red-700 border-red-200',
      dot: 'bg-red-500',
      icon: '⚠️',
    },
  }

  const filteredShipments = filter === 'all'
    ? shipments
    : shipments.filter(s => s.status === filter)

  const counts = {
    all: shipments.length,
    pending: shipments.filter(s => s.status === 'pending').length,
    in_transit: shipments.filter(s => s.status === 'in_transit').length,
    delivered: shipments.filter(s => s.status === 'delivered').length,
    delayed: shipments.filter(s => s.status === 'delayed').length,
  }

  const filterTabs: Array<{ key: typeof filter; label: string }> = [
    { key: 'all', label: `All (${counts.all})` },
    { key: 'pending', label: `Pending (${counts.pending})` },
    { key: 'in_transit', label: `In Transit (${counts.in_transit})` },
    { key: 'delivered', label: `Delivered (${counts.delivered})` },
    { key: 'delayed', label: `Delayed (${counts.delayed})` },
  ]

  return (
    <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
      <div className="flex items-center justify-between mb-6">
        <div>
          <h3 className="text-lg font-semibold text-navy-800">Shipment Tracker</h3>
          <p className="text-sm text-navy-500 mt-0.5">
            Real-time delivery monitoring across all hubs
          </p>
        </div>
      </div>

      {/* Filter Tabs */}
      <div className="flex gap-2 mb-6 overflow-x-auto pb-2 scrollbar-thin">
        {filterTabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setFilter(tab.key)}
            className={`px-4 py-2 rounded-pill text-xs font-semibold whitespace-nowrap transition-all duration-200 ${
              filter === tab.key
                ? 'bg-navy-800 text-white shadow-medical'
                : 'bg-clinical-100 text-navy-500 hover:bg-clinical-200 border border-clinical-200'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Shipment List */}
      {isLoading ? (
        <div className="text-center py-16 text-navy-400">
          <div className="w-8 h-8 mx-auto mb-3 border-2 border-navy-300 border-t-teal-medical rounded-full animate-spin" />
          <p className="text-sm">Loading shipments...</p>
        </div>
      ) : filteredShipments.length === 0 ? (
        <div className="text-center py-12 text-navy-400">
          <p className="text-sm font-medium">No shipments found</p>
          <p className="text-xs mt-1">No shipments match the selected filter</p>
        </div>
      ) : (
        <div className="space-y-3 max-h-[500px] overflow-y-auto scrollbar-thin">
          {filteredShipments.map((shipment) => {
            const config = statusConfig[shipment.status]
            return (
              <div
                key={shipment.id}
                className="p-4 rounded-medical border border-clinical-200 bg-clinical-100 hover:bg-clinical-200 transition-colors duration-150"
              >
                {/* Header Row */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{config.icon}</span>
                    <div>
                      <p className="text-sm font-semibold text-navy-800 font-mono">{shipment.id}</p>
                      <p className="text-xs text-navy-500">{shipment.commodity}</p>
                    </div>
                  </div>
                  <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-pill text-xs font-semibold border ${config.badge}`}>
                    <span className={`w-2 h-2 rounded-full ${config.dot}`} />
                    {config.label}
                  </span>
                </div>

                {/* Details Grid */}
                <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-xs">
                  <div>
                    <p className="text-navy-400 mb-0.5">From</p>
                    <p className="font-medium text-navy-700">{shipment.from}</p>
                  </div>
                  <div>
                    <p className="text-navy-400 mb-0.5">To</p>
                    <p className="font-medium text-navy-700">{shipment.to}</p>
                  </div>
                  <div>
                    <p className="text-navy-400 mb-0.5">Quantity</p>
                    <p className="font-medium text-navy-700">{shipment.quantity.toLocaleString()} units</p>
                  </div>
                  <div>
                    <p className="text-navy-400 mb-0.5">ETA</p>
                    <p className={`font-medium ${shipment.status === 'delayed' ? 'text-red-600' : 'text-navy-700'}`}>
                      {shipment.status === 'delivered'
                        ? shipment.deliveredAt
                        : shipment.estimatedDelivery}
                    </p>
                  </div>
                </div>

                {/* Progress Bar */}
                {shipment.status !== 'delivered' && (
                  <div className="mt-3">
                    <div className="flex justify-between text-xs text-navy-400 mb-1">
                      <span>Dispatched: {shipment.dispatchedAt}</span>
                      <span>
                        {shipment.status === 'pending' ? 'Awaiting pickup' :
                         shipment.status === 'in_transit' ? 'In transit' :
                         'Delayed'}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-clinical-200 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          shipment.status === 'pending' ? 'bg-amber-400 w-1/4' :
                          shipment.status === 'in_transit' ? 'bg-sky-400 w-3/4' :
                          'bg-red-400 w-1/2'
                        }`}
                      />
                    </div>
                  </div>
                )}

                {/* Delivered Confirmation */}
                {shipment.status === 'delivered' && (
                  <div className="mt-3 flex items-center justify-between bg-emerald-50 rounded-medical p-3">
                    <div className="flex items-center gap-2 text-xs text-emerald-700">
                      <span>✓</span>
                      <span>Confirmed by: <span className="font-medium">{shipment.custodian}</span></span>
                    </div>
                    {shipment.ledgerEntry && (
                      <span className="text-xs font-mono text-emerald-600">{shipment.ledgerEntry}</span>
                    )}
                  </div>
                )}
              </div>
            )
          })}
        </div>
      )}

      {/* Summary Footer */}
      <div className="mt-6 pt-4 border-t border-clinical-200 grid grid-cols-4 gap-4 text-center">
        <div>
          <p className="text-lg font-bold text-navy-800">{counts.pending}</p>
          <p className="text-xs text-navy-400">Pending</p>
        </div>
        <div>
          <p className="text-lg font-bold text-sky-600">{counts.in_transit}</p>
          <p className="text-xs text-navy-400">In Transit</p>
        </div>
        <div>
          <p className="text-lg font-bold text-emerald-600">{counts.delivered}</p>
          <p className="text-xs text-navy-400">Delivered</p>
        </div>
        <div>
          <p className="text-lg font-bold text-red-600">{counts.delayed}</p>
          <p className="text-xs text-navy-400">Delayed</p>
        </div>
      </div>
    </div>
  )
}
