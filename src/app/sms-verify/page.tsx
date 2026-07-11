export default function SMSVerifyPage() {
  return (
    <div className="min-h-screen bg-clinical-100 flex items-center justify-center px-4">
      <div className="max-w-lg w-full clinical-card text-center">
        <div className="text-5xl mb-6">📱</div>
        <h1 className="text-display-sm text-navy-800 mb-4">SMS / USSD Verification</h1>
        <p className="text-navy-500 mb-8">No smartphone? No problem. Verify your medicine via text message.</p>
        <div className="bg-navy-50 rounded-medical p-6 mb-6">
          <div className="flex items-center justify-center gap-2 text-2xl font-bold text-navy-800 mb-2">
            <span className="bg-navy-800 text-white px-4 py-2 rounded-medical">*678#</span>
          </div>
          <p className="text-sm text-navy-500">Dial this code from any phone</p>
        </div>
        <div className="text-left space-y-4 mb-8">
          <div className="flex gap-3"><span className="text-emerald-500 font-bold">1.</span><p className="text-sm text-navy-700">Dial <strong>*678#</strong> on any mobile phone</p></div>
          <div className="flex gap-3"><span className="text-emerald-500 font-bold">2.</span><p className="text-sm text-navy-700">Enter the <strong>serial number</strong> from your medicine packaging</p></div>
          <div className="flex gap-3"><span className="text-emerald-500 font-bold">3.</span><p className="text-sm text-navy-700">Receive instant reply: <strong>"Verified: This batch is authentic and safe."</strong></p></div>
        </div>
        <div className="bg-amber-50 border border-amber-200 rounded-medical p-4 text-sm text-amber-800">
          <strong>Coming Soon:</strong> USSD verification for feature phones. No internet required.
        </div>
      </div>
    </div>
  )
}
