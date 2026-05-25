'use client'

import { Html5QrcodeScanner } from 'html5-qrcode'
import { useEffect, useRef } from 'react'

interface Props {
  fps?: number
  qrbox?: { width: number; height: number }
  disableFlip?: boolean
  qrCodeSuccessCallback: (decodedText: string) => void
  qrCodeErrorCallback?: (errorMessage: string) => void
}

export function Html5QrcodePlugin({
  fps = 10,
  qrbox = { width: 250, height: 250 },
  disableFlip = false,
  qrCodeSuccessCallback,
  qrCodeErrorCallback,
}: Props) {
  const scannerRef = useRef<Html5QrcodeScanner | null>(null)
  const containerId = 'html5qr-code-scanner'

  useEffect(() => {
    scannerRef.current = new Html5QrcodeScanner(
      containerId,
      {
        fps,
        qrbox,
        supportedScanTypes: [],
      },
      false
    )

    scannerRef.current.render(
      qrCodeSuccessCallback,
      qrCodeErrorCallback || (() => {})
    )

    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear().catch(console.error)
      }
    }
  }, [fps, qrbox, disableFlip, qrCodeSuccessCallback, qrCodeErrorCallback])

  return <div id={containerId} className="w-full bg-black rounded-medical overflow-hidden" />
}
