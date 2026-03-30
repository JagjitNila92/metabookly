'use client'

import { useCallback, useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'
import {
  ArrowLeft, ShoppingCart, Pencil, Trash2, Check, X, Plus, Minus,
} from 'lucide-react'
import type { IsbnListDetail, IsbnListItem } from '@/lib/types'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function IsbnListDetailPage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()

  const [list, setList] = useState<IsbnListDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Edit name/description
  const [editingName, setEditingName] = useState(false)
  const [draftName, setDraftName] = useState('')
  const [draftDesc, setDraftDesc] = useState('')
  const [saving, setSaving] = useState(false)

  // Item quantities (local, applied on add-to-basket)
  const [qtys, setQtys] = useState<Record<string, number>>({})

  // Actions
  const [removing, setRemoving] = useState<string | null>(null)
  const [addingToBasket, setAddingToBasket] = useState(false)
  const [basketResult, setBasketResult] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const res = await fetch(`/api/isbn-lists/${id}`)
      if (!res.ok) throw new Error('List not found')
      const data: IsbnListDetail = await res.json()
      setList(data)
      const initial: Record<string, number> = {}
      data.items.forEach(item => { initial[item.isbn13] = item.quantity })
      setQtys(initial)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [id])

  useEffect(() => { load() }, [load])

  const startEdit = () => {
    if (!list) return
    setDraftName(list.name)
    setDraftDesc(list.description ?? '')
    setEditingName(true)
  }

  const saveEdit = async () => {
    if (!draftName.trim() || !list) return
    setSaving(true)
    try {
      const res = await fetch(`/api/isbn-lists/${id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: draftName.trim(), description: draftDesc.trim() || null }),
      })
      if (!res.ok) throw new Error('Save failed')
      const updated: IsbnListDetail = await res.json()
      setList(updated)
      setEditingName(false)
    } catch {
      // keep edit open
    } finally {
      setSaving(false)
    }
  }

  const removeItem = async (isbn13: string) => {
    setRemoving(isbn13)
    try {
      const res = await fetch(`/api/isbn-lists/${id}/items`, {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isbns: [isbn13] }),
      })
      if (!res.ok) throw new Error('Remove failed')
      const updated: IsbnListDetail = await res.json()
      setList(updated)
    } finally {
      setRemoving(null)
    }
  }

  const deleteList = async () => {
    if (!list || !confirm(`Delete "${list.name}"? This cannot be undone.`)) return
    await fetch(`/api/isbn-lists/${id}`, { method: 'DELETE' })
    router.push('/order/lists')
  }

  const handleAddToBasket = async () => {
    if (!list) return
    setAddingToBasket(true)
    setBasketResult(null)
    try {
      const res = await fetch('/api/basket/bulk-add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: list.items.map(item => ({
            isbn13: item.isbn13,
            quantity: qtys[item.isbn13] ?? item.quantity,
          })),
        }),
      })
      if (!res.ok) throw new Error('Failed')
      const data = await res.json()
      setBasketResult(
        `${data.added?.length ?? 0} added, ${data.already_in_basket?.length ?? 0} updated${data.failed?.length ? `, ${data.failed.length} failed` : ''}`
      )
      window.dispatchEvent(new Event('basketUpdated'))
    } catch {
      setBasketResult('Failed to add to basket')
    } finally {
      setAddingToBasket(false)
    }
  }

  if (loading) return <div className="min-h-screen bg-slate-50 flex items-center justify-center text-slate-400 text-sm">Loading…</div>
  if (error || !list) return (
    <div className="min-h-screen bg-slate-50 flex flex-col items-center justify-center gap-4">
      <p className="text-slate-500 text-sm">{error ?? 'List not found'}</p>
      <Link href="/order/lists" className="text-amber-600 hover:underline text-sm">Back to lists</Link>
    </div>
  )

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 py-8">

        {/* Back */}
        <Link
          href="/order/lists"
          className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-amber-600 mb-5 transition-colors"
        >
          <ArrowLeft size={14} />
          Saved lists
        </Link>

        {/* Header */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-4">
          {editingName ? (
            <div className="space-y-2">
              <input
                autoFocus
                value={draftName}
                onChange={e => setDraftName(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm font-semibold focus:outline-none focus:ring-2 focus:ring-amber-400"
                placeholder="List name"
              />
              <input
                value={draftDesc}
                onChange={e => setDraftDesc(e.target.value)}
                className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm text-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-400"
                placeholder="Description (optional)"
              />
              <div className="flex gap-2">
                <button
                  onClick={saveEdit}
                  disabled={!draftName.trim() || saving}
                  className="flex items-center gap-1 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-lg px-4 py-1.5 text-sm font-medium"
                >
                  <Check size={13} /> Save
                </button>
                <button
                  onClick={() => setEditingName(false)}
                  className="flex items-center gap-1 border border-slate-200 rounded-lg px-4 py-1.5 text-sm text-slate-600 hover:bg-slate-50"
                >
                  <X size={13} /> Cancel
                </button>
              </div>
            </div>
          ) : (
            <div className="flex items-start justify-between gap-4">
              <div>
                <h1 className="text-xl font-bold text-slate-800">{list.name}</h1>
                {list.description && <p className="text-sm text-slate-500 mt-1">{list.description}</p>}
                <p className="text-xs text-slate-400 mt-2">
                  {list.item_count} ISBN{list.item_count !== 1 ? 's' : ''} · Updated {formatDate(list.updated_at)}
                </p>
              </div>
              <div className="flex items-center gap-2 shrink-0">
                <button
                  onClick={startEdit}
                  className="text-slate-400 hover:text-slate-600 transition-colors"
                  title="Rename"
                >
                  <Pencil size={15} />
                </button>
                <button
                  onClick={deleteList}
                  className="text-slate-400 hover:text-red-500 transition-colors"
                  title="Delete list"
                >
                  <Trash2 size={15} />
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Actions */}
        {list.items.length > 0 && (
          <div className="flex items-center justify-between mb-4">
            <div className="flex items-center gap-3">
              <Link
                href={`/order/bulk`}
                className="text-sm text-slate-500 hover:text-amber-600 transition-colors"
              >
                Add more ISBNs →
              </Link>
            </div>
            <div className="flex items-center gap-2">
              {basketResult && (
                <span className="text-xs text-green-700 bg-green-50 border border-green-200 rounded-full px-3 py-1">
                  {basketResult}
                </span>
              )}
              <button
                onClick={handleAddToBasket}
                disabled={addingToBasket}
                className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
              >
                <ShoppingCart size={14} />
                {addingToBasket ? 'Adding…' : 'Add all to basket'}
              </button>
            </div>
          </div>
        )}

        {/* Items */}
        {list.items.length === 0 ? (
          <div className="text-center py-16 text-slate-400 text-sm bg-white rounded-xl border border-slate-200">
            No ISBNs in this list yet.{' '}
            <Link href="/order/bulk" className="text-amber-600 hover:underline">Add some →</Link>
          </div>
        ) : (
          <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
            {list.items.map((item: IsbnListItem) => (
              <div key={item.isbn13} className="flex items-center gap-4 px-5 py-3">
                <div className="flex-1 min-w-0">
                  <p className="font-mono text-sm text-slate-700">{item.isbn13}</p>
                  {item.note && <p className="text-xs text-slate-400 mt-0.5">{item.note}</p>}
                  <p className="text-xs text-slate-400 mt-0.5">Added {formatDate(item.added_at)}</p>
                </div>

                {/* Qty */}
                <div className="flex items-center gap-1 shrink-0">
                  <button
                    onClick={() => setQtys(prev => ({ ...prev, [item.isbn13]: Math.max(1, (prev[item.isbn13] ?? item.quantity) - 1) }))}
                    className="w-7 h-7 rounded border border-slate-200 flex items-center justify-center text-slate-500 hover:bg-slate-50"
                  >
                    <Minus size={12} />
                  </button>
                  <input
                    type="number"
                    min={1}
                    value={qtys[item.isbn13] ?? item.quantity}
                    onChange={e => setQtys(prev => ({ ...prev, [item.isbn13]: Math.max(1, parseInt(e.target.value) || 1) }))}
                    className="w-12 text-center border border-slate-200 rounded text-sm py-1 focus:outline-none focus:ring-1 focus:ring-amber-400"
                  />
                  <button
                    onClick={() => setQtys(prev => ({ ...prev, [item.isbn13]: (prev[item.isbn13] ?? item.quantity) + 1 }))}
                    className="w-7 h-7 rounded border border-slate-200 flex items-center justify-center text-slate-500 hover:bg-slate-50"
                  >
                    <Plus size={12} />
                  </button>
                </div>

                {/* Remove */}
                <button
                  onClick={() => removeItem(item.isbn13)}
                  disabled={removing === item.isbn13}
                  className="text-slate-300 hover:text-red-400 transition-colors shrink-0"
                >
                  <X size={15} />
                </button>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
