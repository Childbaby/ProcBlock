'use client'

import { useWallet } from '@solana/wallet-adapter-react'
import { useRouter } from 'next/navigation'
import { useEffect, useState } from 'react'
import bs58 from 'bs58'
import nacl from 'tweetnacl'

export function useBlockchainAuth() {
  const { publicKey, signMessage, connected, connecting, connect } = useWallet()
  const router = useRouter()
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [anonymousId, setAnonymousId] = useState<string | null>(null)

  // Generate anonymous ID from wallet address (hash it)
  useEffect(() => {
    if (publicKey) {
      const address = publicKey.toBase58()
      // Create anonymous ID: first 4 + last 4 chars with ... in middle
      const anonId = `${address.slice(0, 6)}...${address.slice(-4)}`
      setAnonymousId(anonId)
    }
  }, [publicKey])

  const loginWithWallet = async () => {
    if (!signMessage || !publicKey) {
      await connect()
      return
    }

    try {
      // Challenge message — the user signs this to prove they own the wallet
      const message = `ProcBlock Login: ${new Date().toISOString()}`
      const encodedMessage = new TextEncoder().encode(message)
      const signature = await signMessage(encodedMessage)

      // Verify the signature (this is what the backend would do)
      const verified = nacl.sign.detached.verify(
        encodedMessage,
        signature,
        publicKey.toBytes()
      )

      if (verified) {
        setIsAuthenticated(true)
        router.push('/dashboard')
      }
    } catch (error) {
      console.error('Login failed:', error)
    }
  }

  const logout = () => {
    setIsAuthenticated(false)
    setAnonymousId(null)
    router.push('/')
  }

  return {
    publicKey,
    anonymousId,
    isAuthenticated,
    connecting,
    connected,
    loginWithWallet,
    logout,
  }
}
