'use client'

import { useEffect, useState, useCallback } from 'react'
import { Search, AlertCircle, Loader2, ChevronLeft, ChevronRight } from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type Retailer = {
  id: string
  company_name: string
  email: string
  contact_name: string | null
  plan: string
  extra_seats: number
  active: boolean
  created_at: string
}

type PageData = { items: Retailer[]; total: number; page: number; page_size: number }

const PLANS = ['free', 'starter_api', 'intelligence', 'enterprise'] as const
type Plan = typeof PLANS[number]

const PLAN_LABELS: Record<Plan, string> = {
  free: 'Free', starter_api: 'Starter API', intelligence: 'Intelligence', enterprise: 'Enterprise',
}

const PLAN_BADGE: Record<Plan, string> = {
  free:          'bg-slate-100 text-slate-600',
  starter_api:   'bg-blue-100 text-blue-700',
  intelligence:  'bg-violet-100 text-violet-700',
  enterprise:    'bg-amber-100 text-amber-700',
}

// ── Inline plan editor ────────────────────────────────────────────────────────

function PlanSelect({
  retailerId, current, onSaved,
}: { retailerId: string; current: string; onSaved: (plan: string) => void }) {
  const [value, setValue] = useState(current)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const save = async (plan: string) => {
    if (plan === current) return
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/admin/retailers/plan', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ retailer_id: retailerId, plan }),
      })
      if (!res.ok) throw new Error((await res.json()).detail ?? 'Failed')
      onSaved(plan)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error')
      setValue(current) // revert
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex items-center gap-2">
      <select
        value={value}
        disabled={saving}
        onChange={e => { setValue(e.target.value); save(e.target.value) }}
        className={`text-xs px-2 py-1 rounded-md border font-medium cursor-pointer
          focus:outline-none focus:ring-2 focus:ring-amber-400
          ${PLAN_BADGE[value as Plan] ?? 'bg-slate-100 text-slate-600'}
          ${saving ? 'opacity-50' : ''}
        `}
      >
        {PLANS.map(p => (
          <option key={p} value={p}>{PLAN_LABELS[p]}</option>
        ))}
      </select>
      {saving && <Loader2 size={12} className="animate-spin text-slate-400" />}
      {error && <span className="text-xs text-red-500">{error}</span>}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminRetailersPage() {
  const [data, setData]       = useState<PageData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)
  const [search, setSearch]   = useState('')
  const [planFilter, setPlanFilter] = useState('')
  const [page, setPage]       = useState(1)

  const load = useCallback(async (q: string, plan: string, p: number) => {
    setLoading(true)
    setError(null)
    try {
      const params = new URLSearchParams()
      if (q)    params.set('search', q)
      if (plan) params.set('plan', plan)
      params.set('page', String(p))
      params.set('page_size', '25')
      const res = await fetch(`/api/admin/retailers?${params}`)
      if (!res.ok) throw new Error('Failed to load')
      setData(await res.json())
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error')
    } finally {
      setLoading(false)
    }
  }, [])

  // Debounce search
  useEffect(() => {
    const t = setTimeout(() => { setPage(1); load(search, planFilter, 1) }, 300)
    return () => clearTimeout(t)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, planFilter])

  useEffect(() => { load(search, planFilter, page) }, [page]) // eslint-disable-line react-hooks/exhaustive-deps

  const updatePlan = (id: string, plan: string) => {
    setData(prev => prev
      ? { ...prev, items: prev.items.map(r => r.id === id ? { ...r, plan } : r) }
      : prev
    )
  }

  const totalPages = data ? Math.ceil(data.total / data.page_size) : 1

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Retailers</h1>
          {data && <p className="text-sm text-slate-500 mt-0.5">{data.total} accounts</p>}
        </div>
      </div>

      {/* Filters */}
      <div className="flex flex-wrap gap-3 mb-5">
        <div className="relative flex-1 min-w-[200px] max-w-sm">
          <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400" />
          <input
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by name or email…"
            className="w-full pl-9 pr-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400 bg-white"
          />
        </div>
        <select
          value={planFilter}
          onChange={e => { setPlanFilter(e.target.value); setPage(1) }}
          className="px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400 bg-white"
        >
          <option value="">All plans</option>
          {PLANS.map(p => <option key={p} value={p}>{PLAN_LABELS[p]}</option>)}
        </select>
      </div>

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm flex items-center gap-2 mb-4">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* Table */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        {/* Header */}
        <div className="grid grid-cols-12 px-5 py-2.5 text-xs font-medium text-slate-400 uppercase tracking-wider border-b border-slate-100 bg-slate-50">
          <div className="col-span-4">Company</div>
          <div className="col-span-3">Email</div>
          <div className="col-span-2">Contact</div>
          <div className="col-span-2">Plan</div>
          <div className="col-span-1 text-right">Joined</div>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="animate-spin text-slate-400" size={20} />
          </div>
        ) : data?.items.length === 0 ? (
          <div className="text-center py-14 text-sm text-slate-400">No retailers found</div>
        ) : (
          <div className="divide-y divide-slate-100">
            {data!.items.map(r => (
              <div key={r.id} className="grid grid-cols-12 px-5 py-3 items-center hover:bg-slate-50 transition-colors">
                <div className="col-span-4 min-w-0 pr-3">
                  <p className="text-sm font-medium text-slate-900 truncate">{r.company_name}</p>
                  {!r.active && (
                    <span className="text-[10px] font-medium text-red-500 uppercase">Inactive</span>
                  )}
                </div>
                <div className="col-span-3 min-w-0 pr-3">
                  <p className="text-sm text-slate-500 truncate">{r.email}</p>
                </div>
                <div className="col-span-2 min-w-0 pr-3">
                  <p className="text-sm text-slate-500 truncate">{r.contact_name ?? '—'}</p>
                </div>
                <div className="col-span-2">
                  <PlanSelect retailerId={r.id} current={r.plan} onSaved={plan => updatePlan(r.id, plan)} />
                </div>
                <div className="col-span-1 text-right">
                  <p className="text-xs text-slate-400">
                    {new Date(r.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' })}
                  </p>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between mt-4">
          <p className="text-xs text-slate-400">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-1">
            <button
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
              className="p-1.5 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors"
            >
              <ChevronLeft size={14} />
            </button>
            <button
              disabled={page === totalPages}
              onClick={() => setPage(p => p + 1)}
              className="p-1.5 rounded border border-slate-200 disabled:opacity-40 hover:bg-slate-50 transition-colors"
            >
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

    </div>
  )
}
