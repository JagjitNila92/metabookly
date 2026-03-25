'use client'

import { useEffect, useState } from 'react'
import { BarChart2, BookOpen, Users, AlertCircle, Loader2, TrendingUp, CheckCircle2 } from 'lucide-react'

const DISTRIBUTOR_CODE = 'mock' // TODO: derive from session when distributor logins are built

type HealthData = {
  distributor_code: string
  total_titles: number
  health_score: number
  completeness: Record<string, { count: number; pct: number }>
  missing_description: { isbn13: string; title: string }[]
}

type DemandData = {
  distributor_code: string
  period_days: number
  total_retailer_views: number
  top_viewed_titles: { isbn13: string; title: string; views: number; unique_retailers: number }[]
  top_price_checked_titles: { isbn13: string; title: string; price_checks: number; unique_retailers: number }[]
}

type LeadsData = {
  distributor_code: string
  period_days: number
  leads: {
    retailer_id: string
    company_name: string
    email: string
    views: number
    unique_titles_viewed: number
    last_seen: string
  }[]
}

function StatCard({ label, value, sub, icon: Icon, color = 'amber' }: {
  label: string
  value: string | number
  sub?: string
  icon: React.ElementType
  color?: string
}) {
  const colors: Record<string, string> = {
    amber: 'bg-amber-100 text-amber-600',
    green: 'bg-green-100 text-green-600',
    blue: 'bg-blue-100 text-blue-600',
    red: 'bg-red-100 text-red-600',
  }
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${colors[color]}`}>
          <Icon size={16} />
        </div>
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</p>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  )
}

function HealthBar({ label, pct, count, total }: { label: string; pct: number; count: number; total: number }) {
  const color = pct >= 80 ? 'bg-green-500' : pct >= 50 ? 'bg-amber-400' : 'bg-red-400'
  return (
    <div>
      <div className="flex justify-between items-center mb-1">
        <span className="text-sm text-slate-700">{label}</span>
        <span className="text-sm font-medium text-slate-900">{pct}% <span className="text-slate-400 font-normal">({count}/{total})</span></span>
      </div>
      <div className="h-2 bg-slate-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full transition-all`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

export default function DistributorDashboardPage() {
  const [health, setHealth] = useState<HealthData | null>(null)
  const [demand, setDemand] = useState<DemandData | null>(null)
  const [leads, setLeads] = useState<LeadsData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  const load = async (period: number) => {
    setLoading(true)
    setError(null)
    try {
      const [h, d, l] = await Promise.all([
        fetch(`/api/analytics/distributor/health?code=${DISTRIBUTOR_CODE}`).then(r => r.json()),
        fetch(`/api/analytics/distributor/demand?code=${DISTRIBUTOR_CODE}&days=${period}`).then(r => r.json()),
        fetch(`/api/analytics/distributor/leads?code=${DISTRIBUTOR_CODE}&days=${period}`).then(r => r.json()),
      ])
      if (h.error || d.error || l.error) throw new Error(h.error ?? d.error ?? l.error)
      setHealth(h)
      setDemand(d)
      setLeads(l)
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
    <div className="max-w-4xl mx-auto px-4 py-16">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm flex items-center gap-2">
        <AlertCircle size={14} /> {error}
      </div>
    </div>
  )

  const completeness = health?.completeness ?? {}

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Distributor Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">Catalogue health and retailer demand signals</p>
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
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Titles" value={health?.total_titles ?? 0} icon={BookOpen} color="amber" />
        <StatCard label="Health Score" value={`${health?.health_score ?? 0}%`} icon={CheckCircle2} color="green" />
        <StatCard label="Retailer Views" value={demand?.total_retailer_views ?? 0} sub={`Last ${days} days`} icon={TrendingUp} color="blue" />
        <StatCard label="Warm Leads" value={leads?.leads.length ?? 0} sub="Retailers not yet linked" icon={Users} color="amber" />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-6">
        {/* Catalogue Health */}
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <BarChart2 size={16} className="text-amber-500" /> Catalogue Completeness
          </h2>
          <div className="space-y-4">
            {[
              ['Description', 'has_description'],
              ['Cover image', 'has_cover'],
              ['UK price', 'has_price'],
              ['UK rights', 'has_uk_rights'],
              ['Subjects', 'has_subjects'],
              ['Publication date', 'has_pub_date'],
            ].map(([label, key]) => (
              <HealthBar
                key={key}
                label={label}
                pct={completeness[key]?.pct ?? 0}
                count={completeness[key]?.count ?? 0}
                total={health?.total_titles ?? 0}
              />
            ))}
          </div>
          {health?.missing_description && health.missing_description.length > 0 && (
            <div className="mt-5 pt-4 border-t border-slate-100">
              <p className="text-xs font-medium text-slate-500 mb-2">Titles missing description (oldest first)</p>
              <div className="space-y-1">
                {health.missing_description.map((b) => (
                  <div key={b.isbn13} className="flex items-center gap-2">
                    <span className="text-xs font-mono text-slate-400 shrink-0">{b.isbn13}</span>
                    <span className="text-xs text-slate-700 truncate">{b.title}</span>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Warm Leads */}
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-1 flex items-center gap-2">
            <Users size={16} className="text-amber-500" /> Warm Leads
          </h2>
          <p className="text-xs text-slate-400 mb-4">Retailers browsing your catalogue with no linked account</p>
          {leads?.leads.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">No unlinked retailer activity yet</p>
          ) : (
            <div className="space-y-3">
              {leads?.leads.map((lead) => (
                <div key={lead.retailer_id} className="flex items-start justify-between py-2.5 border-b border-slate-100 last:border-0">
                  <div>
                    <p className="text-sm font-medium text-slate-900">{lead.company_name}</p>
                    <p className="text-xs text-slate-400">{lead.email}</p>
                  </div>
                  <div className="text-right shrink-0 ml-4">
                    <p className="text-sm font-semibold text-slate-900">{lead.views} views</p>
                    <p className="text-xs text-slate-400">{lead.unique_titles_viewed} titles</p>
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Demand Signal */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <TrendingUp size={16} className="text-amber-500" /> Most Viewed Titles
          </h2>
          {demand?.top_viewed_titles.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">No retailer views yet</p>
          ) : (
            <div className="space-y-2">
              {demand?.top_viewed_titles.map((t, i) => (
                <div key={t.isbn13} className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
                  <span className="text-xs font-bold text-slate-300 w-5 shrink-0">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-slate-900 truncate">{t.title}</p>
                    <p className="text-xs text-slate-400">{t.unique_retailers} retailers</p>
                  </div>
                  <span className="text-sm font-semibold text-slate-700 shrink-0">{t.views}</span>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-base font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <BookOpen size={16} className="text-amber-500" /> Most Price-Checked Titles
          </h2>
          {demand?.top_price_checked_titles.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-8">No price checks yet</p>
          ) : (
            <div className="space-y-2">
              {demand?.top_price_checked_titles.map((t, i) => (
                <div key={t.isbn13} className="flex items-center gap-3 py-2 border-b border-slate-100 last:border-0">
                  <span className="text-xs font-bold text-slate-300 w-5 shrink-0">{i + 1}</span>
                  <div className="min-w-0 flex-1">
                    <p className="text-sm text-slate-900 truncate">{t.title}</p>
                    <p className="text-xs text-slate-400">{t.unique_retailers} retailers</p>
                  </div>
                  <span className="text-sm font-semibold text-slate-700 shrink-0">{t.price_checks}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
