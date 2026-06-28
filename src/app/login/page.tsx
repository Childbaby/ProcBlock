'use client'

import { useState, useCallback, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { useWallet } from '@solana/wallet-adapter-react'
import { WalletMultiButton } from '@solana/wallet-adapter-react-ui'

export default function BlockchainLoginPage() {
  const router = useRouter()
  const { publicKey, signMessage, connected, connecting, select, wallet, wallets } = useWallet()
  const [isSigningIn, setIsSigningIn] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Auto-connect to Phantom if already installed
  useEffect(() => {
    const phantomWallet = wallets.find(w => w.adapter.name === 'Phantom')
    if (phantomWallet && !connected && !connecting) {
      select(phantomWallet.adapter.name)
    }
  }, [wallets, connected, connecting, select])

  const handleSignIn = useCallback(async () => {
    if (!signMessage || !publicKey) {
      setError('Wallet not connected. Please connect your wallet first.')
      return
    }

    setIsSigningIn(true)
    setError(null)

    try {
      const message = `ProcBlock Login: ${new Date().toISOString()}`
      const encodedMessage = new TextEncoder().encode(message)
      await signMessage(encodedMessage)

      const address = publicKey.toBase58()
      const anonId = `${address.slice(0, 6)}...${address.slice(-4)}`
      localStorage.setItem('procblock_wallet', address)
      localStorage.setItem('procblock_anon_id', anonId)

      router.push('/dashboard')
    } catch (err: any) {
      console.error('Sign in error:', err)
      setError(err.message || 'Sign in failed. Please approve the signature request.')
    } finally {
      setIsSigningIn(false)
    }
  }, [publicKey, signMessage, router])

  return (
    <div className="min-h-screen flex">
      {/* Left Panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-navy-800 relative overflow-hidden">
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-teal-medical via-purple-500 to-teal-medical" />
        <div className="relative z-10 flex flex-col justify-center px-16 w-full">
          <div className="mb-12">
            <Link href="/" className="flex items-center gap-4 mb-6 group">
              <svg width="56" height="56" viewBox="0 0 36 36" fill="none" className="transition-transform duration-300 group-hover:scale-105">
                <path d="M18 2L32 9.5V24.5L18 32L4 24.5V9.5L18 2Z" className="stroke-white" strokeWidth="2" fill="none" />
                <rect x="15" y="10" width="6" height="16" rx="1" className="fill-teal-medical" />
                <rect x="10" y="15" width="16" height="6" rx="1" className="fill-teal-medical" />
              </svg>
              <div>
                <h1 className="text-3xl font-bold text-white">ProcBlock</h1>
                <p className="text-teal-medical text-sm font-medium">ZAMMSA PORTAL</p>
              </div>
            </Link>
            <p className="text-navy-200 text-lg leading-relaxed max-w-md">
              Sign in with your Solana wallet. No passwords. No database.
            </p>
          </div>
          <div className="space-y-6">
            {['Wallet-Based Auth', 'No Personal Data', 'Immutable Logs', 'Anonymous Identity'].map(label => (
              <div key={label} className="flex items-center gap-3 text-navy-200">
                <span className="w-2 h-2 rounded-full bg-teal-medical" />
                <span className="text-sm font-medium">{label}</span>
              </div>
            ))}
          </div>
          <div className="mt-auto pt-16">
            <div className="flex items-center gap-2 text-navy-400 text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              Solana Devnet — Live
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="flex-1 flex items-center justify-center px-6 sm:px-12 lg:px-16 bg-clinical-100">
        <div className="w-full max-w-md">
          <div className="lg:hidden text-center mb-10">
            <h2 className="text-xl font-bold text-navy-800">ProcBlock</h2>
          </div>

          <div className="bg-white border border-gray-200 rounded-2xl shadow-lg p-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-navy-800 mb-1">Connect Wallet</h2>
              <p className="text-sm text-gray-500">No username. No password.</p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-xl text-sm text-red-700">
                {error}
              </div>
            )}

            {/* This button directly opens Phantom */}
            <div className="flex justify-center mb-6">
              <WalletMultiButton style={{
                backgroundColor: '#1E293B',
                borderRadius: '12px',
                padding: '12px 32px',
                fontSize: '16px',
                fontWeight: 600,
                color: 'white',
                border: 'none',
                cursor: 'pointer',
                width: '100%',
                justifyContent: 'center',
              }} />
            </div>

            {connected && publicKey && (
              <div className="space-y-4">
                <div className="p-4 bg-emerald-50 border border-emerald-200 rounded-xl text-center">
                  <p className="text-xs text-emerald-600">Wallet Connected</p>
                  <p className="font-mono text-sm font-semibold text-emerald-800 mt-1">
                    {publicKey.toBase58().slice(0, 8)}...{publicKey.toBase58().slice(-6)}
                  </p>
                </div>

                <button
                  onClick={handleSignIn}
                  disabled={isSigningIn}
                  className="w-full py-3 bg-teal-medical hover:bg-teal-dark text-white font-semibold rounded-xl transition-all duration-200 disabled:opacity-60 flex items-center justify-center gap-2"
                >
                  {isSigningIn ? 'Signing...' : 'Sign In with Wallet'}
                </button>
              </div>
            )}

            <div className="mt-6 pt-4 border-t border-gray-200">
              <p className="text-xs text-gray-400 text-center">
                All activity recorded on Solana. Your wallet is your identity.
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
