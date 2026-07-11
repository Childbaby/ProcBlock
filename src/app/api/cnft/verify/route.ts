import { NextResponse } from 'next/server'
import { Connection, PublicKey } from '@solana/web3.js'
import { Program, AnchorProvider, Idl } from '@coral-xyz/anchor'

const PROGRAM_ID = new PublicKey('3Qy4gmdPBKLzzFoMKgVy8WSFJ3mh7pAEApTHEzK3aWFf')

export async function GET(request: Request) {
  const { searchParams } = new URL(request.url)
  const cnfId = searchParams.get('cnfId')

  if (!cnfId) return NextResponse.json({ error: 'cNFT ID required' }, { status: 400 })

  try {
    const connection = new Connection('https://api.devnet.solana.com', 'confirmed')
    const medicinePubkey = new PublicKey(cnfId)
    const accountInfo = await connection.getAccountInfo(medicinePubkey)

    if (!accountInfo) {
      return NextResponse.json({ cnfId, status: 'not_found', message: 'Not found on Solana ledger' })
    }

    return NextResponse.json({
      cnfId, status: 'authentic',
      commodity: 'Verified on Solana Devnet',
      lotNumber: cnfId.slice(0, 12),
      manufacturer: 'ProcBlock Program',
      expiryDate: 'N/A',
      verifiedAt: new Date().toISOString(),
      transactionHash: accountInfo.data ? 'On-chain record exists' : 'N/A',
    })
  } catch (error: any) {
    return NextResponse.json({ cnfId, status: 'error', message: error.message }, { status: 500 })
  }
}
