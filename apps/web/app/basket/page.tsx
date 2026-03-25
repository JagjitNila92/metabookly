'use client'

import { useEffect, useState } from 'react'
import Image from 'next/image'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import {
  ShoppingCart, Trash2, Plus, Minus, Package, AlertCircle,
  ChevronRight, MapPin, X, CheckCircle,
} from 'lucide-react'
import {
  getBasket, updateBasketItem, removeFromBasket, clearBasket,
  submitBasket, getAddresses,
} from '@/lib/api'
import type { BasketResponse, RoutedItem, Address, Order } from '@/lib/types'
import { cn } from '@/lib/utils'

// ─── Status helpers ───────────────────────────────────────────────────────────

function fmt(val: string | null, prefix = '£') {
  if (!val) return '—'
  return `${prefix}${parseFloat(val).toFixed(2)}`
}

function marginColor(pct: string | null) {
  if (!pct) return 'text-slate-400'
  const n = parseFloat(pct)
  if (n >= 40) return 'text-green-600'
  if (n >= 30) return 'text-amber-600'
  return 'text-red-500'
}

// ─── Submit modal ─────────────────────────────────────────────────────────────

function SubmitModal({
  addresses,
  onSubmit,
  onClose,
  submitting,
}: {
  addresses: Address[]
  onSubmit: (deliveryAddressId?: string) => void
  onClose: () => void
  submitting: boolean
}) {
  const delivery = addresses.filter(a => a.address_type === 'delivery')
  const [selected, setSelected] = useState<string | undefined>(
    delivery.find(a => a.is_default)?.id ?? delivery[0]?.id,
  )

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 px-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-md p-6">
        <div className="flex justify-between items-start mb-4">
          <h2 className="text-lg font-semibold text-slate-900">Submit order</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={20} />
          </button>
        </div>

        {delivery.length === 0 ? (
          <div className="text-sm text-slate-600 mb-4">
            <p className="mb-3">You need a delivery address before placing an order.</p>
            <Link
              href="/settings?tab=addresses"
              className="inline-flex items-center gap-1 text-amber-600 hover:text-amber-700 font-medium"
            >
              <MapPin size={14} /> Add delivery address
            </Link>
          </div>
        ) : (
          <div className="mb-5">
            <p className="text-sm text-slate-600 mb-3">Select delivery address:</p>
            <div className="space-y-2">
              {delivery.map(addr => (
                <label
                  key={addr.id}
                  className={cn(
                    'flex items-start gap-3 p-3 rounded-lg border cursor-pointer transition-colors',
                    selected === addr.id
                      ? 'border-amber-400 bg-amber-50'
                      : 'border-slate-200 hover:border-slate-300',
                  )}
                >
                  <input
                    type="radio"
                    name="delivery"
                    value={addr.id}
                    checked={selected === addr.id}
                    onChange={() => setSelected(addr.id)}
                    className="mt-0.5 accent-amber-500"
                  />
                  <div className="text-sm">
                    <div className="font-medium text-slate-900">{addr.label}</div>
                    <div className="text-slate-500">{addr.contact_name}</div>
                    <div className="text-slate-500">
                      {addr.line1}{addr.line2 ? `, ${addr.line2}` : ''}, {addr.city}, {addr.postcode}
                    </div>
                  </div>
                </label>
              ))}
            </div>
          </div>
        )}

        <div className="flex gap-3">
          <button
            onClick={onClose}
            className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            onClick={() => onSubmit(selected)}
            disabled={submitting || delivery.length === 0 || !selected}
            className="flex-1 px-4 py-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
          >
            {submitting ? 'Placing order…' : 'Place order'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Order confirmation ───────────────────────────────────────────────────────

function OrderConfirmation({ order, onDone }: { order: Order; onDone: () => void }) {
  const router = useRouter()
  const allItems = order.lines.flatMap(l => l.items)
  const confirmed = allItems.filter(i => i.status === 'confirmed').length
  const backOrdered = allItems.filter(i => i.status === 'back_ordered').length
  const cannotSupply = allItems.filter(i => i.status === 'cannot_supply').length

  return (
    <div className="max-w-2xl mx-auto px-4 py-12 text-center">
      <div className="w-16 h-16 bg-green-100 rounded-full flex items-center justify-center mx-auto mb-4">
        <CheckCircle className="text-green-600" size={32} />
      </div>
      <h1 className="text-2xl font-bold text-slate-900 mb-1">Order placed!</h1>
      <p className="text-slate-500 mb-1">PO number: <span className="font-mono font-medium text-slate-700">{order.po_number}</span></p>
      <p className="text-slate-500 mb-8 text-sm">Status: <span className="font-medium">{order.status}</span></p>

      <div className="grid grid-cols-3 gap-4 mb-8">
        {confirmed > 0 && (
          <div className="bg-green-50 border border-green-200 rounded-lg p-4">
            <div className="text-2xl font-bold text-green-700">{confirmed}</div>
            <div className="text-xs text-green-600 mt-1">Confirmed</div>
          </div>
        )}
        {backOrdered > 0 && (
          <div className="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div className="text-2xl font-bold text-amber-700">{backOrdered}</div>
            <div className="text-xs text-amber-600 mt-1">Back-ordered</div>
          </div>
        )}
        {cannotSupply > 0 && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-4">
            <div className="text-2xl font-bold text-red-700">{cannotSupply}</div>
            <div className="text-xs text-red-600 mt-1">Cannot supply</div>
          </div>
        )}
      </div>

      <div className="space-y-3 mb-8">
        {order.lines.map(line => (
          <div key={line.id} className="text-left bg-slate-50 rounded-lg p-4 border border-slate-200">
            <div className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
              {line.distributor_code}
            </div>
            {line.items.map(item => (
              <div key={item.id} className="flex items-center justify-between py-1.5 border-b border-slate-100 last:border-0">
                <div className="text-sm text-slate-700">{item.title ?? item.isbn13} × {item.quantity_ordered}</div>
                <ItemStatusBadge status={item.status} />
              </div>
            ))}
          </div>
        ))}
      </div>

      <div className="flex gap-3 justify-center">
        <button
          onClick={() => { onDone(); router.push('/catalog') }}
          className="px-5 py-2.5 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50"
        >
          Continue shopping
        </button>
        <button
          onClick={() => router.push(`/orders/${order.id}`)}
          className="px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-sm font-medium"
        >
          View order <ChevronRight size={14} className="inline" />
        </button>
      </div>
    </div>
  )
}

function ItemStatusBadge({ status }: { status: string }) {
  const map: Record<string, { label: string; cls: string }> = {
    confirmed:     { label: '✓ Confirmed',     cls: 'bg-green-100 text-green-700' },
    back_ordered:  { label: '⏳ Back-ordered',  cls: 'bg-amber-100 text-amber-700' },
    cannot_supply: { label: '✗ Cannot supply', cls: 'bg-red-100 text-red-600' },
    pending:       { label: 'Pending',          cls: 'bg-slate-100 text-slate-600' },
  }
  const s = map[status] ?? { label: status, cls: 'bg-slate-100 text-slate-600' }
  return (
    <span className={cn('text-xs px-2 py-0.5 rounded-full font-medium', s.cls)}>{s.label}</span>
  )
}

// ─── Main basket page ─────────────────────────────────────────────────────────

export default function BasketPage() {
  const [basket, setBasket] = useState<BasketResponse | null>(null)
  const [addresses, setAddresses] = useState<Address[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [showSubmit, setShowSubmit] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [confirmedOrder, setConfirmedOrder] = useState<Order | null>(null)


  useEffect(() => {
    Promise.all([getBasket(), getAddresses()])
      .then(([b, a]) => { setBasket(b); setAddresses(a) })
      .catch(e => setError(e.message))
      .finally(() => setLoading(false))
  }, [])

  async function handleQtyChange(isbn13: string, newQty: number) {
    if (newQty < 1) return handleRemove(isbn13)
    setBasket(b => b ? { ...b, items: b.items.map(i => i.isbn13 === isbn13 ? { ...i, quantity: newQty } : i) } : b)
    try {
      await updateBasketItem(isbn13, { quantity: newQty })
    } catch {
      getBasket().then(setBasket).catch(() => {})
    }
  }

  async function handleRemove(isbn13: string) {
    // Remove from UI immediately
    setBasket(b => {
      if (!b) return b
      const items = b.items.filter(i => i.isbn13 !== isbn13)
      return { ...b, items, item_count: items.length }
    })
    try {
      await removeFromBasket(isbn13)
      window.dispatchEvent(new Event('basketUpdated'))
    } catch {
      getBasket().then(b => { setBasket(b); window.dispatchEvent(new Event('basketUpdated')) }).catch(() => {})
    }
  }

  async function handleClear() {
    setBasket(b => b ? { ...b, items: [], item_count: 0, total_cost_gbp: null, avg_margin_pct: null } : b)
    try {
      await clearBasket()
      window.dispatchEvent(new Event('basketUpdated'))
    } catch {
      getBasket().then(b => { setBasket(b); window.dispatchEvent(new Event('basketUpdated')) }).catch(() => {})
    }
  }

  async function handleSubmit(deliveryAddressId?: string) {
    setSubmitting(true)
    try {
      const order = await submitBasket({ delivery_address_id: deliveryAddressId })
      setConfirmedOrder(order)
      setShowSubmit(false)
      window.dispatchEvent(new Event('basketUpdated'))
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to submit order')
    } finally {
      setSubmitting(false)
    }
  }

  if (confirmedOrder) {
    return <OrderConfirmation order={confirmedOrder} onDone={() => setConfirmedOrder(null)} />
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-24">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-amber-500" />
      </div>
    )
  }

  if (error) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <div className="flex items-center gap-2 text-red-600">
          <AlertCircle size={18} />
          <p>{error}</p>
        </div>
      </div>
    )
  }

  if (!basket || basket.item_count === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-16 text-center">
        <ShoppingCart size={48} className="text-slate-300 mx-auto mb-4" />
        <h1 className="text-xl font-semibold text-slate-700 mb-2">Your basket is empty</h1>
        <p className="text-slate-400 mb-6">Browse the catalog and add titles to start an order.</p>
        <Link
          href="/catalog"
          className="inline-block px-5 py-2.5 bg-amber-500 hover:bg-amber-600 text-white rounded-lg text-sm font-medium transition-colors"
        >
          Browse catalog
        </Link>
      </div>
    )
  }

  // Group items by routed distributor
  const groups: Record<string, RoutedItem[]> = {}
  const unrouted: RoutedItem[] = []
  for (const item of basket.items) {
    if (item.routed_distributor_code) {
      ;(groups[item.routed_distributor_code] ??= []).push(item)
    } else {
      unrouted.push(item)
    }
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {showSubmit && (
        <SubmitModal
          addresses={addresses}
          onSubmit={handleSubmit}
          onClose={() => setShowSubmit(false)}
          submitting={submitting}
        />
      )}

      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
          <ShoppingCart size={24} className="text-amber-500" />
          Basket
          <span className="text-base font-normal text-slate-400">({basket.item_count} {basket.item_count === 1 ? 'title' : 'titles'})</span>
        </h1>
        <button
          onClick={handleClear}
          className="flex items-center gap-1.5 text-sm text-slate-400 hover:text-red-500 transition-colors"
        >
          <Trash2 size={14} /> Clear basket
        </button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Items */}
        <div className="lg:col-span-2 space-y-5">
          {Object.entries(groups).map(([dist, items]) => (
            <div key={dist} className="bg-white rounded-xl border border-slate-200 overflow-hidden">
              <div className="bg-slate-50 px-4 py-2.5 border-b border-slate-200 flex items-center gap-2">
                <Package size={14} className="text-slate-400" />
                <span className="text-xs font-semibold text-slate-600 uppercase tracking-wide">
                  via {dist}
                </span>
              </div>
              <div className="divide-y divide-slate-100">
                {items.map(item => (
                  <BasketRow
                    key={item.isbn13}
                    item={item}
                    onQtyChange={handleQtyChange}
                    onRemove={handleRemove}
                  />
                ))}
              </div>
            </div>
          ))}

          {unrouted.length > 0 && (
            <div className="bg-white rounded-xl border border-amber-200 overflow-hidden">
              <div className="bg-amber-50 px-4 py-2.5 border-b border-amber-200 flex items-center gap-2">
                <AlertCircle size={14} className="text-amber-500" />
                <span className="text-xs font-semibold text-amber-700 uppercase tracking-wide">
                  Cannot route — no active distributor account
                </span>
              </div>
              <div className="divide-y divide-slate-100">
                {unrouted.map(item => (
                  <BasketRow
                    key={item.isbn13}
                    item={item}
                    onQtyChange={handleQtyChange}
                    onRemove={handleRemove}
                    dimmed
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Summary */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-xl border border-slate-200 p-5 sticky top-20">
            <h2 className="font-semibold text-slate-900 mb-4">Order summary</h2>
            <div className="space-y-2 text-sm mb-5">
              <div className="flex justify-between text-slate-600">
                <span>Titles</span>
                <span>{basket.item_count}</span>
              </div>
              <div className="flex justify-between text-slate-600">
                <span>Total cost (trade)</span>
                <span className="font-medium text-slate-900">{fmt(basket.total_cost_gbp)}</span>
              </div>
              {basket.avg_margin_pct && (
                <div className="flex justify-between text-slate-600">
                  <span>Avg margin</span>
                  <span className={cn('font-medium', marginColor(basket.avg_margin_pct))}>
                    {parseFloat(basket.avg_margin_pct).toFixed(1)}%
                  </span>
                </div>
              )}
            </div>

            {unrouted.length > 0 && (
              <div className="bg-amber-50 border border-amber-200 rounded-lg px-3 py-2.5 text-xs text-amber-700 mb-4">
                {unrouted.length} title{unrouted.length > 1 ? 's' : ''} cannot be ordered — link a distributor account first.
              </div>
            )}

            <button
              onClick={() => setShowSubmit(true)}
              disabled={Object.keys(groups).length === 0}
              className="w-full py-3 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-lg font-medium text-sm transition-colors"
            >
              Place order
            </button>
            <Link
              href="/catalog"
              className="block text-center mt-3 text-sm text-slate-400 hover:text-amber-600 transition-colors"
            >
              Continue shopping
            </Link>
          </div>
        </div>
      </div>
    </div>
  )
}

// ─── Basket row ───────────────────────────────────────────────────────────────

function BasketRow({
  item,
  onQtyChange,
  onRemove,
  dimmed = false,
}: {
  item: RoutedItem
  onQtyChange: (isbn13: string, qty: number) => void
  onRemove: (isbn13: string) => void
  dimmed?: boolean
}) {
  return (
    <div className={cn('flex gap-3 p-4', dimmed && 'opacity-60')}>
      {/* Cover */}
      <div className="flex-none w-10 h-14 bg-slate-100 rounded relative overflow-hidden">
        {item.cover_image_url ? (
          <Image src={item.cover_image_url} alt={item.title ?? ''} fill className="object-cover" />
        ) : (
          <div className="w-full h-full flex items-center justify-center text-slate-300 text-xs">No cover</div>
        )}
      </div>

      {/* Details */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-900 truncate">{item.title ?? item.isbn13}</p>
        <p className="text-xs text-slate-400 mb-2">ISBN {item.isbn13}</p>
        <div className="flex items-center gap-4">
          {/* Qty controls */}
          <div className="flex items-center gap-1">
            <button
              onClick={() => onQtyChange(item.isbn13, item.quantity - 1)}
              className="w-6 h-6 rounded border border-slate-200 flex items-center justify-center hover:bg-slate-50 text-slate-500"
            >
              <Minus size={10} />
            </button>
            <span className="w-7 text-center text-sm font-medium text-slate-900">{item.quantity}</span>
            <button
              onClick={() => onQtyChange(item.isbn13, item.quantity + 1)}
              className="w-6 h-6 rounded border border-slate-200 flex items-center justify-center hover:bg-slate-50 text-slate-500"
            >
              <Plus size={10} />
            </button>
          </div>
          {/* Prices */}
          {item.trade_price_gbp && (
            <span className="text-sm font-medium text-slate-900">{fmt(item.trade_price_gbp)}</span>
          )}
          {item.margin_pct && (
            <span className={cn('text-xs font-medium', marginColor(item.margin_pct))}>
              {parseFloat(item.margin_pct).toFixed(1)}% margin
            </span>
          )}
        </div>
      </div>

      {/* Remove */}
      <button
        onClick={() => onRemove(item.isbn13)}
        className="flex-none self-start mt-1 text-slate-300 hover:text-red-400 transition-colors"
      >
        <X size={14} />
      </button>
    </div>
  )
}
