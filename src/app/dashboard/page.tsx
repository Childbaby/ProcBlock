'use client'

import { useEffect, useState } from 'react'
import { DashboardCard } from '@/components/DashboardCard'
import { GeospatialMapperPanel } from '@/components/GeospatialMapperPanel'
import { AnomalyDetectorPanel } from '@/components/AnomalyDetectorPanel'
import { ShipmentTrackerPanel } from '@/components/ShipmentTrackerPanel'
import { CNFTCustodyPanel } from '@/components/CNFTCustodyPanel'
import { fetchAnomalies, fetchGeospatialData, type Anomaly, type HubNode } from '@/lib/ai-client'

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

export default function DashboardPage() {
  const [hubs, setHubs] = useState<HubNode[]>([])
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const [shipments] = useState<Shipment[]>([
    {
      id: 'ZAM-2847', commodity: 'Amoxicillin 250mg Capsules', from: 'Lusaka Central Hub',
      to: 'Kitwe District Hub', quantity: 5000, dispatchedAt: '2026-05-07 08:00',
      estimatedDelivery: '2026-05-07 16:00', deliveredAt: '2026-05-07 15:42',
      status: 'delivered', custodian: 'Dr. Mwansa', ledgerEntry: '0x8f3a...7b2d',
    },
    {
      id: 'ZAM-2848', commodity: 'Insulin Pens (Cold Chain)', from: 'Lusaka Central Hub',
      to: 'Chipata Hub', quantity: 1200, dispatchedAt: '2026-05-07 09:30',
      estimatedDelivery: '2026-05-07 18:00', status: 'in_transit',
    },
    {
      id: 'ZAM-2849', commodity: 'Surgical Gloves', from: 'Kitwe District Hub',
      to: 'Solwezi Hub', quantity: 8000, dispatchedAt: '2026-05-07 10:00',
      estimatedDelivery: '2026-05-07 14:00', status: 'delayed',
    },
    {
      id: 'ZAM-2850', commodity: 'PPE Kits', from: 'Lusaka Central Hub',
      to: 'Livingstone Hub', quantity: 3000, dispatchedAt: '2026-05-07 11:00',
      estimatedDelivery: '2026-05-08 09:00', status: 'pending',
    },
    {
      id: 'ZAM-2851', commodity: 'Vaccine Vials (Cold Chain)', from: 'Chipata Hub',
      to: 'Lundazi Clinic', quantity: 500, dispatchedAt: '2026-05-07 07:00',
      estimatedDelivery: '2026-05-07 12:00', deliveredAt: '2026-05-07 11:30',
      status: 'delivered', custodian: 'Nurse Banda', ledgerEntry: '0xa4b2...9c1e',
    },
    {
      id: 'ZAM-2852', commodity: 'Amoxicillin 250mg Capsules', from: 'Lusaka Central Hub',
      to: 'Mansa Hub', quantity: 2500, dispatchedAt: '2026-05-07 06:00',
      estimatedDelivery: '2026-05-07 20:00', status: 'in_transit',
    },
    {
      id: 'ZAM-2853', commodity: 'Malaria Rapid Test Kits', from: 'Livingstone Hub',
      to: 'Mongu Hub', quantity: 10000, dispatchedAt: '2026-05-07 08:30',
      estimatedDelivery: '2026-05-08 10:00', status: 'pending',
    },
  ])

  // Mock cNFT assets
  const [cnftAssets] = useState<CNFTAsset[]>([
    {
      id: 'cnft-1',
      cnfId: 'cNFT-ZAM-AMX-0847',
      commodity: 'Amoxicillin 250mg Capsules',
      lotNumber: 'LOT-AMX-2024-0847',
      manufacturer: 'Zambia Pharma Ltd.',
      expiryDate: '2026-03-15',
      mintedAt: '2026-05-07 08:00',
      currentCustodian: 'Kitwe District Hub',
      currentLocation: 'Kitwe, Copperbelt Province',
      status: 'active',
      custodyChain: [
        {
          timestamp: '2026-05-07 08:00',
          from: 'Manufacturer',
          to: 'Lusaka Central Hub',
          location: 'Lusaka',
          transactionHash: '0x7a1b...3c4d',
          verified: true,
        },
        {
          timestamp: '2026-05-07 12:30',
          from: 'Lusaka Central Hub',
          to: 'Kitwe District Hub',
          location: 'Kitwe, Copperbelt',
          transactionHash: '0x8f3a...7b2d',
          verified: true,
        },
      ],
    },
    {
      id: 'cnft-2',
      cnfId: 'cNFT-ZAM-INS-0192',
      commodity: 'Insulin Pens (Cold Chain)',
      lotNumber: 'LOT-INS-2024-0192',
      manufacturer: 'Novo Nordisk SA',
      expiryDate: '2025-11-20',
      mintedAt: '2026-05-07 09:00',
      currentCustodian: 'Chipata Hub',
      currentLocation: 'Chipata, Eastern Province',
      status: 'active',
      custodyChain: [
        {
          timestamp: '2026-05-07 09:00',
          from: 'Manufacturer',
          to: 'Lusaka Central Hub',
          location: 'Lusaka',
          transactionHash: '0x2e5f...8a1c',
          verified: true,
        },
        {
          timestamp: '2026-05-07 13:00',
          from: 'Lusaka Central Hub',
          to: 'Chipata Hub',
          location: 'Chipata, Eastern',
          transactionHash: '0x9b4d...2f6e',
          verified: false,
        },
      ],
    },
    {
      id: 'cnft-3',
      cnfId: 'cNFT-ZAM-VAX-0045',
      commodity: 'Vaccine Vials (Cold Chain)',
      lotNumber: 'LOT-VAX-2024-0045',
      manufacturer: 'BioNTech Manufacturing GmbH',
      expiryDate: '2025-08-10',
      mintedAt: '2026-05-07 07:00',
      currentCustodian: 'Lundazi Clinic',
      currentLocation: 'Lundazi, Eastern Province',
      status: 'consumed',
      custodyChain: [
        {
          timestamp: '2026-05-07 07:00',
          from: 'Manufacturer',
          to: 'Lusaka Central Hub',
          location: 'Lusaka',
          transactionHash: '0x3d7a...1b9f',
          verified: true,
        },
        {
          timestamp: '2026-05-07 09:00',
          from: 'Lusaka Central Hub',
          to: 'Chipata Hub',
          location: 'Chipata, Eastern',
          transactionHash: '0x5c8e...4a2d',
          verified: true,
        },
        {
          timestamp: '2026-05-07 11:30',
          from: 'Chipata Hub',
          to: 'Lundazi Clinic',
          location: 'Lundazi, Eastern',
          transactionHash: '0xa4b2...9c1e',
          verified: true,
        },
      ],
    },
    {
      id: 'cnft-4',
      cnfId: 'cNFT-ZAM-PPE-0621',
      commodity: 'PPE Kits',
      lotNumber: 'LOT-PPE-2024-0621',
      manufacturer: 'MediSupply Zambia',
      expiryDate: '2027-01-30',
      mintedAt: '2026-05-07 10:00',
      currentCustodian: 'Lusaka Central Hub',
      currentLocation: 'Lusaka',
      status: 'quarantined',
      custodyChain: [
        {
          timestamp: '2026-05-07 10:00',
          from: 'Manufacturer',
          to: 'Lusaka Central Hub',
          location: 'Lusaka',
          transactionHash: '0x6f1c...0d3a',
          verified: true,
        },
      ],
    },
  ])

  useEffect(() => {
    async function loadData() {
      try {
        const [anomalyData, geospatialData] = await Promise.all([
          fetchAnomalies(),
          fetchGeospatialData(),
        ])
        setAnomalies(anomalyData.anomalies)
        setHubs(geospatialData.hubs)
      } catch (err) {
        console.error('Failed to load AI data:', err)
        setError('AI Insight Module is currently unavailable. Displaying fallback data.')
      } finally {
        setIsLoading(false)
      }
    }
    loadData()
  }, [])

  const pendingCount = shipments.filter(s => s.status === 'pending').length
  const inTransitCount = shipments.filter(s => s.status === 'in_transit').length
  const deliveredCount = shipments.filter(s => s.status === 'delivered').length
  const delayedCount = shipments.filter(s => s.status === 'delayed').length

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-display-md text-navy-800">Dashboard Overview</h1>
        <p className="text-sm text-navy-500 mt-1">
          Real-time medical supply chain monitoring · AI-Powered Analytics
        </p>
      </div>

      {error && (
        <div className="p-4 bg-amber-50 border border-amber-200 rounded-medical text-sm text-amber-700">
          {error}
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <DashboardCard title="Pending Shipments" value={pendingCount} status="warning" subtitle="Awaiting dispatch" />
        <DashboardCard title="In Transit" value={inTransitCount} status="info" subtitle="En route to facilities" />
        <DashboardCard title="Delivered Today" value={deliveredCount} status="verified" subtitle="Confirmed on ledger" />
        <DashboardCard title="Delayed" value={delayedCount} status={delayedCount > 0 ? 'critical' : 'verified'} subtitle={delayedCount > 0 ? 'Requires attention' : 'No delays'} />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <GeospatialMapperPanel hubs={hubs} isLoading={isLoading} />
        <AnomalyDetectorPanel anomalies={anomalies} isLoading={isLoading} onResolve={(id) => console.log('Resolve:', id)} onInvestigate={(id) => console.log('Investigate:', id)} />
      </div>

      <ShipmentTrackerPanel shipments={shipments} isLoading={false} />

      <CNFTCustodyPanel assets={cnftAssets} isLoading={false} />
    </div>
  )
}
