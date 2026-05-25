'use client'

import { useState, FormEvent } from 'react'
import { useRouter } from 'next/navigation'
import Link from 'next/link'

export default function LoginPage() {
  const router = useRouter()
  const [credentials, setCredentials] = useState({ username: '', password: '' })
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleLogin = async (e: FormEvent) => {
    e.preventDefault()
    setError(null)
    setIsLoading(true)

    await new Promise((resolve) => setTimeout(resolve, 1800))

    if (credentials.username === 'admin' && credentials.password === 'zammsa2024') {
      router.push('/dashboard')
    } else if (credentials.username === 'field' && credentials.password === 'zammsa2024') {
      router.push('/scanner')
    } else {
      setError('Invalid credentials. Please try again.')
    }

    setIsLoading(false)
  }

  return (
    <div className="min-h-screen flex">
      {/* Left Panel — Branding */}
      <div className="hidden lg:flex lg:w-1/2 bg-navy-800 relative overflow-hidden">
        <div className="absolute inset-0 opacity-10" style={{ backgroundImage: `url("data:image/svg+xml,%3Csvg width='60' height='60' viewBox='0 0 60 60' xmlns='http://www.w3.org/2000/svg'%3E%3Cg fill='none' fill-rule='evenodd'%3E%3Cg fill='%23FFFFFF' fill-opacity='1'%3E%3Cpath d='M36 34v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zm0-30V0h-2v4h-4v2h4v4h2V6h4V4h-4zM6 34v-4H4v4H0v2h4v4h2v-4h4v-2H6zM6 4V0H4v4H0v2h4v4h2V6h4V4H6z'/%3E%3C/g%3E%3C/g%3E%3C/svg%3E")` }} />
        <div className="absolute top-0 left-0 w-full h-1 bg-gradient-to-r from-teal-medical via-teal-light to-teal-medical" />
        <div className="relative z-10 flex flex-col justify-center px-16 w-full">
          <div className="mb-12">
            {/* Clickable Logo — navigates to landing page */}
            <Link href="/" className="flex items-center gap-4 mb-6 group cursor-pointer">
              <svg width="56" height="56" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true" className="transition-transform duration-300 group-hover:scale-105">
                <path d="M18 2L32 9.5V24.5L18 32L4 24.5V9.5L18 2Z" className="stroke-white" strokeWidth="2" fill="none" />
                <rect x="15" y="10" width="6" height="16" rx="1" className="fill-teal-medical" />
                <rect x="10" y="15" width="16" height="6" rx="1" className="fill-teal-medical" />
              </svg>
              <div>
                <h1 className="text-3xl font-bold text-white tracking-tight group-hover:text-teal-light transition-colors duration-300">ProcBlock</h1>
                <p className="text-teal-medical text-sm font-medium tracking-wide">ZAMMSA PORTAL</p>
              </div>
            </Link>
            <p className="text-navy-200 text-lg leading-relaxed max-w-md">
              A decentralized, high-integrity logistics system for the Zambia Medicines and Medical Supplies Agency.
            </p>
          </div>
          <div className="space-y-6">
            {[
              { label: 'Immutable Ledger Technology' },
              { label: 'Counterfeit Prevention' },
              { label: 'Real-Time Supply Tracking' },
            ].map((item) => (
              <div key={item.label} className="flex items-center gap-3 text-navy-200">
                <span className="w-2 h-2 rounded-full bg-teal-medical" />
                <span className="text-sm font-medium">{item.label}</span>
              </div>
            ))}
          </div>
          <div className="mt-auto pt-16">
            <div className="flex items-center gap-2 text-navy-400 text-xs">
              <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
              ZAMMSA Ledger Network — Online
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel — Login Form */}
      <div className="flex-1 flex items-center justify-center px-6 sm:px-12 lg:px-16 bg-clinical-100">
        <div className="w-full max-w-md">
          {/* Mobile Logo — also clickable */}
          <div className="lg:hidden text-center mb-10">
            <Link href="/" className="inline-block group">
              <svg width="48" height="48" viewBox="0 0 36 36" fill="none" xmlns="http://www.w3.org/2000/svg" className="mx-auto mb-3 transition-transform duration-300 group-hover:scale-105" aria-hidden="true">
                <path d="M18 2L32 9.5V24.5L18 32L4 24.5V9.5L18 2Z" className="stroke-navy-800" strokeWidth="2" fill="none" />
                <rect x="15" y="10" width="6" height="16" rx="1" className="fill-teal-medical" />
                <rect x="10" y="15" width="16" height="6" rx="1" className="fill-teal-medical" />
              </svg>
              <h2 className="text-xl font-bold text-navy-800 group-hover:text-teal-medical transition-colors duration-300">ProcBlock</h2>
              <p className="text-xs text-navy-400">ZAMMSA Portal</p>
            </Link>
          </div>
          <div className="bg-clinical-50 border border-clinical-300 rounded-2xl shadow-medical-lg p-8">
            <div className="text-center mb-8">
              <h2 className="text-2xl font-bold text-navy-800 mb-1">Welcome Back</h2>
              <p className="text-sm text-navy-500">Sign in to access the ZAMMSA portal</p>
            </div>

            {error && (
              <div className="mb-6 p-4 bg-red-50 border border-red-200 rounded-medical flex items-center gap-3">
                <span className="text-red-500 shrink-0">⚠</span>
                <p className="text-sm text-red-700">{error}</p>
              </div>
            )}

            <form onSubmit={handleLogin} className="space-y-5">
              <div>
                <label htmlFor="username" className="block text-sm font-semibold text-navy-700 mb-1.5">Username</label>
                <input
                  id="username"
                  type="text"
                  value={credentials.username}
                  onChange={(e) => setCredentials({ ...credentials, username: e.target.value })}
                  className="w-full px-4 py-3 bg-clinical-100 border border-clinical-300 rounded-medical text-navy-800 placeholder:text-navy-400 focus:border-teal-medical focus:ring-2 focus:ring-teal-light transition-all duration-200 outline-none"
                  placeholder="Enter your username"
                  autoComplete="username"
                  required
                  disabled={isLoading}
                />
              </div>
              <div>
                <label htmlFor="password" className="block text-sm font-semibold text-navy-700 mb-1.5">Password</label>
                <input
                  id="password"
                  type="password"
                  value={credentials.password}
                  onChange={(e) => setCredentials({ ...credentials, password: e.target.value })}
                  className="w-full px-4 py-3 bg-clinical-100 border border-clinical-300 rounded-medical text-navy-800 placeholder:text-navy-400 focus:border-teal-medical focus:ring-2 focus:ring-teal-light transition-all duration-200 outline-none"
                  placeholder="Enter your password"
                  autoComplete="current-password"
                  required
                  disabled={isLoading}
                />
              </div>
              <button
                type="submit"
                disabled={isLoading}
                className="w-full py-3 bg-navy-800 hover:bg-navy-700 active:bg-navy-900 text-white font-semibold rounded-medical transition-all duration-200 focus:outline-none focus:ring-2 focus:ring-teal-medical focus:ring-offset-2 disabled:opacity-60 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {isLoading ? 'Authenticating...' : 'Sign In'}
              </button>
            </form>
            <div className="mt-6 pt-4 border-t border-clinical-200">
              <p className="text-xs text-navy-400 text-center">Restricted system. All access is logged and monitored.</p>
            </div>
          </div>
          <div className="mt-6 p-4 bg-navy-50 border border-navy-200 rounded-medical">
            <p className="text-xs font-semibold text-navy-600 mb-2">Demo Credentials</p>
            <div className="space-y-1 text-xs text-navy-500">
              <p><span className="font-mono text-navy-700">admin</span> / <span className="font-mono text-navy-700">zammsa2024</span> → Dashboard</p>
              <p><span className="font-mono text-navy-700">field</span> / <span className="font-mono text-navy-700">zammsa2024</span> → Field Scanner</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
