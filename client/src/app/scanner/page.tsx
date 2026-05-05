'use client';

import { useState } from 'react';
import Html5QrcodePlugin from './Html5QrcodePlugin';

export default function ScannerPage() {
  const [scanResult, setScanResult] = useState<string | null>(null);

  const onNewScan = (decodedText: string) => {
    setScanResult(decodedText);
    alert(`Successfully scanned: ${decodedText}`);
  };

  return (
    <main style={{ padding: '2rem', fontFamily: 'sans-serif', textAlign: 'center' }}>
      <h1>GS1 DataMatrix Scanner</h1>
      <p>Point your device camera at the medication code to verify custody transfer.</p>

      <div style={{ marginTop: '2rem' }}>
        <Html5QrcodePlugin onScanSuccess={onNewScan} />
      </div>

      {scanResult && (
        <div style={{ marginTop: '2rem', padding: '1rem', border: '1px solid #0070f3', borderRadius: '4px', display: 'inline-block' }}>
          <h3>Last Validated Item:</h3>
          <p>{scanResult}</p>
        </div>
      )}
    </main>
  );
}
