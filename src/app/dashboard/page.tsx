'use client'

import { useEffect, useState } from 'react'
import { DashboardCard } from '@/components/DashboardCard'
import { GeospatialMapperPanel } from '@/components/GeospatialMapperPanel'
import { AnomalyDetectorPanel } from '@/components/AnomalyDetectorPanel'
import { ShipmentTrackerPanel } from '@/components/ShipmentTrackerPanel'
import { CNFTCustodyPanel } from '@/components/CNFTCustodyPanel'
import { ActivityFeed } from '@/components/ActivityFeed'
import { useBlockchainAuth } from '@/lib/use-blockchain-auth'
import { fetchAnomalies, fetchGeospatialData } from '@/lib/ai-client'
import type { Anomaly, HubNode } from '@/lib/ai-client'

export default function DashboardPage() {
  const { anonymousId } = useBlockchainAuth()
  const [hubs, setHubs] = useState<HubNode[]>([])
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [isLoading, setIsLoading] = useState(true)

  const [shipments] = useState([
    {
      id: 'ZAM-2847', commodity: 'Amoxicillin 250mg Capsules', from: 'Lusaka Central Hub',
      to: 'Kitwe District Hub', quantity: 5000, dispatchedAt: '2026-07-01 08:00',
      estimatedDelivery: '2026-07-01 16:00', deliveredAt: '2026-07-01 15:42',
      status: 'delivered' as const, custodian: 'Dr. Mwansa', ledgerEntry: '0x8f3a...7b2d',
      coldChain: { status: 'normal' as const, temperature: 4.2 }
    },
    {
      id: 'ZAM-2848', commodity: 'Insulin Pens (Cold Chain)', from: 'Lusaka Central Hub',
      to: 'Chipata Hub', quantity: 1200, dispatchedAt: '2026-07-01 09:30',
      estimatedDelivery: '2026-07-01 18:00', status: 'in_transit' as const,
      coldChain: { status: 'warning' as const, temperature: 8.5, maxTemp: 12.0 }
    },
    {
      id: 'ZAM-2849', commodity: 'Surgical Gloves', from: 'Kitwe District Hub',
      to: 'Solwezi Hub', quantity: 8000, dispatchedAt: '2026-07-01 10:00',
      estimatedDelivery: '2026-07-01 14:00', status: 'delayed' as const,
    },
    {
      id: 'ZAM-2850', commodity: 'Vaccine Vials (Cold Chain)', from: 'Lusaka Central Hub',
      to: 'Livingstone Hub', quantity: 3000, dispatchedAt: '2026-07-01 11:00',
      estimatedDelivery: '2026-07-02 09:00', status: 'pending' as const,
      coldChain: { status: 'normal' as const, temperature: 2.0 }
    },
    {
      id: 'ZAM-2851', commodity: 'Vaccine Vials (Cold Chain)', from: 'Chipata Hub',
      to: 'Lundazi Clinic', quantity: 500, dispatchedAt: '2026-07-01 07:00',
      estimatedDelivery: '2026-07-01 12:00', deliveredAt: '2026-07-01 11:30',
      status: 'delivered' as const, custodian: 'Nurse Banda', ledgerEntry: '0xa4b2...9c1e',
      coldChain: { status: 'compromised' as const, temperature: 18.5, maxTemp: 25.0 }
    },
    {
      id: 'ZAM-2852', commodity: 'Amoxicillin 250mg Capsules', from: 'Lusaka Central Hub',
      to: 'Mansa Hub', quantity: 2500, dispatchedAt: '2026-07-01 06:00',
      estimatedDelivery: '2026-07-01 20:00', status: 'in_transit' as const,
    },
    {
      id: 'ZAM-2853', commodity: 'Malaria Rapid Test Kits', from: 'Livingstone Hub',
      to: 'Mongu Hub', quantity: 10000, dispatchedAt: '2026-07-01 08:30',
      estimatedDelivery: '2026-07-02 10:00', status: 'pending' as const,
    },
  ])

  const activities = [
    { id: 'act-1', type: 'minted' as const, description: 'New cNFT minted for Amoxicillin 250mg — Lot: LOT-AMX-2024-0847', actor: anonymousId || '8xK9...3mW2', timestamp: '2026-07-01 08:00', transactionHash: '5xHn9kLm3pQr7sT2vW4xY6zA8bC0dE1f' },
    { id: 'act-2', type: 'transferred' as const, description: 'Custody transferred: Lusaka Central Hub → Kitwe District Hub', actor: '4mN7...9pL3', timestamp: '2026-07-01 12:30', transactionHash: '3xJ8iK2lM4nO6pQ8rS0tU2vW4xY6zA8b' },
    { id: 'act-3', type: 'alerted' as const, description: '🚨 Cold chain broken: Vaccine Vials at Lundazi Clinic — temp reached 25°C', actor: 'AI-Monitor', timestamp: '2026-07-01 11:45' },
    { id: 'act-4', type: 'verified' as const, description: 'Public verification: cNFT-ZAM-AMX-0847 confirmed authentic', actor: '2kL5...7nM1', timestamp: '2026-07-01 14:15', transactionHash: '7xP2qR4sT6uV8wX0yZ2aB4cD6eF8gH0i' },
    { id: 'act-5', type: 'alerted' as const, description: '⚠️ Temperature deviation: Insulin Pens at Chipata Hub — 8.5°C (max: 12°C)', actor: 'AI-Monitor', timestamp: '2026-07-01 15:00' },
  ]

  useEffect(() => {
    async function loadData() {
      try {
        const [anomalyData, geospatialData] = await Promise.all([fetchAnomalies(), fetchGeospatialData()])
        setAnomalies(anomalyData.anomalies)
        setHubs(geospatialData.hubs)
      } catch (err) { console.error('Failed to load AI data:', err) }
      finally { setIsLoading(false) }
    }
    loadData()
  }, [])

  return (
    <div className="space-y-8 px-4 pb-12">
      <div>
        <h1 className="text-display-md text-navy-800">Dashboard Overview</h1>
        <p className="text-sm text-navy-500 mt-1">
          Real-time monitoring · Offline-ready · Cold chain aware · <span className="font-mono text-teal-medical">{anonymousId || 'Not connected'}</span>
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <DashboardCard title="Pending" value="2" status="warning" subtitle="Awaiting dispatch" />
        <DashboardCard title="In Transit" value="2" status="info" subtitle="En route" />
        <DashboardCard title="Delivered" value="2" status="verified" subtitle="On-chain confirmed" />
        <DashboardCard title="Cold Chain Alerts" value="2" status="critical" subtitle="1 broken · 1 warning" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        <GeospatialMapperPanel hubs={hubs} isLoading={isLoading} />
        <AnomalyDetectorPanel anomalies={anomalies} isLoading={isLoading} />
      </div>

      <ShipmentTrackerPanel shipments={shipments} isLoading={false} />
      <ActivityFeed activities={activities} />
    </div>
  )
}
