'use client'

import { useState, useCallback } from 'react'
import dynamic from 'next/dynamic'
import { parseGS1DataMatrix, generateTestGS1Code, type GS1Data } from '@/lib/gs1-parser'
import { saveTransferOffline, getCachedTransferCount } from '@/lib/indexeddb-cache'
import { transferCustody } from '@/lib/cnft-service'

const Html5QrcodePlugin = dynamic(() => import('./Html5QrcodePlugin').then(m => ({ default: m.Html5QrcodePlugin })), { ssr: false })

export default function ScannerPage() {
  const [scanResult, setScanResult] = useState<GS1Data | null>(null)
  const [isScanning, setIsScanning] = useState(false)
  const [manualCode, setManualCode] = useState('')
  const [transferStatus, setTransferStatus] = useState<'idle' | 'processing' | 'success' | 'error'>('idle')
  const [toCustodian, setToCustodian] = useState('')
  const [currentLocation, setCurrentLocation] = useState('')
  const [txSignature, setTxSignature] = useState<string | null>(null)
  const [pendingCount, setPendingCount] = useState(0)
  const [mode, setMode] = useState<'camera' | 'file' | 'manual'>('manual')

  const handleScanSuccess = useCallback((decodedText: string) => {
    const parsed = parseGS1DataMatrix(decodedText)
    if (parsed) { setScanResult(parsed); setIsScanning(false); setTransferStatus('idle'); setTxSignature(null) }
  }, [])

  const handleManualSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!manualCode.trim()) return
    const parsed = parseGS1DataMatrix(manualCode.trim())
    if (parsed) { setScanResult(parsed); setManualCode(''); setTransferStatus('idle'); setTxSignature(null) }
  }

  const handleAcceptTransfer = async () => {
    if (!scanResult) return
    setTransferStatus('processing')
    try {
      const result = await transferCustody({
        cnfId: `cNFT-ZAM-${scanResult.serialNumber || Date.now()}`,
        fromCustodian: 'Lusaka Central Hub',
        toCustodian: toCustodian || 'Field Worker',
        location: currentLocation || 'Unknown Location',
      })
      setTxSignature(result.transactionSignature)
      await saveTransferOffline({
        cnfId: result.cnfId,
        fromCustodian: 'Lusaka Central Hub',
        toCustodian: toCustodian || 'Field Worker',
        location: currentLocation || 'Unknown Location',
        commodity: scanResult.gtin || 'Unknown',
        lotNumber: scanResult.lotNumber || 'N/A',
        timestamp: new Date().toISOString(),
      })
      setTransferStatus('success')
      setPendingCount(prev => prev + 1)
      setTimeout(() => { setScanResult(null); setTransferStatus('idle'); setToCustodian(''); setCurrentLocation(''); setTxSignature(null) }, 3000)
    } catch {
      setTransferStatus('error')
      setTimeout(() => setTransferStatus('idle'), 3000)
    }
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6 px-4 pb-12">
      <div>
        <h1 className="text-display-md text-navy-800">Field Scanner</h1>
        <p className="text-sm text-navy-500 mt-1">Scan GS1 DataMatrix barcodes — transfers recorded on Solana</p>
        {pendingCount > 0 && (
          <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 rounded-pill bg-amber-50 border border-amber-200 text-xs font-medium text-amber-700">
            <span className="w-2 h-2 rounded-full bg-amber-500 animate-pulse" />
            {pendingCount} transfer{pendingCount > 1 ? 's' : ''} pending sync
          </div>
        )}
      </div>

      <div className="flex gap-2 overflow-x-auto pb-1">
        {(['manual', 'camera', 'file'] as const).map(opt => (
          <button key={opt} onClick={() => { setMode(opt); setIsScanning(false); setScanResult(null) }}
            className={`px-4 py-2 rounded-pill text-xs font-semibold whitespace-nowrap transition-all ${mode === opt ? 'bg-navy-800 text-white shadow-medical' : 'bg-clinical-100 text-navy-500 hover:bg-clinical-200 border border-clinical-200'}`}>
            {opt === 'manual' ? '📝 Manual' : opt === 'camera' ? '📷 Camera' : '🖼️ Upload'}
          </button>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
          {mode === 'manual' && (
            <form onSubmit={handleManualSubmit} className="space-y-4">
              <h3 className="text-lg font-semibold text-navy-800">Manual Code Entry</h3>
              <textarea id="manual-code" value={manualCode} onChange={e => setManualCode(e.target.value)}
                className="w-full px-4 py-3 bg-clinical-100 border border-clinical-300 rounded-medical text-navy-800 placeholder:text-navy-400 focus:border-teal-medical focus:ring-2 focus:ring-teal-light outline-none font-mono text-sm resize-none h-24"
                placeholder="Paste GS1 code here..." />
              <button type="submit" className="btn-primary w-full" disabled={!manualCode.trim()}>Parse Code</button>
              <button type="button" onClick={() => setManualCode(generateTestGS1Code())} className="btn-secondary w-full text-sm">🧪 Load Test Code</button>
            </form>
          )}
          {mode === 'camera' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-navy-800">Camera Scanner</h3>
              {isScanning ? (
                <>
                  <div className="relative border-2 border-teal-medical rounded-medical overflow-hidden bg-black">
                    <Html5QrcodePlugin fps={10} qrbox={{ width: 250, height: 250 }} disableFlip={false} qrCodeSuccessCallback={handleScanSuccess} qrCodeErrorCallback={() => {}} />
                  </div>
                  <button onClick={() => setIsScanning(false)} className="btn-secondary w-full">Stop Scanner</button>
                </>
              ) : (
                <div className="text-center py-16">
                  <div className="w-20 h-20 mx-auto mb-4 bg-teal-light rounded-full flex items-center justify-center">
                    <svg className="w-10 h-10 text-teal-medical" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" /></svg>
                  </div>
                  <p className="text-sm text-navy-500 mb-4">Position DataMatrix within frame</p>
                  <button onClick={() => setIsScanning(true)} className="btn-primary">Start Camera</button>
                </div>
              )}
            </div>
          )}
          {mode === 'file' && (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-navy-800">Upload Barcode Image</h3>
              <div className="border-2 border-dashed border-clinical-300 rounded-medical p-8 text-center">
                <p className="text-sm text-navy-500">📤 Upload a barcode image to scan</p>
              </div>
            </div>
          )}
        </div>

        <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
          {scanResult ? (
            <div className="space-y-4">
              <h3 className="text-lg font-semibold text-navy-800 flex items-center gap-2"><span className="text-emerald-500">✓</span> Code Parsed</h3>
              <div className="bg-clinical-100 rounded-medical p-4 space-y-2">
                {[['GTIN', scanResult.gtin || 'N/A', true], ['Lot Number', scanResult.lotNumber || 'N/A', false], ['Expiry Date', scanResult.expiryDate || 'N/A', false], ['Serial Number', scanResult.serialNumber || 'N/A', true], ['Quantity', scanResult.quantity?.toString() || 'N/A', false]].map(([label, value, mono]) => (
                  <div key={label} className="flex justify-between"><span className="text-xs text-navy-400">{label}</span><span className={`text-sm font-medium text-navy-800 ${mono ? 'font-mono' : ''}`}>{value as string}</span></div>
                ))}
              </div>
              <div className="space-y-3 pt-2">
                <h4 className="text-sm font-semibold text-navy-700">Accept Custody Transfer</h4>
                <input type="text" value={toCustodian} onChange={e => setToCustodian(e.target.value)} placeholder="Your name / Custodian ID" className="w-full px-4 py-2.5 bg-clinical-100 border border-clinical-300 rounded-medical text-sm text-navy-800 outline-none" />
                <input type="text" value={currentLocation} onChange={e => setCurrentLocation(e.target.value)} placeholder="Current location" className="w-full px-4 py-2.5 bg-clinical-100 border border-clinical-300 rounded-medical text-sm text-navy-800 outline-none" />
              </div>
              <div className="flex gap-3 pt-2">
                <button onClick={handleAcceptTransfer} disabled={transferStatus === 'processing'} className="btn-primary flex-1 disabled:opacity-60">
                  {transferStatus === 'processing' ? '⏳ Processing...' : transferStatus === 'success' ? '✅ Transfer Saved' : 'Accept Transfer'}
                </button>
                <button onClick={() => { setScanResult(null); setTransferStatus('idle') }} className="btn-secondary">Clear</button>
              </div>
              {transferStatus === 'success' && (
                <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-medical text-sm text-emerald-700">
                  <p className="font-medium">✅ Custody transfer recorded</p>
                  {txSignature && <p className="text-xs font-mono mt-1">Tx: {txSignature}</p>}
                </div>
              )}
              {transferStatus === 'error' && <div className="p-3 bg-red-50 border border-red-200 rounded-medical text-sm text-red-700">Transfer failed. Please try again.</div>}
            </div>
          ) : (
            <div className="flex items-center justify-center h-full min-h-[300px] text-navy-400">
              <div className="text-center"><p className="text-sm font-medium">Scan or enter a GS1 code</p><p className="text-xs mt-1">Parsed data will appear here</p></div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
