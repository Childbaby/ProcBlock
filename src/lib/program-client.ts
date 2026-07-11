import { Connection, PublicKey } from '@solana/web3.js'
import { Program, AnchorProvider, Idl } from '@coral-xyz/anchor'

const PROGRAM_ID = new PublicKey('3Qy4gmdPBKLzzFoMKgVy8WSFJ3mh7pAEApTHEzK3aWFf')

// Minimal IDL matching your deployed contract
const IDL: Idl = {
  version: '0.1.0',
  name: 'procblock_program',
  instructions: [
    {
      name: 'mintMedicine',
      accounts: [
        { name: 'medicine', isMut: true, isSigner: false },
        { name: 'authority', isMut: true, isSigner: true },
        { name: 'systemProgram', isMut: false, isSigner: false },
      ],
      args: [
        { name: 'commodity', type: 'string' },
        { name: 'lotNumber', type: 'string' },
        { name: 'manufacturer', type: 'string' },
        { name: 'expiryDate', type: 'string' },
        { name: 'serialNumber', type: 'string' },
        { name: 'quantity', type: 'u32' },
      ],
    },
    {
      name: 'transferCustody',
      accounts: [
        { name: 'medicine', isMut: true, isSigner: false },
        { name: 'authority', isMut: false, isSigner: true },
      ],
      args: [
        { name: 'newCustodian', type: 'publicKey' },
        { name: 'location', type: 'string' },
      ],
    },
    {
      name: 'verifyMedicine',
      accounts: [
        { name: 'medicine', isMut: false, isSigner: false },
      ],
      args: [],
    },
  ],
}

export function getProgram(wallet: any) {
  const connection = new Connection('https://api.devnet.solana.com', 'confirmed')
  const provider = new AnchorProvider(connection, wallet, { commitment: 'confirmed' })
  return new Program(IDL, PROGRAM_ID, provider)
}

export { PROGRAM_ID }
