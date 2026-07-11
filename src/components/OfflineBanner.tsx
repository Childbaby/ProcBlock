'use client'

import { useEffect, useState } from 'react'
import { getPendingTransfers } from '@/lib/indexeddb-cache'

export function OfflineBanner() {
  const [isOnline, setIsOnline] = useState(true)
  const [pendingCount, setPendingCount] = useState(0)

  useEffect(() => {
    setIsOnline(navigator.onLine)
    const handleOnline = () => setIsOnline(true)
    const handleOffline = () => setIsOnline(false)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  useEffect(() => {
    getPendingTransfers().then(t => setPendingCount(t.length))
    const interval = setInterval(() => {
      getPendingTransfers().then(t => setPendingCount(t.length))
    }, 5000)
    return () => clearInterval(interval)
  }, [])

  if (isOnline && pendingCount === 0) return null

  return (
    <div className={`px-4 py-2 text-center text-sm font-medium ${
      !isOnline ? 'bg-amber-50 text-amber-800 border-b border-amber-200' : 'bg-emerald-50 text-emerald-800 border-b border-emerald-200'
    }`}>
      {!isOnline ? (
        <>📡 You are offline. {pendingCount} transfer{pendingCount !== 1 ? 's' : ''} queued for sync.</>
      ) : (
        <>🔄 Syncing {pendingCount} pending transfer{pendingCount !== 1 ? 's' : ''} to Solana...</>
      )}
    </div>
  )
}
