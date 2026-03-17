'use client'

import { useSession, signIn } from 'next-auth/react'
import { useEffect, useState } from 'react'
import { Package, Clock, AlertCircle, LogIn, TrendingDown } from 'lucide-react'

interface DistributorPrice {
  distributor_code: string
  distributor_name: string
  available: boolean
  stock_quantity: number | null
  price_gbp: number | null
  discount_percent: number | null
  lead_time_days: number | null
  error: string | null
}

interface PricingPanelProps {
  isbn13: string
  rrpGbp: string | null
}

export function PricingPanel({ isbn13, rrpGbp }: PricingPanelProps) {
  const { data: session, status } = useSession()
  const [distributors, setDistributors] = useState<DistributorPrice[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!session) return
    setLoading(true)
    setError(null)
    fetch(`/api/pricing/${isbn13}`)
      .then((r) => {
        if (!r.ok) throw new Error(`${r.status}`)
        return r.json()
      })
      .then((d) => setDistributors(d.distributors ?? []))
      .catch(() => setError('Could not load pricing. Please try again.'))
      .finally(() => setLoading(false))
  }, [isbn13, session])

  if (status === 'loading') return null

  if (!session) {
    return (
      <div className="mt-4 rounded-lg border border-slate-200 bg-slate-50 p-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Trade Pricing
        </p>
        <p className="text-sm text-slate-500 mb-3">
          Sign in to see your live trade price and stock availability from your distributor accounts.
        </p>
        <button
          onClick={() => signIn()}
          className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-700 bg-amber-100 hover:bg-amber-200 px-3 py-1.5 rounded transition-colors"
        >
          <LogIn size={14} /> Sign in to view pricing
        </button>
      </div>
    )
  }

  return (
    <div className="mt-4 rounded-lg border border-green-200 bg-green-50 p-4">
      <p className="text-xs font-semibold text-green-700 uppercase tracking-wide mb-3">
        Your Trade Price
      </p>

      {loading && (
        <div className="space-y-3">
          {[1, 2].map((i) => (
            <div key={i} className="h-14 rounded-lg bg-green-100 animate-pulse" />
          ))}
        </div>
      )}

      {error && (
        <p className="text-sm text-red-500 flex items-center gap-1.5">
          <AlertCircle size={13} /> {error}
        </p>
      )}

      {distributors && distributors.length === 0 && (
        <p className="text-sm text-slate-500">No distributor accounts configured for your account.</p>
      )}

      {distributors &&
        distributors.map((dist) => (
          <div
            key={dist.distributor_code}
            className="mb-3 last:mb-0 bg-white rounded-lg border border-green-100 p-3"
          >
            <p className="text-[11px] text-slate-400 uppercase tracking-wide mb-2">
              {dist.distributor_name}
            </p>

            {dist.error ? (
              <p className="text-xs text-red-500 flex items-center gap-1">
                <AlertCircle size={12} /> {dist.error}
              </p>
            ) : dist.available ? (
              <div className="flex flex-wrap items-center gap-4">
                <div>
                  <span className="text-2xl font-bold text-slate-900">
                    £{dist.price_gbp?.toFixed(2)}
                  </span>
                  {dist.discount_percent != null && rrpGbp && (
                    <span className="ml-2 inline-flex items-center gap-0.5 text-xs text-green-700 font-semibold">
                      <TrendingDown size={11} />
                      {dist.discount_percent.toFixed(0)}% off RRP
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-3 text-xs text-slate-500">
                  {dist.stock_quantity != null && (
                    <span className="flex items-center gap-1">
                      <Package size={12} /> {dist.stock_quantity} in stock
                    </span>
                  )}
                  {dist.lead_time_days != null && (
                    <span className="flex items-center gap-1">
                      <Clock size={12} /> {dist.lead_time_days}d delivery
                    </span>
                  )}
                </div>
              </div>
            ) : (
              <span className="inline-flex items-center gap-1 text-xs text-red-500 font-medium">
                <AlertCircle size={12} /> Out of stock
              </span>
            )}
          </div>
        ))}
    </div>
  )
}
