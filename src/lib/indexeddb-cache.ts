const DB_NAME = 'procblock-cache'
const DB_VERSION = 1

function openDB(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains('transfers')) {
        const store = db.createObjectStore('transfers', { keyPath: 'id' })
        store.createIndex('synced', 'synced', { unique: false })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function saveTransferOffline(payload: {
  cnfId: string
  fromCustodian: string
  toCustodian: string
  location: string
  commodity: string
  lotNumber: string
  timestamp: string
}): Promise<string> {
  const db = await openDB()
  const record = {
    id: `cache-${Date.now()}-${Math.random().toString(36).substring(2, 6)}`,
    type: 'custody_transfer' as const,
    payload,
    synced: false,
    createdAt: new Date().toISOString(),
  }
  return new Promise((resolve, reject) => {
    const tx = db.transaction('transfers', 'readwrite')
    const store = tx.objectStore('transfers')
    const request = store.add(record)
    request.onsuccess = () => resolve(record.id)
    request.onerror = () => reject(request.error)
  })
}

export interface CachedTransfer {
  id: string
  type: 'custody_transfer'
  payload: {
    cnfId: string
    fromCustodian: string
    toCustodian: string
    location: string
    commodity: string
    lotNumber: string
    timestamp: string
  }
  synced: boolean
  createdAt: string
}

export async function getPendingTransfers(): Promise<CachedTransfer[]> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('transfers', 'readonly')
    const store = tx.objectStore('transfers')
    const index = store.index('synced')
    const request = index.getAll(false)
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

export async function markTransferSynced(id: string): Promise<void> {
  const db = await openDB()
  return new Promise((resolve, reject) => {
    const tx = db.transaction('transfers', 'readwrite')
    const store = tx.objectStore('transfers')
    const getRequest = store.get(id)
    getRequest.onsuccess = () => {
      const record = getRequest.result
      if (record) {
        record.synced = true
        store.put(record)
        resolve()
      }
    }
    getRequest.onerror = () => reject(getRequest.error)
  })
}

export async function getCachedTransferCount(): Promise<number> {
  const pending = await getPendingTransfers()
  return pending.length
}
