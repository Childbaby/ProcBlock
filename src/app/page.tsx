import Link from 'next/link'

export default function LandingPage() {
  return (
    <div className="min-h-[80vh] flex flex-col items-center justify-center text-center px-4">
      <div className="max-w-3xl mx-auto mb-16">
        <div className="mb-6">
          <span className="inline-flex items-center gap-2 px-4 py-2 rounded-pill bg-teal-light text-teal-dark text-sm font-medium mb-8">
            <span className="w-2 h-2 rounded-full bg-teal-medical animate-pulse-status" />
            ZAMMSA Network Online
          </span>
        </div>

        <h1 className="text-display-lg text-navy-800 mb-6 text-balance">
          ProcBlock Medical Supply Chain Portal
        </h1>

        <p className="text-lg text-navy-500 mb-10 max-w-2xl mx-auto text-balance">
          A decentralized, high-integrity logistics system for the Zambia Medicines 
          and Medical Supplies Agency. Tracking medical commodities with immutable 
          digital twins from central hub to local clinic.
        </p>

        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <Link href="/login" className="btn-primary text-center">
            Access Portal
          </Link>
          <Link href="/verify" className="btn-secondary text-center">
            Verify Medicine
          </Link>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 w-full max-w-5xl">
        {[
          {
            icon: '🔒',
            title: 'Immutability',
            description: 'Every transaction recorded on the ZAMMSA Ledger cannot be altered retroactively.',
          },
          {
            icon: '⚡',
            title: 'Efficiency',
            description: 'DataMatrix field scanning for instant supply registration without manual entry.',
          },
          {
            icon: '👁️',
            title: 'Transparency',
            description: 'Full network status and supply flow visibility for administrators and citizens.',
          },
        ].map((feature) => (
          <div key={feature.title} className="clinical-card-hover text-center">
            <div className="text-3xl mb-3">{feature.icon}</div>
            <h3 className="text-lg font-semibold text-navy-800 mb-2">
              {feature.title}
            </h3>
            <p className="text-sm text-navy-500">
              {feature.description}
            </p>
          </div>
        ))}
      </div>

      <div className="mt-16 clinical-card w-full max-w-5xl">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6 text-center">
          {[
            { label: 'Ledger Uptime', value: '99.98%' },
            { label: 'Active Hubs', value: '7' },
            { label: 'Shipments Today', value: '847' },
            { label: 'Verifications', value: '3,421' },
          ].map((stat) => (
            <div key={stat.label}>
              <p className="text-display-sm text-navy-800">{stat.value}</p>
              <p className="text-xs text-navy-400 mt-1">{stat.label}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  )
}
