import { NextResponse } from 'next/server'

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const cnfId = searchParams.get('cnfId')

  if (!cnfId) {
    return NextResponse.json({ error: 'cNFT ID required' }, { status: 400 })
  }

  // TODO: Query Solana for cNFT existence and status
  // const asset = await getAsset(cnfId)

  // Mock verification — replace with real ledger lookup
  if (cnfId.startsWith('cNFT-ZAM-') || cnfId.startsWith('ZAM-')) {
    return NextResponse.json({
      cnfId,
      status: 'authentic',
      commodity: 'Amoxicillin 250mg Capsules',
      lotNumber: 'LOT-AMX-2024-0847',
      manufacturer: 'Zambia Pharma Ltd.',
      expiryDate: '2026-03-15',
      verifiedAt: new Date().toISOString(),
    })
  }

  if (cnfId.includes('FLAGGED')) {
    return NextResponse.json({
      cnfId,
      status: 'flagged',
      reason: 'Product marked as suspicious in ZAMMSA Ledger',
      hotline: '+260 211 123 456',
    })
  }

  return NextResponse.json({
    cnfId,
    status: 'not_found',
    message: 'Serial number not found in ZAMMSA Ledger',
  })
}
