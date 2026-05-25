'use client'

import { useState, useEffect, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { parseGS1DataMatrix, generateTestGS1Code, type GS1Data } from '@/lib/gs1-parser'
import { saveTransferOffline, getCachedTransferCount } from '@/lib/indexeddb-cache'

const Html5QrcodePlugin = dynamic(
  () => import('./Html5QrcodePlugin').then((mod) => mod.Html5QrcodePlugin),
  { ssr: false }
)

interface TransferRecord {
  id: string
  gs1Data: GS1Data
  commodity: string
  fromCustodian: string
  toCustodian: string
  location: string
  timestamp: string
  synced: boolean
}

export default function ScannerPage() {
  const [scanResult, setScanResult] = useState<GS1Data | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [manualCode, setManualCode] = useState('')
  const [transferStatus, setTransferStatus] = useState<'idle' | 'processing' | 'success' | 'error'>('idle')
  const [toCustodian, setToCustodian] = useState('')
  const [currentLocation, setCurrentLocation] = useState('')
  const [recentTransfers, setRecentTransfers] = useState<TransferRecord[]>([])
  const [pendingCount, setPendingCount] = useState(0)
  const [mode, setMode] = useState<'camera' | 'file' | 'manual'>('manual')

  useEffect(() => {
    getCachedTransferCount().then(setPendingCount)
  }, [transferStatus])

  const handleScanSuccess = useCallback((decodedText: string) => {
    const parsed = parseGS1DataMatrix(decodedText)
    if (parsed) {
      setScanResult(parsed)
      setIsScanning(false)
      setTransferStatus('idle')
    }
  }, [])

  const handleScanError = useCallback((_error: string) => {
    // Called on every frame where no code is detected — not a real error.
  }, [])

  const handleFileUpload = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    try {
      const { Html5Qrcode } = await import('html5-qrcode')
      const scanner = new Html5Qrcode('file-scan-target')
      const decodedText = await scanner.scanFile(file, true)
      const parsed = parseGS1DataMatrix(decodedText)
      if (parsed) {
        setScanResult(parsed)
        setTransferStatus('idle')
      }
    } catch (err) {
      console.error('File scan error:', err)
    }
  }, [])

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!manualCode.trim()) return

    const parsed = parseGS1DataMatrix(manualCode.trim())
    if (parsed) {
      setScanResult(parsed)
      setManualCode('')
      setTransferStatus('idle')
    }
  }

  const handleAcceptTransfer = async () => {
    if (!scanResult) return

    setTransferStatus('processing')

    try {
      const recordId = await saveTransferOffline({
        cnfId: `cNFT-ZAM-${scanResult.serialNumber || Date.now()}`,
        fromCustodian: 'Lusaka Central Hub',
        toCustodian: toCustodian || 'Field Worker',
        location: currentLocation || 'Unknown Location',
        commodity: `GTIN: ${scanResult.gtin || 'N/A'}`,
        lotNumber: scanResult.lotNumber || 'N/A',
        timestamp: new Date().toISOString(),
      })

      const newTransfer: TransferRecord = {
        id: recordId,
        gs1Data: scanResult,
        commodity: `GTIN: ${scanResult.gtin || 'N/A'}`,
        fromCustodian: 'Lusaka Central Hub',
        toCustodian: toCustodian || 'Field Worker',
        location: currentLocation || 'Unknown Location',
        timestamp: new Date().toLocaleString(),
        synced: false,
      }

      setRecentTransfers((prev) => [newTransfer, ...prev].slice(0, 10))
      setTransferStatus('success')
      setScanResult(null)
      setToCustodian('')
      setCurrentLocation('')
      setPendingCount((prev) => prev + 1)

      setTimeout(() => setTransferStatus('idle'), 3000)
    } catch (error) {
      console.error('Transfer error:', error)
      setTransferStatus('error')
      setTimeout(() => setTransferStatus('idle'), 3000)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 px-4 pb-12">
      {/* Header */}
      <div>
        <h1 className="text-display-md text-navy-800">Field Scanner</h1>
        <p className="text-sm text-navy-500 mt-1">
          Scan GS1 DataMatrix barcodes to process custody transfers
        </p>
        {pendingCount > 0 && (
          <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 rounded-pill bg-amber-50 border border-amber-200 text-xs font-medium text-amber-700">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            {pendingCount} transfer{pendingCount > 1 ? 's' : ''} pending sync
          </div>
        )}
      </div>

      {/* Scan Mode Selector */}
      <div className="flex gap-2 overflow-x-auto pb-1">
        {([
          { key: 'manual', label: '📝 Manual Entry', icon: '⌨️' },
          { key: 'camera', label: '📷 Camera Scan', icon: '📸' },
          { key: 'file', label: '🖼️ Upload Image', icon: '📤' },
        ] as const).map((opt) => (
          <button
            key={opt.key}
            onClick={() => { setMode(opt.key); setIsScanning(false); setScanResult(null) }}
            className={`px-4 py-2 rounded-pill text-xs font-semibold whitespace-nowrap transition-all duration-200 ${
              mode === opt.key
                ? 'bg-navy-800 text-white shadow-medical'
                : 'bg-clinical-100 text-navy-500 hover:bg-clinical-200 border border-clinical-200'
            }`}
          >
            {opt.label}
          </button>
        ))}
      </div>

      {/* Input Area */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Left: Scanner / Input */}
        <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
          {/* Manual Entry */}
          {mode === 'manual' && (
            <form onSubmit={handleManualSubmit} className="space-y-4">
              <h3 className="text-lg font-semibold text-navy-800">Manual Code Entry</h3>
              <div>
                <label htmlFor="manual-code" className="block text-sm font-medium text-navy-700 mb-1.5">
                  Enter GS1 DataMatrix Code
                </label>
                <textarea
                  id="manual-code"
                  value={manualCode}
                  onChange={(e) => setManualCode(e.target.value)}
                  className="w-full px-4 py-3 bg-clinical-100 border border-clinical-300 rounded-medical text-navy-800 placeholder:text-navy-400 focus:border-teal-medical focus:ring-2 focus:ring-teal-light transition-all duration-200 outline-none font-mono text-sm resize-none h-24"
                  placeholder="Paste GS1 code here...&#10;e.g. 010761234567890110LOT-AMX-08471726031521ZAM-2847-AMX-0847375000"
                />
              </div>
              <button type="submit" className="btn-primary w-full" disabled={!manualCode.trim()}>
                Parse Code
              </button>
              <button
                type="button"
                onClick={() => { const code = generateTestGS1Code(); setManualCode(code); handleManualSubmit({ preventDefault: () => {} } as any) }}
                className="btn-secondary w-full text-sm"
              >
                🧪 Load Test Code
              </button>
            </form>
          )}

          {/* Camera Scan */}
          {mode === 'camera' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-navy-800">Camera Scanner</h3>
              {isScanning ? (
                <>
                  <div className="relative border-2 border-teal-medical rounded-medical overflow-hidden bg-black">
                    <Html5QrcodePlugin
                      fps={10}
                      qrbox={{ width: 250, height: 250 }}
                      disableFlip={false}
                      qrCodeSuccessCallback={handleScanSuccess}
                      qrCodeErrorCallback={handleScanError}
                    />
                    <div className="absolute top-0 left-0 w-full h-0.5 bg-gradient-to-r from-transparent via-teal-medical to-transparent animate-scan-line" />
                  </div>
                  <button onClick={() => setIsScanning(false)} className="btn-secondary w-full">
                    Stop Scanner
                  </button>
                </>
              ) : (
                <div className="text-center py-16">
                  <div className="w-20 h-20 mx-auto mb-4 bg-teal-light rounded-full flex items-center justify-center">
                    <svg className="w-10 h-10 text-teal-medical" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                    </svg>
                  </div>
                  <p className="text-sm text-navy-500 mb-1">Position DataMatrix within frame</p>
                  <p className="text-xs text-navy-400 mb-4">Supports GS1 QR and DataMatrix codes</p>
                  <button onClick={() => setIsScanning(true)} className="btn-primary">
                    Start Camera
                  </button>
                </div>
              )}
            </div>
          )}

          {/* File Upload */}
          {mode === 'file' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-navy-800">Upload Barcode Image</h3>
              <div className="border-2 border-dashed border-clinical-300 rounded-medical p-8 text-center hover:border-teal-medical transition-colors duration-200">
                <input
                  type="file"
                  accept="image/*"
                  onChange={handleFileUpload}
                  className="hidden"
                  id="file-upload"
                />
                <label htmlFor="file-upload" className="cursor-pointer">
                  <svg className="w-12 h-12 mx-auto mb-3 text-navy-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                  </svg>
                  <p className="text-sm font-medium text-navy-600">Click to upload barcode image</p>
                  <p className="text-xs text-navy-400 mt-1">PNG, JPG or GIF</p>
                </label>
              </div>
              <div id="file-scan-target" className="hidden" />
            </div>
          )}
        </div>

        {/* Right: Scan Result + Transfer Form */}
        <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
          {scanResult ? (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-navy-800 flex items-center gap-2">
                <span className="text-emerald-500">✓</span> Code Parsed
              </h3>

              {/* GS1 Data Display */}
              <div className="bg-clinical-100 rounded-medical p-4 space-y-2">
                {[
                  { label: 'GTIN', value: scanResult.gtin || 'N/A', mono: true },
                  { label: 'Lot Number', value: scanResult.lotNumber || 'N/A', mono: false },
                  { label: 'Expiry Date', value: scanResult.expiryDate || 'N/A', mono: false },
                  { label: 'Serial Number', value: scanResult.serialNumber || 'N/A', mono: true },
                  { label: 'Quantity', value: scanResult.quantity?.toString() || 'N/A', mono: false },
                ].map((field) => (
                  <div key={field.label} className="flex justify-between">
                    <span className="text-xs text-navy-400">{field.label}</span>
                    <span className={`text-sm font-medium text-navy-800 ${field.mono ? 'font-mono' : ''}`}>
                      {field.value}
                    </span>
                  </div>
                ))}
              </div>

              {/* Custody Transfer Form */}
              <div className="space-y-3 pt-2">
                <h4 className="text-sm font-semibold text-navy-700">Accept Custody Transfer</h4>
                <input
                  type="text"
                  value={toCustodian}
                  onChange={(e) => setToCustodian(e.target.value)}
                  placeholder="Your name / Custodian ID"
                  className="w-full px-4 py-2.5 bg-clinical-100 border border-clinical-300 rounded-medical text-sm text-navy-800 placeholder:text-navy-400 focus:border-teal-medical focus:ring-2 focus:ring-teal-light outline-none"
                />
                <input
                  type="text"
                  value={currentLocation}
                  onChange={(e) => setCurrentLocation(e.target.value)}
                  placeholder="Current location (facility name)"
                  className="w-full px-4 py-2.5 bg-clinical-100 border border-clinical-300 rounded-medical text-sm text-navy-800 placeholder:text-navy-400 focus:border-teal-medical focus:ring-2 focus:ring-teal-light outline-none"
                />
              </div>

              {/* Action Buttons */}
              <div className="flex gap-3 pt-2">
                <button
                  onClick={handleAcceptTransfer}
                  disabled={transferStatus === 'processing'}
                  className="btn-primary flex-1 flex items-center justify-center gap-2 disabled:opacity-60"
                >
                  {transferStatus === 'processing' ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      Processing...
                    </>
                  ) : transferStatus === 'success' ? (
                    '✓ Transfer Saved'
                  ) : (
                    'Accept Transfer'
                  )}
                </button>
                <button onClick={() => { setScanResult(null); setTransferStatus('idle') }} className="btn-secondary">
                  Clear
                </button>
              </div>

              {transferStatus === 'success' && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-medical text-sm text-emerald-700 text-center">
                  Transfer saved locally. Will sync when online.
                </div>
              )}

              {transferStatus === 'error' && (
                <div className="p-3 bg-red-50 border border-red-200 rounded-medical text-sm text-red-700 text-center">
                  Transfer failed. Please try again.
                </div>
              )}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full min-h-[300px] text-navy-400">
              <div className="text-center">
                <svg className="w-16 h-16 mx-auto mb-4 text-navy-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M12 4v1m6 11h2m-6 0h-2m4 0v-6a3 3 0 00-3-3h-2a3 3 0 00-3 3v6m10 0H6" />
                </svg>
                <p className="text-sm font-medium">Scan or enter a GS1 code</p>
                <p className="text-xs mt-1">Parsed data will appear here</p>
              </div>
            </div>
          )}
        </div>
      </div>

      {/* Recent Transfers */}
      {recentTransfers.length > 0 && (
        <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
          <h3 className="text-lg font-semibold text-navy-800 mb-4">Recent Transfers</h3>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-navy-500 text-xs border-b border-clinical-200">
                  <th className="px-3 py-2 text-left">Time</th>
                  <th className="px-3 py-2 text-left">Serial</th>
                  <th className="px-3 py-2 text-left">Lot</th>
                  <th className="px-3 py-2 text-left">To</th>
                  <th className="px-3 py-2 text-left">Status</th>
                </tr>
              </thead>
              <tbody>
                {recentTransfers.map((t) => (
                  <tr key={t.id} className="border-b border-clinical-100">
                    <td className="px-3 py-2 text-xs text-navy-500">{t.timestamp}</td>
                    <td className="px-3 py-2 font-mono text-xs">{t.gs1Data.serialNumber || 'N/A'}</td>
                    <td className="px-3 py-2 text-xs">{t.gs1Data.lotNumber || 'N/A'}</td>
                    <td className="px-3 py-2 text-xs">{t.toCustodian}</td>
                    <td className="px-3 py-2">
                      <span className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-pill text-xs ${
                        t.synced ? 'bg-emerald-50 text-emerald-700' : 'bg-amber-50 text-amber-700'
                      }`}>
                        {t.synced ? '✓ Synced' : '⏳ Local'}
                      </span>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}
