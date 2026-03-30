'use client'

import { useEffect, useState } from 'react'
import { Package, Gift, ChevronDown, ChevronUp, AlertCircle, Loader2 } from 'lucide-react'
import { cn } from '@/lib/utils'

const DISTRIBUTOR_CODE = 'mock' // TODO: derive from session when distributor logins are built

type OrderLineItem = {
  isbn13: string
  title: string | null
  quantity_ordered: number
  quantity_confirmed: number | null
  status: string
  trade_price_gbp: string | null
}

type DistributorOrder = {
  order_line_id: string
  order_id: string
  po_number: string
  order_type: string
  order_status: string
  line_status: string
  submitted_at: string | null
  retailer_company: string
  subtotal_gbp: string | null
  items: OrderLineItem[]
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function fmt(val: string | null) {
  if (val === null || val === undefined) return '—'
  return `£${parseFloat(val).toFixed(2)}`
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function OrderTypeBadge({ type }: { type: string }) {
  if (type === 'gratis') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-violet-100 text-violet-700 text-xs font-medium">
        <Gift size={10} /> Gratis
      </span>
    )
  }
  if (type === 'sample') {
    return (
      <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-blue-100 text-blue-700 text-xs font-medium">
        Sample
      </span>
    )
  }
  return null
}

function LineStatusBadge({ status }: { status: string }) {
  const map: Record<string, string> = {
    pending:       'bg-slate-100 text-slate-600',
    submitted:     'bg-amber-100 text-amber-700',
    acknowledged:  'bg-amber-100 text-amber-700',
    confirmed:     'bg-green-100 text-green-700',
    back_ordered:  'bg-orange-100 text-orange-700',
    despatched:    'bg-blue-100 text-blue-700',
    invoiced:      'bg-purple-100 text-purple-700',
    cancelled:     'bg-red-100 text-red-600',
    transmission_failed: 'bg-red-100 text-red-600',
  }
  return (
    <span className={cn('px-2 py-0.5 rounded-full text-xs font-medium capitalize', map[status] ?? 'bg-slate-100 text-slate-600')}>
      {status.replace(/_/g, ' ')}
    </span>
  )
}

// ─── Order row ────────────────────────────────────────────────────────────────

function OrderRow({ order }: { order: DistributorOrder }) {
  const [expanded, setExpanded] = useState(false)
  const isGratis = order.order_type !== 'trade'

  return (
    <div className={cn(
      'bg-white border rounded-xl overflow-hidden transition-colors',
      isGratis ? 'border-violet-200' : 'border-slate-200',
    )}>
      {/* Header row */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full text-left px-5 py-4 flex items-center gap-4 hover:bg-slate-50 transition-colors"
      >
        {/* PO + type */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-mono text-sm font-semibold text-slate-900">{order.po_number}</span>
            <OrderTypeBadge type={order.order_type} />
          </div>
          <p className="text-xs text-slate-500">{order.retailer_company}</p>
        </div>

        {/* Items count */}
        <div className="text-center hidden sm:block">
          <p className="text-sm font-semibold text-slate-900">{order.items.length}</p>
          <p className="text-xs text-slate-400">title{order.items.length !== 1 ? 's' : ''}</p>
        </div>

        {/* Subtotal */}
        <div className="text-right hidden sm:block">
          <p className={cn('text-sm font-semibold', isGratis ? 'text-violet-700' : 'text-slate-900')}>
            {isGratis ? '£0.00' : fmt(order.subtotal_gbp)}
          </p>
          <p className="text-xs text-slate-400">subtotal</p>
        </div>

        {/* Status */}
        <div className="hidden md:block">
          <LineStatusBadge status={order.line_status} />
        </div>

        {/* Date */}
        <div className="text-right shrink-0">
          <p className="text-xs text-slate-400">{fmtDate(order.submitted_at)}</p>
        </div>

        {/* Expand icon */}
        <div className="text-slate-400 shrink-0">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </div>
      </button>

      {/* Expanded items */}
      {expanded && (
        <div className={cn('border-t px-5 py-4', isGratis ? 'border-violet-100 bg-violet-50/30' : 'border-slate-100 bg-slate-50/50')}>
          {isGratis && (
            <div className="flex items-center gap-2 mb-3 text-xs text-violet-700 bg-violet-100 border border-violet-200 rounded-lg px-3 py-2">
              <Gift size={12} /> Complimentary order — no charge to retailer
            </div>
          )}
          <table className="w-full text-sm">
            <thead>
              <tr className="text-xs text-slate-400 uppercase tracking-wide border-b border-slate-200">
                <th className="text-left pb-2 font-medium">Title</th>
                <th className="text-left pb-2 font-medium">ISBN</th>
                <th className="text-right pb-2 font-medium">Qty</th>
                <th className="text-right pb-2 font-medium">Confirmed</th>
                <th className="text-right pb-2 font-medium">Price</th>
                <th className="text-right pb-2 font-medium">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {order.items.map(item => (
                <tr key={item.isbn13} className="py-2">
                  <td className="py-2 pr-4 text-slate-900 max-w-xs truncate">{item.title ?? '—'}</td>
                  <td className="py-2 pr-4 font-mono text-xs text-slate-500">{item.isbn13}</td>
                  <td className="py-2 text-right text-slate-900">{item.quantity_ordered}</td>
                  <td className="py-2 text-right text-slate-500">{item.quantity_confirmed ?? '—'}</td>
                  <td className={cn('py-2 text-right font-medium', isGratis ? 'text-violet-600' : 'text-slate-900')}>
                    {isGratis ? '£0.00' : fmt(item.trade_price_gbp)}
                  </td>
                  <td className="py-2 text-right">
                    <LineStatusBadge status={item.status} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}

// ─── Filters ──────────────────────────────────────────────────────────────────

const ORDER_TYPE_OPTIONS = [
  { value: '', label: 'All orders' },
  { value: 'trade', label: 'Trade only' },
  { value: 'gratis', label: 'Gratis only' },
]

const STATUS_OPTIONS = [
  { value: '', label: 'All statuses' },
  { value: 'submitted', label: 'Submitted' },
  { value: 'acknowledged', label: 'Acknowledged' },
  { value: 'back_ordered', label: 'Back-ordered' },
  { value: 'despatched', label: 'Despatched' },
  { value: 'invoiced', label: 'Invoiced' },
]

// ─── Main page ────────────────────────────────────────────────────────────────

export default function DistributorOrdersPage() {
  const [orders, setOrders] = useState<DistributorOrder[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [orderType, setOrderType] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [nextCursor, setNextCursor] = useState<string | null>(null)
  const [loadingMore, setLoadingMore] = useState(false)

  async function load(reset = true) {
    if (reset) setLoading(true)
    else setLoadingMore(true)
    setError(null)
    try {
      const qs = new URLSearchParams({ distributor_code: DISTRIBUTOR_CODE })
      if (orderType) qs.set('order_type', orderType)
      if (statusFilter) qs.set('status', statusFilter)
      if (!reset && nextCursor) qs.set('cursor', nextCursor)
      const res = await fetch(`/api/distributor/orders?${qs}`)
      const data = await res.json()
      if (!res.ok) throw new Error(data.error ?? 'Failed to load orders')
      setOrders(prev => reset ? data.orders : [...prev, ...data.orders])
      setNextCursor(data.next_cursor)
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to load orders')
    } finally {
      setLoading(false)
      setLoadingMore(false)
    }
  }

  useEffect(() => { load(true) }, [orderType, statusFilter])

  const gratisfCount = orders.filter(o => o.order_type === 'gratis').length
  const tradeCount = orders.filter(o => o.order_type === 'trade').length

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Package size={22} className="text-amber-500" /> Incoming Orders
        </h1>
        <p className="text-sm text-slate-500 mt-1">Orders transmitted to {DISTRIBUTOR_CODE.toUpperCase()}</p>
      </div>

      {/* Summary pills */}
      {!loading && orders.length > 0 && (
        <div className="flex gap-3 mb-6">
          <div className="px-3 py-1.5 bg-slate-100 rounded-full text-xs font-medium text-slate-700">
            {tradeCount} trade
          </div>
          {gratisfCount > 0 && (
            <div className="px-3 py-1.5 bg-violet-100 rounded-full text-xs font-medium text-violet-700 flex items-center gap-1">
              <Gift size={11} /> {gratisfCount} gratis
            </div>
          )}
        </div>
      )}

      {/* Filters */}
      <div className="flex gap-3 mb-6">
        <select
          value={orderType}
          onChange={e => setOrderType(e.target.value)}
          className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
        >
          {ORDER_TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
        <select
          value={statusFilter}
          onChange={e => setStatusFilter(e.target.value)}
          className="px-3 py-1.5 border border-slate-200 rounded-lg text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
        >
          {STATUS_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
        </select>
      </div>

      {/* Content */}
      {loading ? (
        <div className="flex justify-center py-24">
          <Loader2 className="animate-spin text-slate-400" size={24} />
        </div>
      ) : error ? (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm flex items-center gap-2">
          <AlertCircle size={14} /> {error}
        </div>
      ) : orders.length === 0 ? (
        <div className="text-center py-24 text-slate-400">
          <Package size={40} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">No orders yet for {DISTRIBUTOR_CODE.toUpperCase()}</p>
        </div>
      ) : (
        <div className="space-y-3">
          {orders.map(order => <OrderRow key={order.order_line_id} order={order} />)}
          {nextCursor && (
            <div className="text-center pt-4">
              <button
                onClick={() => load(false)}
                disabled={loadingMore}
                className="px-5 py-2 text-sm text-slate-600 border border-slate-200 rounded-lg hover:bg-slate-50 disabled:opacity-50"
              >
                {loadingMore ? 'Loading…' : 'Load more'}
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
