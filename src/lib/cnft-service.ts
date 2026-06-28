interface MintCNFTParams {
  commodity: string
  lotNumber: string
  manufacturer: string
  expiryDate: string
  serialNumber: string
  quantity: number
  initialCustodian: string
}

interface TransferCNFTParams {
  cnfId: string
  fromCustodian: string
  toCustodian: string
  location: string
}

export async function mintCNFT(params: MintCNFTParams) {
  const res = await fetch('/api/cnft/mint', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return res.json()
}

export async function transferCustody(params: TransferCNFTParams) {
  const res = await fetch('/api/cnft/transfer', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(params),
  })
  return res.json()
}

export async function verifyCNFT(cnfId: string) {
  const res = await fetch(`/api/cnft/verify?cnfId=${encodeURIComponent(cnfId)}`)
  return res.json()
}

export async function listCNFTs() {
  const res = await fetch('/api/cnft/list')
  return res.json()
}
