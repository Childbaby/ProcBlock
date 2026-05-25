import type { Metadata } from 'next'
import { HeaderWrapper } from '@/components/HeaderWrapper'
import './globals.css'

export const metadata: Metadata = {
  title: 'ProcBlock | ZAMMSA Medical Supply Portal',
  description: 'Decentralized medical logistics system for the Zambia Medicines and Medical Supplies Agency',
  icons: {
    icon: '/favicon.ico',
  },
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className="min-h-screen flex flex-col">
        <HeaderWrapper />
        <main className="flex-1">{children}</main>
      </body>
    </html>
  )
}
