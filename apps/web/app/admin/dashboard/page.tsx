'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Users, BookOpen, ShoppingBag, TrendingUp, AlertCircle, Loader2, ArrowRight } from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type PlanCounts = { free: number; starter_api: number; intelligence: number; enterprise: number }
type Stats = {
  total_retailers: number
  retailers_by_plan: PlanCounts
  new_retailers_7d: number
  total_titles: number
  total_orders: number
}

// ── Helpers ───────────────────────────────────────────────────────────────────

const PLAN_LABELS: Record<string, string> = {
  free: 'Free',
  starter_api: 'Starter API',
  intelligence: 'Intelligence',
  enterprise: 'Enterprise',
}

const PLAN_COLORS: Record<string, string> = {
  free:          'bg-slate-100 text-slate-600',
  starter_api:   'bg-blue-100 text-blue-700',
  intelligence:  'bg-violet-100 text-violet-700',
  enterprise:    'bg-amber-100 text-amber-700',
}

function StatCard({
  label, value, sub, icon: Icon, accent = 'slate',
}: {
  label: string; value: string | number; sub?: string
  icon: React.ElementType; accent?: 'slate' | 'blue' | 'emerald' | 'violet' | 'amber'
}) {
  const bg: Record<string, string> = {
    slate:   'bg-slate-100 text-slate-600',
    blue:    'bg-blue-50 text-blue-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    violet:  'bg-violet-50 text-violet-600',
    amber:   'bg-amber-50 text-amber-600',
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

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminDashboard() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/admin/stats')
      .then(r => r.json())
      .then(d => { setStats(d); setLoading(false) })
      .catch(() => { setError('Failed to load stats'); setLoading(false) })
  }, [])

  if (loading) return (
    <div className="flex justify-center py-24">
      <Loader2 className="animate-spin text-slate-400" size={24} />
    </div>
  )

  if (error || !stats) return (
    <div className="max-w-5xl mx-auto px-6 py-16">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm flex items-center gap-2">
        <AlertCircle size={14} /> {error ?? 'Unknown error'}
      </div>
    </div>
  )

  const planEntries: [string, number][] = [
    ['free',         stats.retailers_by_plan.free],
    ['starter_api',  stats.retailers_by_plan.starter_api],
    ['intelligence', stats.retailers_by_plan.intelligence],
    ['enterprise',   stats.retailers_by_plan.enterprise],
  ]

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">

      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Admin Overview</h1>
        <p className="text-sm text-slate-500 mt-1">Platform-wide metrics</p>
      </div>

      {/* Top stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard label="Total Retailers"  value={stats.total_retailers}   sub="All accounts"          icon={Users}       accent="blue"    />
        <StatCard label="New (7 days)"     value={stats.new_retailers_7d}  sub="Recent signups"        icon={TrendingUp}  accent="emerald" />
        <StatCard label="Catalog Titles"   value={stats.total_titles.toLocaleString()} sub="Books in system" icon={BookOpen} accent="violet" />
        <StatCard label="Total Orders"     value={stats.total_orders}      sub="All time"              icon={ShoppingBag} accent="amber"   />
      </div>

      {/* Plan breakdown */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6">
        <div className="flex items-center justify-between mb-5">
          <h2 className="text-sm font-semibold text-slate-900">Retailers by Plan</h2>
          <Link
            href="/admin/retailers"
            className="flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700 font-medium"
          >
            View all <ArrowRight size={12} />
          </Link>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-4">
          {planEntries.map(([plan, count]) => (
            <div key={plan} className="text-center">
              <div className="text-3xl font-bold text-slate-900 mb-1">{count}</div>
              <span className={`inline-block px-2.5 py-0.5 rounded-full text-xs font-medium ${PLAN_COLORS[plan]}`}>
                {PLAN_LABELS[plan]}
              </span>
            </div>
          ))}
        </div>
        {/* Simple bar chart */}
        {stats.total_retailers > 0 && (
          <div className="mt-6 flex gap-1 h-2 rounded-full overflow-hidden">
            {planEntries.map(([plan, count]) => {
              const pct = (count / stats.total_retailers) * 100
              if (pct === 0) return null
              const barColors: Record<string, string> = {
                free: 'bg-slate-300', starter_api: 'bg-blue-400',
                intelligence: 'bg-violet-500', enterprise: 'bg-amber-500',
              }
              return (
                <div
                  key={plan}
                  className={`${barColors[plan]} rounded-full`}
                  style={{ width: `${pct}%` }}
                  title={`${PLAN_LABELS[plan]}: ${count}`}
                />
              )
            })}
          </div>
        )}
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <Link
          href="/admin/retailers"
          className="bg-white border border-slate-200 rounded-xl p-5 flex items-center justify-between hover:border-amber-300 hover:shadow-sm transition-all group"
        >
          <div>
            <p className="font-semibold text-slate-900 text-sm">Manage Retailers</p>
            <p className="text-xs text-slate-400 mt-0.5">Search, view, and change plan tiers</p>
          </div>
          <ArrowRight size={16} className="text-slate-300 group-hover:text-amber-500 transition-colors" />
        </Link>
        <Link
          href="/admin/flags"
          className="bg-white border border-slate-200 rounded-xl p-5 flex items-center justify-between hover:border-amber-300 hover:shadow-sm transition-all group"
        >
          <div>
            <p className="font-semibold text-slate-900 text-sm">Feature Flags</p>
            <p className="text-xs text-slate-400 mt-0.5">Toggle global features for all users</p>
          </div>
          <ArrowRight size={16} className="text-slate-300 group-hover:text-amber-500 transition-colors" />
        </Link>
      </div>

    </div>
  )
}
