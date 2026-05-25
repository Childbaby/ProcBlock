"use client";

import { useState, FormEvent } from "react";

interface VerifiedProduct {
  commodity: string;
  lotNumber: string;
  manufacturer: string;
  expiryDate: string;
  description: string;
  verifiedAt: string;
  ledgerEntry: string;
  status: "authentic" | "not_found" | "flagged";
}

export default function VerifyPage() {
  const [searchCode, setSearchCode] = useState("");
  const [isVerifying, setIsVerifying] = useState(false);
  const [result, setResult] = useState<VerifiedProduct | null>(null);
  const [error, setError] = useState<string | null>(null);

  const handleVerify = async (e: FormEvent) => {
    e.preventDefault();
    if (!searchCode.trim()) return;

    setIsVerifying(true);
    setError(null);
    setResult(null);

    // Simulate ledger verification delay
    await new Promise((resolve) => setTimeout(resolve, 1500));

    // Mock verification — replace with actual ledger query
    if (searchCode.startsWith("ZAM-")) {
      setResult({
        commodity: "Amoxicillin 250mg Capsules",
        lotNumber: "LOT-AMX-2024-0847",
        manufacturer: "Zambia Pharma Ltd.",
        expiryDate: "2026-03-15",
        description: "Broad-spectrum antibiotic, 100 capsules per bottle",
        verifiedAt: new Date().toISOString(),
        ledgerEntry: "0x8f3a...7b2d",
        status: "authentic",
      });
    } else if (searchCode.startsWith("FLAGGED-")) {
      setResult({
        commodity: "Unknown Product",
        lotNumber: "N/A",
        manufacturer: "Unknown",
        expiryDate: "N/A",
        description: "This product has been flagged in the ZAMMSA Ledger",
        verifiedAt: new Date().toISOString(),
        ledgerEntry: "0x9a2c...1e4f",
        status: "flagged",
      });
    } else {
      setResult({
        commodity: "Not Found",
        lotNumber: "N/A",
        manufacturer: "N/A",
        expiryDate: "N/A",
        description: "No record found in the ZAMMSA Ledger",
        verifiedAt: new Date().toISOString(),
        ledgerEntry: "N/A",
        status: "not_found",
      });
    }

    setIsVerifying(false);
  };

  return (
    <div className="min-h-[80vh] flex flex-col">
      {/* Page Header */}
      <div className="text-center mb-12">
        <h1 className="text-display-md text-navy-800 mb-2">
          Public Medicine Verification
        </h1>
        <p className="text-sm text-navy-500 max-w-lg mx-auto">
          Verify the authenticity of your medical commodities against the ZAMMSA
          Secure Ledger. Enter the serial number found on your medicine
          packaging.
        </p>
      </div>

      {/* Search Form */}
      <div className="max-w-xl mx-auto w-full mb-12">
        <form onSubmit={handleVerify} className="flex gap-3">
          <input
            type="text"
            value={searchCode}
            onChange={(e) => setSearchCode(e.target.value)}
            className="input-clinical flex-1 font-mono text-lg"
            placeholder="Enter serial number (e.g., ZAM-2847-AMX-0847)"
            disabled={isVerifying}
          />
          <button
            type="submit"
            className="btn-primary flex items-center gap-2"
            disabled={isVerifying || !searchCode.trim()}
          >
            {isVerifying ? (
              <>
                <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                    fill="none"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"
                  />
                </svg>
                Verifying...
              </>
            ) : (
              "Verify"
            )}
          </button>
        </form>
      </div>

      {/* Verification Result */}
      {result && (
        <div className="max-w-xl mx-auto w-full">
          {result.status === "authentic" && (
            <div className="certificate-container">
              <div className="text-center mb-8">
                <div className="w-16 h-16 mx-auto mb-4 bg-emerald-50 rounded-full flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-status-verified"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M5 13l4 4L19 7"
                    />
                  </svg>
                </div>
                <h2 className="text-display-sm text-navy-800 mb-1">
                  Medicine Verified
                </h2>
                <p className="text-sm text-navy-500">
                  This product is authentic and registered on the ZAMMSA Secure
                  Ledger
                </p>
              </div>

              <div className="grid grid-cols-2 gap-4 mb-8">
                {[
                  { label: "Product", value: result.commodity },
                  { label: "Lot Number", value: result.lotNumber, mono: true },
                  { label: "Manufacturer", value: result.manufacturer },
                  { label: "Expiry Date", value: result.expiryDate },
                ].map((field) => (
                  <div key={field.label}>
                    <p className="text-xs text-navy-400 mb-0.5">
                      {field.label}
                    </p>
                    <p
                      className={`text-sm font-medium text-navy-800 ${field.mono ? "font-mono" : ""}`}
                    >
                      {field.value}
                    </p>
                  </div>
                ))}
              </div>

              <div className="bg-clinical-100 rounded-medical p-4 space-y-2">
                <div className="flex justify-between text-xs">
                  <span className="text-navy-400">Ledger Entry</span>
                  <span className="font-mono text-navy-600">
                    {result.ledgerEntry}
                  </span>
                </div>
                <div className="flex justify-between text-xs">
                  <span className="text-navy-400">Verified At</span>
                  <span className="text-navy-600">
                    {new Date(result.verifiedAt).toLocaleString()}
                  </span>
                </div>
              </div>

              <div className="mt-6 text-center">
                <p className="text-xs text-navy-400">
                  Secured by ZAMMSA Distributed Ledger Technology · ProcBlock
                </p>
              </div>
            </div>
          )}

          {result.status === "flagged" && (
            <div className="clinical-card border-l-4 border-l-status-critical bg-red-50/50">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-red-50 rounded-full flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-status-critical"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z"
                    />
                  </svg>
                </div>
                <h2 className="text-display-sm text-status-critical mb-1">
                  Product Flagged
                </h2>
                <p className="text-sm text-navy-600 mb-4">
                  This product has been flagged in the ZAMMSA Ledger. Do not
                  use.
                </p>
                <div className="bg-white rounded-medical p-4 text-left">
                  <p className="text-sm font-medium text-navy-800">
                    What to do:
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-navy-600">
                    <li>• Do not consume or use this product</li>
                    <li>• Contact ZAMMSA immediately: +260 211 123 456</li>
                    <li>• Report via WhatsApp: +260 977 123 456</li>
                    <li>• Retain packaging for investigation</li>
                  </ul>
                </div>
              </div>
            </div>
          )}

          {result.status === "not_found" && (
            <div className="clinical-card border-l-4 border-l-status-warning bg-amber-50/50">
              <div className="text-center">
                <div className="w-16 h-16 mx-auto mb-4 bg-amber-50 rounded-full flex items-center justify-center">
                  <svg
                    className="w-8 h-8 text-status-warning"
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={2}
                      d="M8.228 9c.549-1.165 2.03-2 3.772-2 2.21 0 4 1.343 4 3 0 1.4-1.278 2.575-3.006 2.907-.542.104-.994.54-.994 1.093m0 3h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"
                    />
                  </svg>
                </div>
                <h2 className="text-display-sm text-navy-800 mb-1">
                  Product Not Found
                </h2>
                <p className="text-sm text-navy-600 mb-4">
                  This serial number was not found in the ZAMMSA Ledger.
                </p>
                <div className="bg-white rounded-medical p-4 text-left">
                  <p className="text-sm font-medium text-navy-800">
                    Possible reasons:
                  </p>
                  <ul className="mt-2 space-y-1 text-sm text-navy-600">
                    <li>• Incorrect serial number entered</li>
                    <li>• Product not yet registered in the system</li>
                    <li>• Counterfeit or unauthorized product</li>
                  </ul>
                </div>
                <button
                  onClick={() => {
                    setResult(null);
                    setSearchCode("");
                  }}
                  className="btn-secondary mt-6"
                >
                  Try Another Code
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Trust Banner */}
      {!result && (
        <div className="max-w-xl mx-auto w-full mt-8 clinical-card text-center">
          <div className="flex items-center justify-center gap-2 mb-2">
            <span className="w-2 h-2 rounded-full bg-status-verified" />
            <span className="text-xs font-medium text-navy-600">
              ZAMMSA Ledger Online
            </span>
          </div>
          <p className="text-xs text-navy-400">
            Every verification is checked against the immutable distributed
            ledger. Results are tamper-proof and cannot be falsified.
          </p>
        </div>
      )}
    </div>
  );
}
