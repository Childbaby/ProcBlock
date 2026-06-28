'use client'

import { useState, FormEvent } from 'react'

export default function VerifyPage() {
  const [searchCode, setSearchCode] = useState('')
  const [isVerifying, setIsVerifying] = useState(false)
  const [result, setResult] = useState<any>(null)

  const handleVerify = async (e: FormEvent) => {
    e.preventDefault()
    if (!searchCode.trim()) return
    setIsVerifying(true)
    try {
      const res = await fetch(`/api/cnft/verify?cnfId=${encodeURIComponent(searchCode.trim())}`)
      const data = await res.json()
      setResult(data)
    } catch {
      setResult({ status: 'error', message: 'Failed to reach ledger' })
    }
    setIsVerifying(false)
  }

  return (
    <div className="min-h-[80vh] flex flex-col px-4">
      <div className="text-center mb-12">
        <h1 className="text-display-md text-navy-800 mb-2">Public Medicine Verification</h1>
        <p className="text-sm text-navy-500 max-w-lg mx-auto">Verify authenticity against the ZAMMSA Secure Ledger on Solana.</p>
      </div>

      <div className="max-w-xl mx-auto w-full mb-12">
        <form onSubmit={handleVerify} className="flex gap-3">
          <input type="text" value={searchCode} onChange={e => setSearchCode(e.target.value)} className="input-clinical flex-1 font-mono text-lg" placeholder="Enter serial number (e.g., ZAM-2847)" disabled={isVerifying} />
          <button type="submit" className="btn-primary flex items-center gap-2" disabled={isVerifying || !searchCode.trim()}>
            {isVerifying ? 'Verifying...' : 'Verify'}
          </button>
        </form>
      </div>

      {result && (
        <div className="max-w-xl mx-auto w-full">
          {result.status === 'authentic' && (
            <div className="certificate-container">
              <div className="text-center mb-8">
                <div className="w-16 h-16 mx-auto mb-4 bg-emerald-50 rounded-full flex items-center justify-center">
                  <span className="text-3xl">✅</span>
                </div>
                <h2 className="text-display-sm text-navy-800 mb-1">Medicine Verified</h2>
                <p className="text-sm text-navy-500">Authentic — Registered on ZAMMSA Ledger (Solana)</p>
              </div>
              <div className="grid grid-cols-2 gap-4 mb-8">
                {[['Product', result.commodity], ['Lot Number', result.lotNumber], ['Manufacturer', result.manufacturer], ['Expiry Date', result.expiryDate]].map(([label, value]) => (
                  <div key={label}><p className="text-xs text-navy-400 mb-0.5">{label}</p><p className="text-sm font-medium text-navy-800">{value}</p></div>
                ))}
              </div>
              <div className="mt-6 text-center"><p className="text-xs text-navy-400">Secured by Solana Blockchain · ProcBlock</p></div>
            </div>
          )}
          {result.status === 'flagged' && (
            <div className="clinical-card border-l-4 border-l-status-critical bg-red-50/50">
              <div className="text-center">
                <span className="text-4xl">🚩</span>
                <h2 className="text-display-sm text-status-critical mb-1">Product Flagged</h2>
                <p className="text-sm text-navy-600 mb-4">Do not use. Contact ZAMMSA: +260 211 123 456</p>
              </div>
            </div>
          )}
          {result.status === 'not_found' && (
            <div className="clinical-card border-l-4 border-l-status-warning bg-amber-50/50">
              <div className="text-center">
                <span className="text-4xl">❓</span>
                <h2 className="text-display-sm text-navy-800 mb-1">Not Found</h2>
                <p className="text-sm text-navy-600">Not found in ZAMMSA Ledger. Possible counterfeit.</p>
                <button onClick={() => { setResult(null); setSearchCode('') }} className="btn-secondary mt-6">Try Another Code</button>
              </div>
            </div>
          )}
        </div>
      )}

      {!result && (
        <div className="max-w-xl mx-auto w-full mt-8 clinical-card text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-status-verified" />
            <span className="text-xs font-medium text-navy-600">ZAMMSA Ledger Online (Solana Devnet)</span>
          </div>
          <p className="text-xs text-navy-400">Every verification is checked against the immutable distributed ledger.</p>
        </div>
      )}
    </div>
  )
}
