import { NextResponse } from 'next/server'
import { Connection, PublicKey, Keypair } from '@solana/web3.js'
import { Program, AnchorProvider, Idl } from '@coral-xyz/anchor'

const PROGRAM_ID = new PublicKey('3Qy4gmdPBKLzzFoMKgVy8WSFJ3mh7pAEApTHEzK3aWFf')

export async function POST(request: Request) {
  const body = await request.json()
  const { cnfId, fromCustodian, toCustodian, location } = body

  try {
    const connection = new Connection('https://api.devnet.solana.com', 'confirmed')
    const wallet = Keypair.generate()
    const provider = new AnchorProvider(connection, { publicKey: wallet.publicKey, signTransaction: async (tx) => tx, signAllTransactions: async (txs) => txs }, { commitment: 'confirmed' })

    const IDL: Idl = {
      version: '0.1.0', name: 'procblock_program',
      instructions: [{
        name: 'transferCustody',
        accounts: [
          { name: 'medicine', isMut: true, isSigner: false },
          { name: 'authority', isMut: false, isSigner: true },
        ],
        args: [{ name: 'newCustodian', type: 'publicKey' }, { name: 'location', type: 'string' }],
      }],
    }
    const program = new Program(IDL, PROGRAM_ID, provider)

    const tx = await program.methods
      .transferCustody(new PublicKey(toCustodian), location)
      .accounts({ medicine: new PublicKey(cnfId), authority: wallet.publicKey })
      .signers([wallet])
      .rpc()

    return NextResponse.json({ success: true, cnfId, transactionSignature: tx, custodyEvent: { timestamp: new Date().toISOString(), from: fromCustodian, to: toCustodian, location, transactionHash: tx } })
  } catch (error: any) {
    console.error('Transfer error:', error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}
