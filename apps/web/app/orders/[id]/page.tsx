'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  ArrowLeft, Package, CheckCircle, Clock, AlertCircle,
  Truck, FileText, X, ChevronDown, ChevronUp, Zap,
} from 'lucide-react'
import { getOrder, cancelOrder, cancelOrderLine, getInvoice, advanceOrder } from '@/lib/api'
import type { Order, OrderLine, OrderLineItem, InvoiceResponse } from '@/lib/types'
import { cn } from '@/lib/utils'

const ITEM_STATUS_CONFIG: Record<string, { icon: React.ReactNode; cls: string; label: string }> = {
  pending:       { icon: <Clock size={12} />,        cls: 'bg-slate-100 text-slate-600',   label: 'Pending' },
  confirmed:     { icon: <CheckCircle size={12} />,  cls: 'bg-green-100 text-green-700',   label: 'Confirmed' },
  back_ordered:  { icon: <Clock size={12} />,        cls: 'bg-amber-100 text-amber-700',   label: 'Back-ordered' },
  despatched:    { icon: <Truck size={12} />,        cls: 'bg-indigo-100 text-indigo-700', label: 'Despatched' },
  invoiced:      { icon: <FileText size={12} />,     cls: 'bg-purple-100 text-purple-700', label: 'Invoiced' },
  cannot_supply: { icon: <X size={12} />,            cls: 'bg-red-100 text-red-600',       label: 'Cannot supply' },
  cancelled:     { icon: <X size={12} />,            cls: 'bg-slate-100 text-slate-400',   label: 'Cancelled' },
}

function fmt(val: string | null) {
  return val ? `£${parseFloat(val).toFixed(2)}` : '—'
}

function fmtDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

function StatusBadge({ status }: { status: string }) {
  const cfg = ITEM_STATUS_CONFIG[status]
  if (cfg) {
    return (
      <span className={cn('inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium', cfg.cls)}>
        {cfg.icon} {cfg.label}
      </span>
    )
  }
  return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 font-medium">
      {status.replace(/_/g, ' ')}
    </span>
  )
}

function InvoicePanel({ orderId }: { orderId: string }) {
  const [invoice, setInvoice] = useState<InvoiceResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getInvoice(orderId)
      .then(setInvoice)
      .catch(() => setInvoice(null))
      .finally(() => setLoading(false))
  }, [orderId])

  if (loading) return null
  if (!invoice) return null

  return (
    <div className="mt-4 bg-purple-50 border border-purple-200 rounded-lg p-4">
      <div className="flex items-center gap-2 mb-3">
        <FileText size={14} className="text-purple-600" />
        <span className="text-sm font-semibold text-purple-800">Invoice available</span>
      </div>
      <div className="grid grid-cols-2 gap-2 text-sm">
        <div className="text-slate-500">Invoice no.</div>
        <div className="font-mono text-slate-900">{invoice.invoice_number}</div>
        <div className="text-slate-500">Date</div>
        <div className="text-slate-900">{fmtDate(invoice.invoice_date)}</div>
        <div className="text-slate-500">Net</div>
        <div className="text-slate-900">{fmt(invoice.net_gbp)}</div>
        <div className="text-slate-500">VAT (20%)</div>
        <div className="text-slate-900">{fmt(invoice.vat_gbp)}</div>
        <div className="text-slate-500 font-semibold">Gross</div>
        <div className="font-semibold text-slate-900">{fmt(invoice.gross_gbp)}</div>
      </div>
    </div>
  )
}

function OrderLineCard({
  line,
  orderId,
  onCancel,
}: {
  line: OrderLine
  orderId: string
  onCancel: () => void
}) {
  const [expanded, setExpanded] = useState(true)
  const [cancelling, setCancelling] = useState(false)
  const canCancelLine = line.items.some(i => ['pending', 'back_ordered'].includes(i.status))

  async function handleCancelLine() {
    if (!confirm('Cancel all back-ordered items in this line?')) return
    setCancelling(true)
    try {
      await cancelOrderLine(orderId, line.id)
      onCancel()
    } catch { /* ignore */ } finally {
      setCancelling(false)
    }
  }

  return (
    <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-3 bg-slate-50 border-b border-slate-200">
        <div className="flex items-center gap-2">
          <Package size={14} className="text-slate-400" />
          <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
            {line.distributor_code}
          </span>
          <StatusBadge status={line.status} />
        </div>
        <div className="flex items-center gap-3">
          {line.subtotal_gbp && (
            <span className="text-sm font-medium text-slate-900">{fmt(line.subtotal_gbp)}</span>
          )}
          {canCancelLine && (
            <button
              onClick={handleCancelLine}
              disabled={cancelling}
              className="text-xs text-red-500 hover:text-red-600 font-medium disabled:opacity-50"
            >
              {cancelling ? 'Cancelling…' : 'Cancel line'}
            </button>
          )}
          <button onClick={() => setExpanded(e => !e)} className="text-slate-400 hover:text-slate-600">
            {expanded ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
          </button>
        </div>
      </div>

      {expanded && (
        <div>
          {line.tracking_ref && (
            <div className="px-4 py-2.5 bg-indigo-50 border-b border-indigo-100 text-xs text-indigo-700 flex items-center gap-1.5">
              <Truck size={12} /> Tracking: {line.tracking_ref}
              {line.estimated_delivery_date && ` · Est. delivery: ${fmtDate(line.estimated_delivery_date)}`}
            </div>
          )}

          <div className="divide-y divide-slate-100">
            {line.items.map((item: OrderLineItem) => (
              <div key={item.id} className="flex items-start justify-between px-4 py-3 gap-4">
                <div className="flex-1 min-w-0">
                  <p className="text-sm font-medium text-slate-900 truncate">{item.title ?? item.isbn13}</p>
                  <p className="text-xs text-slate-400">ISBN {item.isbn13}</p>
                  {item.expected_despatch_date && item.status === 'back_ordered' && (
                    <p className="text-xs text-amber-600 mt-0.5">
                      Expected: {fmtDate(item.expected_despatch_date)}
                    </p>
                  )}
                </div>
                <div className="flex items-center gap-3 flex-none text-sm">
                  <span className="text-slate-500">×{item.quantity_ordered}</span>
                  {item.trade_price_gbp && (
                    <span className="font-medium text-slate-900">{fmt(item.trade_price_gbp)}</span>
                  )}
                  <StatusBadge status={item.status} />
                </div>
              </div>
            ))}
          </div>

          {line.status === 'invoiced' && <InvoicePanel orderId={orderId} />}
        </div>
      )}
    </div>
  )
}

export default function OrderDetailPage() {
  const { id } = useParams<{ id: string }>()
  const [order, setOrder] = useState<Order | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState(false)
  const [advancing, setAdvancing] = useState(false)

  const isDev = process.env.NODE_ENV === 'development'

  function load() {
    setLoading(true)
    getOrder(id)
      .then(setOrder)
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }

  useEffect(() => { load() }, [id])

  async function handleCancelOrder() {
    if (!confirm('Cancel this entire order?')) return
    setCancelling(true)
    try {
      await cancelOrder(id)
      load()
    } catch { /* ignore */ } finally {
      setCancelling(false)
    }
  }

  async function handleAdvance() {
    setAdvancing(true)
    try {
      const updated = await advanceOrder(id)
      setOrder(updated)
    } catch { /* ignore */ } finally {
      setAdvancing(false)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500" />
      </div>
    )
  }

  if (error || !order) {
    return (
      <div className="max-w-5xl mx-auto px-4 py-12">
        <div className="flex items-center gap-2 text-red-600">
          <AlertCircle size={18} /> {error ?? 'Order not found'}
        </div>
      </div>
    )
  }

  const cancellable = ['draft', 'pending_transmission', 'submitted'].includes(order.status)

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Header */}
      <div className="flex items-start justify-between mb-6">
        <div>
          <Link
            href="/orders"
            className="inline-flex items-center gap-1 text-sm text-slate-400 hover:text-amber-600 mb-3 transition-colors"
          >
            <ArrowLeft size={14} /> All orders
          </Link>
          <h1 className="text-xl font-bold text-slate-900 font-mono">{order.po_number}</h1>
          <div className="flex items-center gap-3 mt-1.5">
            <span className={cn(
              'text-xs px-2 py-0.5 rounded-full font-medium',
              order.status === 'acknowledged' ? 'bg-blue-100 text-blue-700' :
              order.status.includes('despatched') ? 'bg-indigo-100 text-indigo-700' :
              order.status === 'invoiced' ? 'bg-purple-100 text-purple-700' :
              order.status === 'completed' ? 'bg-green-100 text-green-700' :
              order.status === 'transmission_failed' ? 'bg-red-100 text-red-600' :
              'bg-slate-100 text-slate-600',
            )}>
              {order.status.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
            </span>
            {order.submitted_at && (
              <span className="text-xs text-slate-400">Submitted {fmtDate(order.submitted_at)}</span>
            )}
            {order.total_gbp && (
              <span className="text-sm font-semibold text-slate-900">{fmt(order.total_gbp)}</span>
            )}
          </div>
        </div>

        <div className="flex items-center gap-2">
          {isDev && (
            <button
              onClick={handleAdvance}
              disabled={advancing || order.status === 'invoiced' || order.status === 'completed'}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg font-medium disabled:opacity-40 transition-colors"
            >
              <Zap size={12} /> {advancing ? 'Advancing…' : 'Advance (dev)'}
            </button>
          )}
          {cancellable && (
            <button
              onClick={handleCancelOrder}
              disabled={cancelling}
              className="px-3 py-1.5 text-xs border border-red-200 text-red-500 hover:bg-red-50 rounded-lg font-medium disabled:opacity-50 transition-colors"
            >
              {cancelling ? 'Cancelling…' : 'Cancel order'}
            </button>
          )}
        </div>
      </div>

      {/* Order lines */}
      <div className="space-y-4">
        {order.lines.map((line: OrderLine) => (
          <OrderLineCard
            key={line.id}
            line={line}
            orderId={order.id}
            onCancel={load}
          />
        ))}
      </div>
    </div>
  )
}
