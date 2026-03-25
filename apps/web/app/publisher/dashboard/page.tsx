'use client'

import dynamic from 'next/dynamic'
import { useEffect, useState } from 'react'
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Legend,
} from 'recharts'
import {
  Eye, ShoppingBag, Users, TrendingUp, DollarSign,
  AlertCircle, Loader2, BookOpen, ArrowUpRight,
} from 'lucide-react'

// Load world map client-side only (uses browser APIs)
const WorldMap = dynamic(() => import('@/components/WorldMap'), { ssr: false })

// ── Types ─────────────────────────────────────────────────────────────────────

type Summary = {
  total_views: number
  total_orders: number
  active_retailers: number
  engagement_rate: number
  total_order_value_gbp: number
}

type DayPoint = { date: string; views: number; orders: number }
type TopTitle = { isbn13: string; title: string; views: number; unique_retailers: number }
type Genre    = { genre: string; title_count: number; views: number }
type Country  = { country_code: string; order_count: number; retailer_count: number }

type DashData = {
  period_days: number
  summary: Summary
  daily_trend: DayPoint[]
  top_titles: TopTitle[]
  genre_breakdown: Genre[]
  retailer_countries: Country[]
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmt(n: number) {
  return n >= 1000 ? `${(n / 1000).toFixed(1)}k` : String(n)
}

function StatCard({
  label, value, sub, icon: Icon, accent = 'amber',
}: {
  label: string; value: string | number; sub?: string
  icon: React.ElementType; accent?: 'amber' | 'indigo' | 'emerald' | 'blue' | 'rose'
}) {
  const bg: Record<string, string> = {
    amber:   'bg-amber-50 text-amber-600',
    indigo:  'bg-indigo-50 text-indigo-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    blue:    'bg-blue-50 text-blue-600',
    rose:    'bg-rose-50 text-rose-600',
  }
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-5">
      <div className="flex items-center gap-3 mb-3">
        <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${bg[accent]}`}>
          <Icon size={16} />
        </div>
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">{label}</p>
      </div>
      <p className="text-2xl font-bold text-slate-900">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  )
}

// ── Empty state ───────────────────────────────────────────────────────────────

function EmptyPanel({ message }: { message: string }) {
  return (
    <div className="flex flex-col items-center justify-center py-12 text-center">
      <BookOpen size={28} className="text-slate-200 mb-3" />
      <p className="text-sm text-slate-400">{message}</p>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function PublisherDashboard() {
  const [data, setData] = useState<DashData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [days, setDays] = useState(30)

  const load = async (period: number) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/analytics/publisher?days=${period}`)
      const json = await res.json()
      if (!res.ok) throw new Error(json.error ?? 'Failed to load')
      setData(json)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load dashboard')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load(days) }, [days])

  if (loading) return (
    <div className="flex justify-center py-24">
      <Loader2 className="animate-spin text-slate-400" size={24} />
    </div>
  )

  if (error) return (
    <div className="max-w-5xl mx-auto px-4 py-16">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm flex items-center gap-2">
        <AlertCircle size={14} /> {error}
      </div>
    </div>
  )

  const s = data!.summary

  // Format trend dates to short labels
  const trendData = data!.daily_trend.map(d => ({
    ...d,
    label: new Date(d.date).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' }),
  }))

  // Top 8 genres for bar chart
  const genreData = data!.genre_breakdown.slice(0, 8).map(g => ({
    genre: g.genre.length > 20 ? g.genre.slice(0, 18) + '…' : g.genre,
    views: g.views,
    titles: g.title_count,
  }))

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-10">

      {/* Header */}
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Publisher Dashboard</h1>
          <p className="text-sm text-slate-500 mt-1">
            Performance overview across the Metabookly retailer network
          </p>
        </div>
        <select
          value={days}
          onChange={e => setDays(Number(e.target.value))}
          className="px-3 py-1.5 border border-slate-300 rounded-md text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
        >
          <option value={7}>Last 7 days</option>
          <option value={30}>Last 30 days</option>
          <option value={90}>Last 90 days</option>
          <option value={365}>Last 12 months</option>
        </select>
      </div>

      {/* Summary stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-4 mb-8">
        <StatCard label="Title Views"      value={fmt(s.total_views)}          sub={`Last ${days} days`}             icon={Eye}          accent="blue"    />
        <StatCard label="Orders Placed"    value={fmt(s.total_orders)}          sub="On your titles"                  icon={ShoppingBag}  accent="indigo"  />
        <StatCard label="Active Retailers" value={s.active_retailers}           sub="Ordered from you"                icon={Users}        accent="emerald" />
        <StatCard label="Engagement Rate"  value={`${s.engagement_rate}%`}      sub="Views → orders"                  icon={TrendingUp}   accent="amber"   />
        <StatCard label="Order Value"      value={`£${s.total_order_value_gbp.toFixed(0)}`} sub="Trade price total"   icon={DollarSign}   accent="rose"    />
      </div>

      {/* Sales trend chart */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6">
        <h2 className="text-sm font-semibold text-slate-900 mb-6">Views &amp; Orders Over Time</h2>
        {trendData.length === 0 ? (
          <EmptyPanel message="No activity yet in this period" />
        ) : (
          <ResponsiveContainer width="100%" height={220}>
            <LineChart data={trendData} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
              <XAxis
                dataKey="label"
                tick={{ fontSize: 11, fill: '#94a3b8' }}
                tickLine={false}
                interval="preserveStartEnd"
              />
              <YAxis tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
              <Tooltip
                contentStyle={{ border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12 }}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Line
                type="monotone" dataKey="views" name="Views"
                stroke="#3b82f6" strokeWidth={2} dot={false} activeDot={{ r: 4 }}
              />
              <Line
                type="monotone" dataKey="orders" name="Orders"
                stroke="#f59e0b" strokeWidth={2} dot={false} activeDot={{ r: 4 }}
              />
            </LineChart>
          </ResponsiveContainer>
        )}
      </div>

      {/* World map + genre chart */}
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-6 mb-6">

        {/* World map — 3 cols */}
        <div className="lg:col-span-3 bg-white border border-slate-200 rounded-xl p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-sm font-semibold text-slate-900">Retailer Locations</h2>
            {data!.retailer_countries.length > 0 && (
              <span className="text-xs text-slate-400">
                {data!.retailer_countries.length} {data!.retailer_countries.length === 1 ? 'country' : 'countries'}
              </span>
            )}
          </div>
          {data!.retailer_countries.length === 0 ? (
            <EmptyPanel message="No order data yet — map will populate as retailers order" />
          ) : (
            <WorldMap data={data!.retailer_countries} />
          )}
        </div>

        {/* Genre breakdown — 2 cols */}
        <div className="lg:col-span-2 bg-white border border-slate-200 rounded-xl p-6">
          <h2 className="text-sm font-semibold text-slate-900 mb-6">Top Genres by Views</h2>
          {genreData.length === 0 ? (
            <EmptyPanel message="No genre data yet" />
          ) : (
            <ResponsiveContainer width="100%" height={280}>
              <BarChart
                data={genreData}
                layout="vertical"
                margin={{ top: 0, right: 8, bottom: 0, left: 0 }}
              >
                <CartesianGrid strokeDasharray="3 3" horizontal={false} stroke="#f1f5f9" />
                <XAxis type="number" tick={{ fontSize: 11, fill: '#94a3b8' }} tickLine={false} axisLine={false} />
                <YAxis
                  dataKey="genre" type="category"
                  tick={{ fontSize: 11, fill: '#64748b' }} tickLine={false} width={100}
                />
                <Tooltip
                  contentStyle={{ border: '1px solid #e2e8f0', borderRadius: 8, fontSize: 12 }}
                />
                <Bar dataKey="views" name="Views" fill="#f59e0b" radius={[0, 4, 4, 0]} />
              </BarChart>
            </ResponsiveContainer>
          )}
        </div>
      </div>

      {/* Top titles table */}
      <div className="bg-white border border-slate-200 rounded-xl">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-900">Top Performing Titles</h2>
          <span className="text-xs text-slate-400">Ranked by retailer views</span>
        </div>
        {data!.top_titles.length === 0 ? (
          <div className="px-6 py-10">
            <EmptyPanel message="No title views recorded yet in this period" />
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {/* Header row */}
            <div className="grid grid-cols-12 px-6 py-2 text-xs font-medium text-slate-400 uppercase tracking-wider">
              <div className="col-span-1">#</div>
              <div className="col-span-6">Title</div>
              <div className="col-span-2 text-right">Views</div>
              <div className="col-span-2 text-right">Retailers</div>
              <div className="col-span-1" />
            </div>
            {data!.top_titles.map((t, i) => (
              <div key={t.isbn13} className="grid grid-cols-12 px-6 py-3 items-center hover:bg-slate-50 transition-colors">
                <div className="col-span-1 text-sm font-bold text-slate-300">{i + 1}</div>
                <div className="col-span-6 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{t.title}</p>
                  <p className="text-xs text-slate-400 font-mono">{t.isbn13}</p>
                </div>
                <div className="col-span-2 text-right">
                  <span className="text-sm font-semibold text-slate-700">{fmt(t.views)}</span>
                </div>
                <div className="col-span-2 text-right">
                  <span className="text-sm text-slate-500">{t.unique_retailers}</span>
                </div>
                <div className="col-span-1 flex justify-end">
                  <a
                    href={`/books/${t.isbn13}`}
                    className="text-slate-300 hover:text-amber-500 transition-colors"
                    target="_blank"
                    rel="noreferrer"
                  >
                    <ArrowUpRight size={14} />
                  </a>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
