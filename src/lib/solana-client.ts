import { Connection, PublicKey } from '@solana/web3.js'

const DEVNET_RPC = 'https://api.devnet.solana.com'
export const connection = new Connection(DEVNET_RPC, 'confirmed')

// Placeholder — your teammate provides the real one
export const PROGRAM_ID = new PublicKey('ProcBlock111111111111111111111111111111111')

export async function getSolanaBalance(address: string): Promise<number> {
  const pubkey = new PublicKey(address)
  return connection.getBalance(pubkey)
}

export async function confirmTransaction(signature: string) {
  return connection.confirmTransaction(signature, 'confirmed')
}
