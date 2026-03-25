'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { ArrowLeft, Package, Clock, AlertCircle } from 'lucide-react'
import { getBackorders, cancelOrderLine } from '@/lib/api'
import type { BackorderItem, BackordersPage } from '@/lib/types'

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function BackordersPage() {
  const [data, setData] = useState<BackordersPage | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState<string | null>(null)

  function load() {
    setLoading(true)
    getBackorders()
      .then(setData)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [])

  async function handleCancel(item: BackorderItem) {
    if (!confirm(`Cancel back-order for ${item.isbn13}?`)) return
    setCancelling(item.item_id)
    try {
      await cancelOrderLine(item.order_id, item.order_line_id)
      load()
    } catch { /* ignore */ } finally {
      setCancelling(null)
    }
  }

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      <div className="mb-6">
        <Link
          href="/orders"
          className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-amber-600 mb-3 transition-colors"
        >
          <ArrowLeft size={14} /> All orders
        </Link>
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <Package size={24} className="text-amber-500" />
          Back-orders
        </h1>
        <p className="text-sm text-slate-500 mt-1">All titles currently on back-order across all orders.</p>
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

      {!loading && !error && (!data || data.items.length === 0) && (
        <div className="text-center py-16 text-slate-400">
          <Package size={40} className="mx-auto mb-3 opacity-40" />
          <p className="text-sm">No active back-orders.</p>
        </div>
      )}

      {!loading && data && data.items.length > 0 && (
        <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                <th className="text-left px-4 py-3 font-medium text-slate-500">Title / ISBN</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500 hidden sm:table-cell">Distributor</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500 hidden sm:table-cell">PO</th>
                <th className="text-left px-4 py-3 font-medium text-slate-500">
                  <span className="flex items-center gap-1"><Clock size={12} /> Expected</span>
                </th>
                <th className="text-left px-4 py-3 font-medium text-slate-500 hidden md:table-cell">Qty</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.items.map((item: BackorderItem) => (
                <tr key={item.item_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900">{item.title ?? item.isbn13}</p>
                    <p className="text-xs text-slate-400">ISBN {item.isbn13}</p>
                  </td>
                  <td className="px-4 py-3 text-slate-600 hidden sm:table-cell">
                    {item.distributor_code}
                  </td>
                  <td className="px-4 py-3 hidden sm:table-cell">
                    <Link
                      href={`/orders/${item.order_id}`}
                      className="font-mono text-xs text-amber-600 hover:text-amber-700"
                    >
                      {item.po_number}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {item.expected_despatch_date ? (
                      <span className="text-amber-700">{fmtDate(item.expected_despatch_date)}</span>
                    ) : (
                      <span className="text-slate-400">Unknown</span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-600 hidden md:table-cell">{item.quantity_ordered}</td>
                  <td className="px-4 py-3 text-right">
                    <button
                      onClick={() => handleCancel(item)}
                      disabled={cancelling === item.item_id}
                      className="text-xs text-red-400 hover:text-red-600 font-medium disabled:opacity-50 transition-colors"
                    >
                      {cancelling === item.item_id ? 'Cancelling…' : 'Cancel'}
                    </button>
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
