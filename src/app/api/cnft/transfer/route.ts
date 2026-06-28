import { NextResponse } from 'next/server'

export async function POST(request: Request) {
  const body = await request.json()
  const { cnfId, fromCustodian, toCustodian, location } = body

  // TODO: Replace with real Solana custody transfer
  // const txSig = await program.transferCustody(cnfId, fromCustodian, toCustodian, location)

  const txSig = `4x${Math.random().toString(36).substring(2, 14)}`

  return NextResponse.json({
    success: true,
    cnfId,
    transactionSignature: txSig,
    custodyEvent: {
      timestamp: new Date().toISOString(),
      from: fromCustodian,
      to: toCustodian,
      location,
      transactionHash: txSig,
    },
  })
}
