import type { Metadata } from 'next'
import { SolanaWalletProvider } from '@/components/WalletProvider'
import { HeaderWrapper } from '@/components/HeaderWrapper'
import './globals.css'

export const metadata: Metadata = {
  title: 'ProcBlock | ZAMMSA Medical Supply Portal',
  description: 'Decentralized medical logistics system on Solana',
  manifest: '/manifest.json',
  icons: { icon: '/favicon.ico' },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <SolanaWalletProvider>
          <HeaderWrapper />
          <main className="flex-1">{children}</main>
        </SolanaWalletProvider>
      </body>
    </html>
  )
}
