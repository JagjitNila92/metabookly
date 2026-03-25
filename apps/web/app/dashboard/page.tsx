'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import {
  ShoppingBag, ShoppingCart, Package, TrendingUp, AlertCircle,
  Loader2, ArrowRight, CheckCircle, Clock, XCircle, Building2,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type OrderSummary = {
  id: string
  po_number: string
  status: string
  total_lines: number
  total_gbp: string | null
  submitted_at: string | null
  created_at: string
}

type RetailerProfile = {
  company_name: string
  email: string
  distributor_accounts: { distributor_code: string; status: string }[]
}

type BasketData = { items: { isbn13: string }[] }

// ── Helpers ───────────────────────────────────────────────────────────────────

const STATUS_META: Record<string, { label: string; color: string; icon: React.ElementType }> = {
  draft:                 { label: 'Draft',            color: 'text-slate-400',  icon: Clock },
  pending_transmission:  { label: 'Sending…',         color: 'text-amber-500',  icon: Clock },
  submitted:             { label: 'Submitted',         color: 'text-blue-500',   icon: Clock },
  acknowledged:          { label: 'Acknowledged',      color: 'text-blue-600',   icon: CheckCircle },
  partially_despatched:  { label: 'Part despatched',   color: 'text-indigo-500', icon: Package },
  fully_despatched:      { label: 'Despatched',        color: 'text-indigo-600', icon: Package },
  invoiced:              { label: 'Invoiced',          color: 'text-emerald-500',icon: CheckCircle },
  completed:             { label: 'Completed',         color: 'text-emerald-600',icon: CheckCircle },
  transmission_failed:   { label: 'Failed',            color: 'text-red-500',    icon: XCircle },
  cancelled:             { label: 'Cancelled',         color: 'text-slate-400',  icon: XCircle },
}

function StatusBadge({ status }: { status: string }) {
  const meta = STATUS_META[status] ?? { label: status, color: 'text-slate-500', icon: Clock }
  const Icon = meta.icon
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium ${meta.color}`}>
      <Icon size={11} />
      {meta.label}
    </span>
  )
}

function StatCard({
  label, value, sub, icon: Icon, href, accent = 'amber',
}: {
  label: string; value: string | number; sub?: string
  icon: React.ElementType; href?: string; accent?: 'amber' | 'indigo' | 'emerald' | 'blue'
}) {
  const bg: Record<string, string> = {
    amber: 'bg-amber-50 text-amber-600',
    indigo: 'bg-indigo-50 text-indigo-600',
    emerald: 'bg-emerald-50 text-emerald-600',
    blue: 'bg-blue-50 text-blue-600',
  }
  const card = (
    <div className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md transition-shadow">
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
  return href ? <Link href={href}>{card}</Link> : card
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function RetailerDashboard() {
  const [profile, setProfile] = useState<RetailerProfile | null>(null)
  const [orders, setOrders] = useState<OrderSummary[]>([])
  const [basket, setBasket] = useState<BasketData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    async function load() {
      try {
        const [profileRes, ordersRes, basketRes] = await Promise.all([
          fetch('/api/retailer/me'),
          fetch('/api/orders?page_size=5'),
          fetch('/api/basket'),
        ])
        const [p, o, b] = await Promise.all([
          profileRes.json(), ordersRes.json(), basketRes.json(),
        ])
        if (!profileRes.ok) throw new Error(p.error ?? 'Could not load profile')
        setProfile(p)
        setOrders(o.orders ?? [])
        setBasket(b)
      } catch (e: unknown) {
        setError(e instanceof Error ? e.message : 'Failed to load dashboard')
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const approvedAccounts = profile?.distributor_accounts?.filter(a => a.status === 'approved') ?? []
  const pendingAccounts  = profile?.distributor_accounts?.filter(a => a.status === 'pending') ?? []
  const basketCount = basket?.items?.length ?? 0

  const activeOrders = orders.filter(o =>
    !['completed', 'cancelled'].includes(o.status)
  ).length

  if (loading) return (
    <div className="flex justify-center py-24">
      <Loader2 className="animate-spin text-slate-400" size={24} />
    </div>
  )

  if (error) return (
    <div className="max-w-3xl mx-auto px-4 py-16">
      <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm flex items-center gap-2">
        <AlertCircle size={14} /> {error}
      </div>
    </div>
  )

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">

      {/* Welcome */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">
          Welcome back{profile?.company_name ? `, ${profile.company_name}` : ''}
        </h1>
        <p className="text-sm text-slate-500 mt-1">
          Here&apos;s your trading summary for today.
        </p>
      </div>

      {/* Pending account alert */}
      {pendingAccounts.length > 0 && (
        <div className="mb-6 bg-amber-50 border border-amber-200 rounded-xl p-4 flex items-start gap-3">
          <AlertCircle size={16} className="text-amber-600 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-amber-800">
              {pendingAccounts.length} distributor account{pendingAccounts.length > 1 ? 's' : ''} awaiting approval
            </p>
            <p className="text-xs text-amber-700 mt-0.5">
              You&apos;ll receive an email once approved. Until then, trade pricing won&apos;t show for those distributors.{' '}
              <Link href="/account" className="underline">View accounts →</Link>
            </p>
          </div>
        </div>
      )}

      {/* No distributor accounts yet */}
      {approvedAccounts.length === 0 && pendingAccounts.length === 0 && (
        <div className="mb-6 bg-slate-50 border border-slate-200 rounded-xl p-4 flex items-start gap-3">
          <Building2 size={16} className="text-slate-500 shrink-0 mt-0.5" />
          <div>
            <p className="text-sm font-medium text-slate-700">No distributor accounts linked yet</p>
            <p className="text-xs text-slate-500 mt-0.5">
              Link your Gardners or Bertrams trade account to see live pricing.{' '}
              <Link href="/account" className="underline">Link an account →</Link>
            </p>
          </div>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-8">
        <StatCard
          label="Active Orders"
          value={activeOrders}
          sub="In progress"
          icon={ShoppingBag}
          href="/orders"
          accent="indigo"
        />
        <StatCard
          label="In Basket"
          value={basketCount}
          sub={basketCount === 1 ? '1 title' : `${basketCount} titles`}
          icon={ShoppingCart}
          href="/basket"
          accent="amber"
        />
        <StatCard
          label="Distributor Accounts"
          value={approvedAccounts.length}
          sub="Approved & active"
          icon={Building2}
          href="/account"
          accent="emerald"
        />
        <StatCard
          label="Total Orders"
          value={orders.length > 0 ? orders.length : '—'}
          sub="This session"
          icon={TrendingUp}
          href="/orders"
          accent="blue"
        />
      </div>

      {/* Recent orders */}
      <div className="bg-white border border-slate-200 rounded-xl mb-6">
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-100">
          <h2 className="text-sm font-semibold text-slate-900">Recent Orders</h2>
          <Link href="/orders" className="text-xs text-amber-600 hover:text-amber-700 flex items-center gap-1">
            View all <ArrowRight size={12} />
          </Link>
        </div>

        {orders.length === 0 ? (
          <div className="px-6 py-10 text-center">
            <ShoppingBag size={24} className="text-slate-200 mx-auto mb-3" />
            <p className="text-sm text-slate-400">No orders yet</p>
            <Link
              href="/catalog"
              className="mt-3 inline-flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700"
            >
              Browse the catalogue <ArrowRight size={11} />
            </Link>
          </div>
        ) : (
          <div className="divide-y divide-slate-100">
            {orders.map(order => (
              <Link
                key={order.id}
                href={`/orders/${order.id}`}
                className="flex items-center justify-between px-6 py-3 hover:bg-slate-50 transition-colors"
              >
                <div className="min-w-0">
                  <p className="text-sm font-medium text-slate-900 font-mono">{order.po_number}</p>
                  <p className="text-xs text-slate-400 mt-0.5">
                    {order.total_lines} line{order.total_lines !== 1 ? 's' : ''}
                    {order.submitted_at && (
                      <> · {new Date(order.submitted_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })}</>
                    )}
                  </p>
                </div>
                <div className="flex items-center gap-4 shrink-0 ml-4">
                  {order.total_gbp && (
                    <span className="text-sm font-semibold text-slate-700">
                      £{parseFloat(order.total_gbp).toFixed(2)}
                    </span>
                  )}
                  <StatusBadge status={order.status} />
                </div>
              </Link>
            ))}
          </div>
        )}
      </div>

      {/* Quick links */}
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
        {[
          { href: '/catalog', label: 'Browse catalogue', icon: TrendingUp },
          { href: '/basket', label: 'View basket', icon: ShoppingCart },
          { href: '/orders/backorders', label: 'Backorders', icon: Package },
          { href: '/account', label: 'Distributor accounts', icon: Building2 },
          { href: '/settings', label: 'Settings', icon: CheckCircle },
          { href: '/retailer/dashboard', label: 'My activity', icon: TrendingUp },
        ].map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-2 px-4 py-3 bg-white border border-slate-200 rounded-lg text-sm text-slate-700 hover:border-amber-300 hover:text-amber-700 transition-colors"
          >
            <Icon size={14} className="text-slate-400" />
            {label}
          </Link>
        ))}
      </div>
    </div>
  )
}
