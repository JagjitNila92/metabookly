'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ClipboardList, ChevronRight, AlertCircle, Package } from 'lucide-react'
import { getOrders } from '@/lib/api'
import type { OrderSummary, OrdersPage } from '@/lib/types'
import { cn } from '@/lib/utils'

const STATUS_STYLES: Record<string, string> = {
  draft:                'bg-slate-100 text-slate-600',
  pending_transmission: 'bg-amber-100 text-amber-700',
  submitted:            'bg-blue-100 text-blue-700',
  acknowledged:         'bg-blue-100 text-blue-700',
  partially_despatched: 'bg-indigo-100 text-indigo-700',
  fully_despatched:     'bg-indigo-100 text-indigo-700',
  invoiced:             'bg-purple-100 text-purple-700',
  completed:            'bg-green-100 text-green-700',
  transmission_failed:  'bg-red-100 text-red-600',
  cancelled:            'bg-slate-100 text-slate-400 line-through',
}

function fmt(val: string | null) {
  if (!val) return '—'
  return `£${parseFloat(val).toFixed(2)}`
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function StatusBadge({ status }: { status: string }) {
  const cls = STATUS_STYLES[status] ?? 'bg-slate-100 text-slate-600'
  const label = status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())
  return <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium', cls)}>{label}</span>
}

export default function OrdersPage() {
  const [data, setData] = useState<OrdersPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [statusFilter, setStatusFilter] = useState('')

  useEffect(() => {
    setLoading(true)
    getOrders(statusFilter ? { status: statusFilter } : undefined)
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [statusFilter])

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <ClipboardList size={24} className="text-amber-500" />
          Orders
        </h1>
        <Link
          href="/orders/backorders"
          className="flex items-center gap-1.5 text-sm text-amber-600 hover:text-amber-700 font-medium"
        >
          <Package size={14} /> Back-orders
        </Link>
      </div>

      {/* Status filter */}
      <div className="flex gap-2 flex-wrap mb-6">
        {['', 'submitted', 'acknowledged', 'partially_despatched', 'fully_despatched', 'invoiced', 'transmission_failed'].map(s => (
          <button
            key={s}
            onClick={() => setStatusFilter(s)}
            className={cn(
              'px-3 py-1 rounded-full text-xs font-medium border transition-colors',
              statusFilter === s
                ? 'bg-amber-500 text-white border-amber-500'
                : 'border-slate-200 text-slate-600 hover:border-slate-300 bg-white',
            )}
          >
            {s === '' ? 'All' : s.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
          </button>
        ))}
      </div>

      {loading && (
        <div className="flex justify-center py-16">
          <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500" />
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 text-red-600 py-8">
          <AlertCircle size={18} /> {error}
        </div>
      )}

      {!loading && !error && data?.orders.length === 0 && (
        <div className="text-center py-16 text-slate-400">
          <ClipboardList size={40} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">No orders yet.</p>
          <Link href="/catalog" className="mt-3 inline-block text-sm text-amber-600 hover:text-amber-700">
            Browse catalog →
          </Link>
        </div>
      )}

      {!loading && data && data.orders.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-slate-500">PO Number</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500">Status</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500 hidden sm:table-cell">Lines</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500 hidden sm:table-cell">Total</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500 hidden md:table-cell">Submitted</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.orders.map((order: OrderSummary) => (
                <tr key={order.id} className="hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <Link href={`/orders/${order.id}`} className="font-mono text-sm font-medium text-slate-900 hover:text-amber-600">
                      {order.po_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3"><StatusBadge status={order.status} /></td>
                  <td className="px-4 py-3 text-slate-500 hidden sm:table-cell">{order.total_lines ?? '—'}</td>
                  <td className="px-4 py-3 font-medium text-slate-900 hidden sm:table-cell">{fmt(order.total_gbp)}</td>
                  <td className="px-4 py-3 text-slate-500 hidden md:table-cell">{fmtDate(order.submitted_at)}</td>
                  <td className="px-4 py-3 text-right">
                    <Link href={`/orders/${order.id}`} className="text-slate-400 hover:text-amber-600">
                      <ChevronRight size={16} />
                    </Link>
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
