import { NextResponse } from 'next/server'

export async function GET() {
  // TODO: Query Solana for all ProcBlock cNFTs
  // const assets = await getAllProcBlockCNFTs()

  const assets = [
    {
      id: 'cnft-1',
      cnfId: 'cNFT-ZAM-AMX-0847',
      commodity: 'Amoxicillin 250mg Capsules',
      lotNumber: 'LOT-AMX-2024-0847',
      manufacturer: 'Zambia Pharma Ltd.',
      expiryDate: '2026-03-15',
      mintedAt: '2026-05-07T08:00:00Z',
      currentCustodian: 'Kitwe District Hub',
      currentLocation: 'Kitwe, Copperbelt Province',
      status: 'active',
      custodyChain: [
        { timestamp: '2026-05-07T08:00:00Z', from: 'Manufacturer', to: 'Lusaka Central Hub', location: 'Lusaka', transactionHash: '0x7a1b...3c4d', verified: true },
        { timestamp: '2026-05-07T12:30:00Z', from: 'Lusaka Central Hub', to: 'Kitwe District Hub', location: 'Kitwe', transactionHash: '0x8f3a...7b2d', verified: true },
      ],
    },
    {
      id: 'cnft-2',
      cnfId: 'cNFT-ZAM-INS-0192',
      commodity: 'Insulin Pens (Cold Chain)',
      lotNumber: 'LOT-INS-2024-0192',
      manufacturer: 'Novo Nordisk SA',
      expiryDate: '2025-11-20',
      mintedAt: '2026-05-07T09:00:00Z',
      currentCustodian: 'Chipata Hub',
      currentLocation: 'Chipata, Eastern Province',
      status: 'active',
      custodyChain: [
        { timestamp: '2026-05-07T09:00:00Z', from: 'Manufacturer', to: 'Lusaka Central Hub', location: 'Lusaka', transactionHash: '0x2e5f...8a1c', verified: true },
        { timestamp: '2026-05-07T13:00:00Z', from: 'Lusaka Central Hub', to: 'Chipata Hub', location: 'Chipata', transactionHash: '0x9b4d...2f6e', verified: false },
      ],
    },
  ]

  return NextResponse.json({ assets, total: assets.length })
}
