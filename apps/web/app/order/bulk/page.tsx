'use client'

import { useCallback, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import Image from 'next/image'
import Link from 'next/link'
import {
  Upload, Search, ShoppingCart, ChevronDown, ChevronUp,
  X, AlertTriangle, BookX, CheckCircle2, Save,
} from 'lucide-react'
import type { BookSummary, BulkLookupResponse, OutOfPrintEntry } from '@/lib/types'
import { cn } from '@/lib/utils'

// ─── Types ────────────────────────────────────────────────────────────────────

interface MatchedRow {
  book: BookSummary
  quantity: number
  alreadyInBasket?: boolean
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function parseIsbnText(raw: string): string[] {
  // Split on whitespace, commas, semicolons, pipes, or newlines
  return raw
    .split(/[\s,;|\n\r]+/)
    .map(s => s.trim().replace(/-/g, ''))
    .filter(s => s.length > 0)
}

function coverSrc(url: string | null, isbn: string) {
  return url || `https://covers.openlibrary.org/b/isbn/${isbn}-M.jpg`
}

function fmt(val: string | null) {
  if (!val) return '—'
  return `£${parseFloat(val).toFixed(2)}`
}

function authorLine(book: BookSummary) {
  const authors = book.contributors.filter(c => c.role_code === 'A01')
  if (!authors.length) return null
  return authors.map(a => a.person_name).join(', ')
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function CollapsibleSection({
  title, count, variant, children,
}: {
  title: string
  count: number
  variant: 'amber' | 'red'
  children: React.ReactNode
}) {
  const [open, setOpen] = useState(false)
  if (!count) return null
  const colors = {
    amber: 'bg-amber-50 border-amber-200 text-amber-800',
    red: 'bg-red-50 border-red-200 text-red-800',
  }
  return (
    <div className={cn('border rounded-lg overflow-hidden', colors[variant])}>
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-sm font-medium"
      >
        <span>{title} ({count})</span>
        {open ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>
      {open && <div className="px-4 pb-3">{children}</div>}
    </div>
  )
}

function SaveListModal({
  onSave,
  onClose,
}: {
  onSave: (name: string, description: string) => void
  onClose: () => void
}) {
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <div className="flex items-center justify-between mb-4">
          <h2 className="font-semibold text-slate-800">Save as ISBN list</h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X size={18} />
          </button>
        </div>
        <div className="space-y-3">
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">List name *</label>
            <input
              autoFocus
              value={name}
              onChange={e => setName(e.target.value)}
              placeholder="e.g. Christmas 2026 Order"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
            />
          </div>
          <div>
            <label className="text-xs font-medium text-slate-600 mb-1 block">Description (optional)</label>
            <input
              value={desc}
              onChange={e => setDesc(e.target.value)}
              placeholder="e.g. Titles for the holiday display"
              className="w-full border border-slate-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
            />
          </div>
        </div>
        <div className="flex gap-2 mt-5">
          <button
            onClick={onClose}
            className="flex-1 border border-slate-200 rounded-lg px-4 py-2 text-sm text-slate-600 hover:bg-slate-50"
          >
            Cancel
          </button>
          <button
            disabled={!name.trim()}
            onClick={() => onSave(name.trim(), desc.trim())}
            className="flex-1 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-lg px-4 py-2 text-sm font-medium"
          >
            Save list
          </button>
        </div>
      </div>
    </div>
  )
}

// ─── Main page ────────────────────────────────────────────────────────────────

export default function BulkOrderPage() {
  const router = useRouter()
  const fileRef = useRef<HTMLInputElement>(null)

  const [rawInput, setRawInput] = useState('')
  const [looking, setLooking] = useState(false)
  const [result, setResult] = useState<BulkLookupResponse | null>(null)
  const [rows, setRows] = useState<MatchedRow[]>([])
  const [adding, setAdding] = useState(false)
  const [addResult, setAddResult] = useState<{ added: number; already: number; failed: number } | null>(null)
  const [showSaveModal, setShowSaveModal] = useState(false)
  const [saveStatus, setSaveStatus] = useState<'idle' | 'saving' | 'saved' | 'error'>('idle')
  const [error, setError] = useState<string | null>(null)

  // ── Parse CSV file ──────────────────────────────────────────────────────────
  const handleFile = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    const reader = new FileReader()
    reader.onload = ev => {
      const text = ev.target?.result as string
      setRawInput(prev => (prev ? prev + '\n' + text : text))
    }
    reader.readAsText(file)
    e.target.value = ''
  }, [])

  // ── Lookup ──────────────────────────────────────────────────────────────────
  const handleLookup = useCallback(async () => {
    const isbns = parseIsbnText(rawInput)
    if (!isbns.length) return
    setLooking(true)
    setError(null)
    setResult(null)
    setAddResult(null)
    try {
      const res = await fetch('/api/catalog/bulk-lookup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ isbns }),
      })
      if (!res.ok) throw new Error(`Lookup failed (${res.status})`)
      const data: BulkLookupResponse = await res.json()
      setResult(data)
      setRows(data.matched.map(b => ({ book: b, quantity: 1 })))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Lookup failed')
    } finally {
      setLooking(false)
    }
  }, [rawInput])

  // ── Quantity change ─────────────────────────────────────────────────────────
  const setQty = (isbn13: string, qty: number) => {
    setRows(prev => prev.map(r => r.book.isbn13 === isbn13 ? { ...r, quantity: Math.max(1, qty) } : r))
  }

  // ── Add to basket ───────────────────────────────────────────────────────────
  const handleAddToBasket = useCallback(async () => {
    if (!rows.length) return
    setAdding(true)
    setError(null)
    try {
      const res = await fetch('/api/basket/bulk-add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          items: rows.map(r => ({ isbn13: r.book.isbn13, quantity: r.quantity })),
        }),
      })
      if (!res.ok) throw new Error(`Add to basket failed (${res.status})`)
      const data = await res.json()
      setAddResult({
        added: data.added?.length ?? 0,
        already: data.already_in_basket?.length ?? 0,
        failed: data.failed?.length ?? 0,
      })
      // Mark already-in-basket rows
      const alreadySet = new Set<string>(data.already_in_basket ?? [])
      setRows(prev => prev.map(r => ({ ...r, alreadyInBasket: alreadySet.has(r.book.isbn13) })))
      window.dispatchEvent(new Event('basketUpdated'))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Add to basket failed')
    } finally {
      setAdding(false)
    }
  }, [rows])

  // ── Save as list ────────────────────────────────────────────────────────────
  const handleSaveList = useCallback(async (name: string, description: string) => {
    setShowSaveModal(false)
    setSaveStatus('saving')
    try {
      const res = await fetch('/api/isbn-lists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          name,
          description: description || null,
          items: rows.map(r => ({ isbn13: r.book.isbn13, quantity: r.quantity })),
        }),
      })
      if (!res.ok) throw new Error('Save failed')
      setSaveStatus('saved')
      setTimeout(() => setSaveStatus('idle'), 3000)
    } catch {
      setSaveStatus('error')
      setTimeout(() => setSaveStatus('idle'), 3000)
    }
  }, [rows])

  // ─────────────────────────────────────────────────────────────────────────────

  const hasResults = result !== null
  const totalInput = parseIsbnText(rawInput).length

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-4xl mx-auto px-4 py-8">

        {/* Header */}
        <div className="mb-6">
          <h1 className="text-2xl font-bold text-slate-800">Quick order</h1>
          <p className="text-slate-500 text-sm mt-1">
            Paste ISBNs or upload a CSV to check availability and add to basket in bulk.{' '}
            <Link href="/order/lists" className="text-amber-600 hover:underline">View saved lists →</Link>
          </p>
        </div>

        {/* Input area */}
        <div className="bg-white rounded-xl border border-slate-200 p-5 mb-4">
          <div className="flex items-center justify-between mb-3">
            <label className="text-sm font-medium text-slate-700">
              ISBNs — paste one per line, or comma/semicolon separated
            </label>
            <button
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-1.5 text-xs text-amber-600 hover:text-amber-700 font-medium border border-amber-200 rounded-lg px-3 py-1.5 hover:bg-amber-50 transition-colors"
            >
              <Upload size={13} />
              Upload CSV
            </button>
          </div>
          <input ref={fileRef} type="file" accept=".csv,.txt" onChange={handleFile} className="hidden" />
          <textarea
            value={rawInput}
            onChange={e => setRawInput(e.target.value)}
            placeholder={`9781234567890\n9780987654321, 9781111111111\nor paste from a spreadsheet...`}
            rows={8}
            className="w-full font-mono text-sm border border-slate-200 rounded-lg px-3 py-2.5 focus:outline-none focus:ring-2 focus:ring-amber-400 resize-y"
          />
          <div className="flex items-center justify-between mt-3">
            <span className="text-xs text-slate-400">
              {totalInput > 0 ? `${totalInput} ISBN${totalInput !== 1 ? 's' : ''} detected` : 'Supports ISBN-13, ISBN-10, and Excel formats'}
            </span>
            <button
              onClick={handleLookup}
              disabled={!rawInput.trim() || looking}
              className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-lg px-5 py-2 text-sm font-medium transition-colors"
            >
              <Search size={15} />
              {looking ? 'Checking…' : 'Check availability'}
            </button>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700 mb-4">
            {error}
          </div>
        )}

        {/* Results */}
        {hasResults && (
          <div className="space-y-4">

            {/* Summary bar */}
            <div className="flex flex-wrap gap-3 text-sm">
              <span className="bg-green-50 text-green-700 border border-green-200 rounded-full px-3 py-1 font-medium">
                ✓ {result.matched.length} available
              </span>
              {result.out_of_print.length > 0 && (
                <span className="bg-amber-50 text-amber-700 border border-amber-200 rounded-full px-3 py-1 font-medium">
                  {result.out_of_print.length} out of print
                </span>
              )}
              {result.not_found.length > 0 && (
                <span className="bg-red-50 text-red-700 border border-red-200 rounded-full px-3 py-1 font-medium">
                  {result.not_found.length} not found
                </span>
              )}
              {result.duplicates_removed > 0 && (
                <span className="text-slate-400 text-xs self-center">
                  ({result.duplicates_removed} duplicate{result.duplicates_removed !== 1 ? 's' : ''} removed)
                </span>
              )}
            </div>

            {/* Add result toast */}
            {addResult && (
              <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-800 flex items-center gap-2">
                <CheckCircle2 size={16} className="shrink-0" />
                <span>
                  {addResult.added} title{addResult.added !== 1 ? 's' : ''} added to basket
                  {addResult.already > 0 && `, ${addResult.already} quantity updated`}
                  {addResult.failed > 0 && ` — ${addResult.failed} failed`}
                </span>
              </div>
            )}

            {/* Save status */}
            {saveStatus === 'saved' && (
              <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 text-sm text-green-800 flex items-center gap-2">
                <CheckCircle2 size={16} className="shrink-0" />
                List saved. <Link href="/order/lists" className="underline font-medium">View your lists →</Link>
              </div>
            )}
            {saveStatus === 'error' && (
              <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
                Failed to save list. Please try again.
              </div>
            )}

            {/* Matched titles table */}
            {rows.length > 0 && (
              <div className="bg-white rounded-xl border border-slate-200 overflow-hidden">
                <div className="flex items-center justify-between px-5 py-3 border-b border-slate-100">
                  <h2 className="font-semibold text-slate-800 text-sm">
                    Available titles ({rows.length})
                  </h2>
                  <div className="flex items-center gap-2">
                    <button
                      onClick={() => setShowSaveModal(true)}
                      disabled={saveStatus === 'saving'}
                      className="flex items-center gap-1.5 text-xs border border-slate-200 rounded-lg px-3 py-1.5 text-slate-600 hover:bg-slate-50 transition-colors"
                    >
                      <Save size={13} />
                      {saveStatus === 'saving' ? 'Saving…' : 'Save as list'}
                    </button>
                    <button
                      onClick={handleAddToBasket}
                      disabled={adding}
                      className="flex items-center gap-1.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-lg px-4 py-1.5 text-xs font-medium transition-colors"
                    >
                      <ShoppingCart size={13} />
                      {adding ? 'Adding…' : `Add all to basket`}
                    </button>
                  </div>
                </div>

                <div className="divide-y divide-slate-100">
                  {rows.map(({ book, quantity, alreadyInBasket }) => (
                    <div key={book.isbn13} className="flex items-center gap-3 px-5 py-3">
                      {/* Cover */}
                      <div className="w-10 h-14 shrink-0 relative rounded overflow-hidden bg-slate-100">
                        <Image
                          src={coverSrc(book.cover_image_url, book.isbn13)}
                          alt={book.title}
                          fill
                          className="object-cover"
                          unoptimized
                        />
                      </div>

                      {/* Info */}
                      <div className="flex-1 min-w-0">
                        <Link
                          href={`/books/${book.isbn13}`}
                          className="font-medium text-slate-800 text-sm hover:text-amber-600 line-clamp-1"
                        >
                          {book.title}
                        </Link>
                        {authorLine(book) && (
                          <p className="text-xs text-slate-500 mt-0.5">{authorLine(book)}</p>
                        )}
                        <p className="text-xs text-slate-400 mt-0.5">{book.isbn13}</p>
                      </div>

                      {/* Price */}
                      <div className="text-right shrink-0">
                        <p className="text-sm font-medium text-slate-700">{fmt(book.rrp_gbp)}</p>
                        <p className="text-[11px] text-slate-400">RRP</p>
                      </div>

                      {/* Already in basket badge */}
                      {alreadyInBasket && (
                        <span className="text-[11px] bg-amber-100 text-amber-700 rounded-full px-2 py-0.5 shrink-0 font-medium">
                          In basket
                        </span>
                      )}

                      {/* Qty */}
                      <div className="flex items-center gap-1 shrink-0">
                        <button
                          onClick={() => setQty(book.isbn13, quantity - 1)}
                          className="w-7 h-7 rounded border border-slate-200 flex items-center justify-center text-slate-500 hover:bg-slate-50 text-lg leading-none"
                        >
                          −
                        </button>
                        <input
                          type="number"
                          min={1}
                          value={quantity}
                          onChange={e => setQty(book.isbn13, parseInt(e.target.value) || 1)}
                          className="w-12 text-center border border-slate-200 rounded text-sm py-1 focus:outline-none focus:ring-1 focus:ring-amber-400"
                        />
                        <button
                          onClick={() => setQty(book.isbn13, quantity + 1)}
                          className="w-7 h-7 rounded border border-slate-200 flex items-center justify-center text-slate-500 hover:bg-slate-50 text-lg leading-none"
                        >
                          +
                        </button>
                      </div>

                      {/* Remove */}
                      <button
                        onClick={() => setRows(prev => prev.filter(r => r.book.isbn13 !== book.isbn13))}
                        className="text-slate-300 hover:text-red-400 transition-colors"
                      >
                        <X size={16} />
                      </button>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Out of print — collapsed */}
            <CollapsibleSection
              title="Out of print"
              count={result.out_of_print.length}
              variant="amber"
            >
              <div className="space-y-1 mt-1">
                {result.out_of_print.map((e: OutOfPrintEntry) => (
                  <div key={e.isbn13} className="flex items-center gap-2 text-sm">
                    <BookX size={13} className="text-amber-500 shrink-0" />
                    <span className="font-mono text-xs text-amber-700">{e.isbn13}</span>
                    {e.title && <span className="text-amber-800 truncate">{e.title}</span>}
                    {e.publisher_name && (
                      <span className="text-amber-600 text-xs shrink-0">({e.publisher_name})</span>
                    )}
                  </div>
                ))}
              </div>
            </CollapsibleSection>

            {/* Not found — collapsed */}
            <CollapsibleSection
              title="Not found in catalogue"
              count={result.not_found.length}
              variant="red"
            >
              <div className="flex flex-wrap gap-2 mt-1">
                {result.not_found.map((isbn: string) => (
                  <span key={isbn} className="font-mono text-xs bg-red-100 text-red-700 rounded px-2 py-0.5 flex items-center gap-1">
                    <AlertTriangle size={11} />
                    {isbn}
                  </span>
                ))}
              </div>
            </CollapsibleSection>

          </div>
        )}

        {/* Empty state */}
        {!hasResults && !looking && (
          <div className="text-center py-16 text-slate-400">
            <ShoppingCart size={40} className="mx-auto mb-3 opacity-30" />
            <p className="text-sm">Paste ISBNs above and click <strong>Check availability</strong></p>
          </div>
        )}

      </div>

      {/* Save list modal */}
      {showSaveModal && (
        <SaveListModal
          onSave={handleSaveList}
          onClose={() => setShowSaveModal(false)}
        />
      )}
    </div>
  )
}
