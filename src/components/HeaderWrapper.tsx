'use client'

import { usePathname } from 'next/navigation'
import { Header } from '@/components/Header'

export function HeaderWrapper() {
  const pathname = usePathname()

  // Hide header on landing page and login page
  if (pathname === '/' || pathname === '/login') return null

  return <Header />
}
