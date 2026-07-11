import { NextResponse } from 'next/server'
import { Connection, PublicKey, Keypair } from '@solana/web3.js'
import { Program, AnchorProvider, Idl } from '@coral-xyz/anchor'

const PROGRAM_ID = new PublicKey('3Qy4gmdPBKLzzFoMKgVy8WSFJ3mh7pAEApTHEzK3aWFf')

const IDL: Idl = {
  version: '0.1.0', name: 'procblock_program',
  instructions: [
    {
      name: 'mintMedicine',
      accounts: [
        { name: 'medicine', isMut: true, isSigner: false },
        { name: 'authority', isMut: true, isSigner: true },
        { name: 'systemProgram', isMut: false, isSigner: false },
      ],
      args: [
        { name: 'commodity', type: 'string' }, { name: 'lotNumber', type: 'string' },
        { name: 'manufacturer', type: 'string' }, { name: 'expiryDate', type: 'string' },
        { name: 'serialNumber', type: 'string' }, { name: 'quantity', type: 'u32' },
      ],
    },
  ],
}

export async function POST(request: Request) {
  const body = await request.json()
  const { commodity, lotNumber, manufacturer, expiryDate, serialNumber, quantity } = body

  try {
    const connection = new Connection('https://api.devnet.solana.com', 'confirmed')
    const wallet = Keypair.generate()
    const provider = new AnchorProvider(connection, { publicKey: wallet.publicKey, signTransaction: async (tx) => tx, signAllTransactions: async (txs) => txs }, { commitment: 'confirmed' })
    const program = new Program(IDL, PROGRAM_ID, provider)

    const medicineKeypair = Keypair.generate()

    const tx = await program.methods
      .mintMedicine(commodity, lotNumber, manufacturer, expiryDate, serialNumber, quantity)
      .accounts({ medicine: medicineKeypair.publicKey, authority: wallet.publicKey, systemProgram: new PublicKey('11111111111111111111111111111111') })
      .signers([wallet, medicineKeypair])
      .rpc()

    return NextResponse.json({ success: true, cnfId: medicineKeypair.publicKey.toBase58(), transactionSignature: tx, mintedAt: new Date().toISOString() })
  } catch (error: any) {
    console.error('Mint error:', error)
    return NextResponse.json({ success: false, error: error.message }, { status: 500 })
  }
}
