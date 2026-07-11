'use client'

import { Clock, User, Package, ShieldCheck, AlertTriangle } from 'lucide-react'

interface Activity {
  id: string
  type: 'minted' | 'transferred' | 'verified' | 'alerted'
  description: string
  actor: string
  timestamp: string
  transactionHash?: string
}

const activityIcon = {
  minted: Package,
  transferred: User,
  verified: ShieldCheck,
  alerted: AlertTriangle,
}

const activityColor = {
  minted: 'bg-teal-50 border-teal-200 text-teal-700',
  transferred: 'bg-sky-50 border-sky-200 text-sky-700',
  verified: 'bg-emerald-50 border-emerald-200 text-emerald-700',
  alerted: 'bg-red-50 border-red-200 text-red-700',
}

const activityLabel = {
  minted: 'cNFT Minted',
  transferred: 'Custody Transferred',
  verified: 'Authenticity Verified',
  alerted: 'Anomaly Detected',
}

export function ActivityFeed({ activities }: { activities: Activity[] }) {
  return (
    <div className="bg-clinical-50 border border-clinical-300 rounded-medical shadow-medical p-6">
      <h3 className="text-lg font-semibold text-navy-800 mb-4 flex items-center gap-2">
        <Clock size={20} className="text-teal-medical" />
        On-Chain Activity
      </h3>
      <div className="space-y-0">
        {activities.map((activity, idx) => {
          const Icon = activityIcon[activity.type]
          const colorClass = activityColor[activity.type]
          return (
            <div key={activity.id} className="flex gap-4">
              <div className="flex flex-col items-center">
                <div className={`w-8 h-8 rounded-full flex items-center justify-center border-2 ${colorClass}`}>
                  <Icon size={14} />
                </div>
                {idx < activities.length - 1 && <div className="w-0.5 h-full bg-clinical-300" />}
              </div>
              <div className={`flex-1 pb-6 ${idx === activities.length - 1 ? 'pb-0' : ''}`}>
                <div className="bg-clinical-100 border border-clinical-200 rounded-medical p-4">
                  <div className="flex items-center justify-between mb-2">
                    <span className={`text-xs font-semibold px-2 py-0.5 rounded-pill ${colorClass}`}>{activityLabel[activity.type]}</span>
                    <span className="text-xs text-navy-400">{activity.timestamp}</span>
                  </div>
                  <p className="text-sm text-navy-700">{activity.description}</p>
                  <div className="flex items-center justify-between mt-2">
                    <span className="text-xs text-navy-500 font-mono">By: {activity.actor}</span>
                    {activity.transactionHash && (
                      <a href={`https://explorer.solana.com/tx/${activity.transactionHash}?cluster=devnet`} target="_blank" className="text-xs text-teal-medical hover:underline font-mono">
                        View on Solana ↗
                      </a>
                    )}
                  </div>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}
