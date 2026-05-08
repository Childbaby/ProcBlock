// Typed fetch helpers for the ProcBlock AI Insight Module

export interface Anomaly {
  id: string
  type: 'counterfeit' | 'expiry' | 'stockout' | 'temperature' | 'custody'
  severity: 'high' | 'medium' | 'low'
  message: string
  location: string
  timestamp: string
  status: 'active' | 'resolved' | 'investigating'
  score?: number
}

export interface HubNode {
  id: string
  name: string
  region: string
  status: 'online' | 'offline' | 'degraded'
  stockLevel: number
  transactionCount: number
  lastUpdate: string
}

export interface FlowData {
  hub: string
  totalShipments: number
  totalQuantity: number
  avgTransitHours: number
}

interface AnomalyResponse {
  anomalies: Anomaly[]
  total_records: number
  anomaly_count: number
}

interface GeospatialResponse {
  hubs: HubNode[]
  flows: FlowData[]
  total_hubs: number
}

export async function fetchAnomalies(): Promise<AnomalyResponse> {
  const res = await fetch('/api/anomalies', { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch anomalies')
  return res.json()
}

export async function fetchGeospatialData(): Promise<GeospatialResponse> {
  const res = await fetch('/api/geospatial', { cache: 'no-store' })
  if (!res.ok) throw new Error('Failed to fetch geospatial data')
  return res.json()
}
