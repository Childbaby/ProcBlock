import { useEffect, useRef } from 'react';
import { Html5QrcodeScanner } from 'html5-qrcode';

type Props = {
  onScanSuccess: (decodedText: string) => void;
  fps?: number;
  qrbox?: number;
};

export default function Html5QrcodePlugin({ onScanSuccess, fps = 10, qrbox = 250 }: Props) {
  const mountId = "html5qr-reader";
  const scannerRef = useRef<Html5QrcodeScanner | null>(null);

  useEffect(() => {
    const scanner = new Html5QrcodeScanner(
      mountId,
      { fps, qrbox: { width: qrbox, height: qrbox } },
      false
    );

    scanner.render(
      (decodedText: string) => {
        onScanSuccess(decodedText);
      },
      (err: any) => {
        console.warn("Scanning in progress...", err);
      }
    );

    scannerRef.current = scanner;

    return () => {
      if (scannerRef.current) {
        scannerRef.current.clear().catch((error) => {
          console.error("Failed to clear scanner.", error);
        });
      }
    };
  }, [fps, qrbox, onScanSuccess]);

  return <div id={mountId} style={{ width: '100%', maxWidth: '500px', margin: '0 auto' }} />;
}
