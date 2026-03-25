'use client'

import { useEffect, useState } from 'react'
import { Search, BookOpen, AlertCircle, Loader2, TrendingUp, ShoppingBag } from 'lucide-react'

type AnalyticsData = {
  period_days: number
  recent_searches: { query: string; result_count: number; searched_at: string }[]
  top_viewed_titles: { isbn13: string; title: string; views: number }[]
  price_checks: { total: number; with_gap: number }
}

function StatCard({ label, value, sub, icon: Icon }: {
  label: string; value: string | number; sub?: string; icon: React.ElementType
}) {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-amber-100 text-amber-600">
          <Icon size={16} />
        </div>
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</p>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  )
}

export default function RetailerDashboardPage() {
  const [data, setData] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  const load = async (period: number) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/analytics/retailer?days=${period}`)
      const json = await res.json()
      if (!res.ok) throw new Error(json.error ?? 'Failed to load')
      setData(json)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(days) }, [days])

  if (loading) return (
    <div className="flex justify-center py-24"><Loader2 className="animate-spin text-slate-400" size={24} /></div>
  )

  if (error) return (
    <div className="max-w-2xl mx-auto px-4 py-16">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm flex items-center gap-2">
        <AlertCircle size={14} /> {error}
      </div>
    </div>
  )

  const gapRate = data && data.price_checks.total > 0
    ? Math.round((data.price_checks.with_gap / data.price_checks.total) * 100)
    : 0

  return (
    <div className="max-w-4xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">My Activity</h1>
          <p className="text-sm text-slate-500 mt-1">Your catalogue browsing and pricing activity</p>
        </div>
        <select
          value={days}
          onChange={(e) => setDays(Number(e.target.value))}
          className="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
        </select>
      </div>

      {/* Summary stats */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4 mb-8">
        <StatCard
          label="Searches"
          value={data?.recent_searches.length ?? 0}
          sub={`Last ${days} days`}
          icon={Search}
        />
        <StatCard
          label="Price Checks"
          value={data?.price_checks.total ?? 0}
          sub={`${gapRate}% with no price returned`}
          icon={ShoppingBag}
        />
        <StatCard
          label="Titles Viewed"
          value={data?.top_viewed_titles.length ?? 0}
          sub="Unique titles"
          icon={BookOpen}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Recent searches */}
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <Search size={16} className="text-amber-500" /> Recent Searches
          </h2>
          {data?.recent_searches.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">No searches yet</p>
          ) : (
            <div className="space-y-2">
              {data?.recent_searches.map((s, i) => (
                <div key={i} className="flex items-center justify-between py-2 border-b border-slate-100 last:border-0">
                  <div className="min-w-0">
                    <p className="text-sm text-slate-900 truncate">&ldquo;{s.query}&rdquo;</p>
                    <p className="text-xs text-slate-400">
                      {new Date(s.searched_at).toLocaleDateString('en-GB', {
                        day: 'numeric', month: 'short',
                      })}
                    </p>
                  </div>
                  <span className="text-xs text-slate-500 shrink-0 ml-3">
                    {s.result_count} results
                  </span>
                </div>
              ))}
            </div>
          )}
        </div>

        {/* Most viewed titles */}
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <TrendingUp size={16} className="text-amber-500" /> Most Viewed Titles
          </h2>
          {data?.top_viewed_titles.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">No title views yet</p>
          ) : (
            <div className="space-y-2">
              {data?.top_viewed_titles.map((t, i) => (
                <div key={t.isbn13} className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
                  <span className="text-xs font-bold text-slate-300 w-5 shrink-0">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-slate-900 truncate">{t.title}</p>
                    <p className="text-xs font-mono text-slate-400">{t.isbn13}</p>
                  </div>
                  <span className="text-xs text-slate-500 shrink-0">{t.views}×</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Pricing gap alert */}
      {data && data.price_checks.with_gap > 0 && (
        <div className="mt-6 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle size={16} className="text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">
              {data.price_checks.with_gap} price {data.price_checks.with_gap === 1 ? 'check' : 'checks'} returned no pricing
            </p>
            <p className="text-xs text-amber-700 mt-0.5">
              This usually means you don&apos;t have an approved account linked with the distributor for those titles.
              Go to <a href="/account" className="underline">My Account</a> to request access.
            </p>
          </div>
        </div>
      )}
    </div>
  )
}
