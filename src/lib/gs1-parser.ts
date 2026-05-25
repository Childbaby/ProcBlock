export interface GS1Data {
  gtin: string
  lotNumber: string
  expiryDate: string
  serialNumber: string
  quantity?: number
}

export function parseGS1DataMatrix(raw: string): GS1Data | null {
  try {
    const cleaned = raw.replace(/[^\x20-\x7E]/g, '')
    const result: Partial<GS1Data> = {}

    const gtinMatch = cleaned.match(/01(\d{14})/)
    if (gtinMatch) result.gtin = gtinMatch[1]

    const lotMatch = cleaned.match(/10([A-Za-z0-9\-]{1,20})/)
    if (lotMatch) result.lotNumber = lotMatch[1]

    const expiryMatch = cleaned.match(/17(\d{6})/)
    if (expiryMatch) {
      const rawDate = expiryMatch[1]
      result.expiryDate = `20${rawDate.substring(0,2)}-${rawDate.substring(2,4)}-${rawDate.substring(4,6)}`
    }

    const serialMatch = cleaned.match(/21([A-Za-z0-9\-]{1,20})/)
    if (serialMatch) result.serialNumber = serialMatch[1]

    const qtyMatch = cleaned.match(/37(\d{1,8})/)
    if (qtyMatch) result.quantity = parseInt(qtyMatch[1])

    if (result.gtin || result.serialNumber) return result as GS1Data

    return { gtin: '', lotNumber: '', expiryDate: '', serialNumber: cleaned }
  } catch {
    return null
  }
}

export function generateTestGS1Code(): string {
  const gtin = '07612345678901'
  const lot = 'LOT-TEST-' + Math.random().toString(36).substring(2, 8).toUpperCase()
  const expiry = '260315'
  const serial = 'ZAM-' + Math.random().toString(36).substring(2, 10).toUpperCase()
  const qty = Math.floor(Math.random() * 9000 + 1000).toString()
  return `010${gtin}10${lot}17${expiry}21${serial}37${qty}`
}
