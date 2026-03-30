'use client'

import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { Plus, List, Trash2, ChevronRight, BookOpen } from 'lucide-react'
import type { IsbnList } from '@/lib/types'

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export default function IsbnListsPage() {
  const [lists, setLists] = useState<IsbnList[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [deleting, setDeleting] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      const res = await fetch('/api/isbn-lists')
      if (!res.ok) throw new Error('Failed to load lists')
      setLists(await res.json())
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => { load() }, [load])

  const handleDelete = async (id: string, name: string) => {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return
    setDeleting(id)
    try {
      await fetch(`/api/isbn-lists/${id}`, { method: 'DELETE' })
      setLists(prev => prev.filter(l => l.id !== id))
    } finally {
      setDeleting(null)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50">
      <div className="max-w-3xl mx-auto px-4 py-8">

        <div className="flex items-center justify-between mb-6">
          <div>
            <h1 className="text-2xl font-bold text-slate-800">Saved ISBN lists</h1>
            <p className="text-slate-500 text-sm mt-1">
              Save order lists for later — Christmas orders, standing orders, display sets.
            </p>
          </div>
          <Link
            href="/order/bulk"
            className="flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg px-4 py-2 text-sm font-medium transition-colors"
          >
            <Plus size={15} />
            New quick order
          </Link>
        </div>

        {loading && (
          <div className="text-center py-16 text-slate-400 text-sm">Loading…</div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg px-4 py-3 text-sm text-red-700">
            {error}
          </div>
        )}

        {!loading && !error && lists.length === 0 && (
          <div className="text-center py-20">
            <List size={44} className="mx-auto mb-4 text-slate-200" />
            <p className="text-slate-500 text-sm mb-4">No saved lists yet.</p>
            <Link
              href="/order/bulk"
              className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white rounded-lg px-5 py-2.5 text-sm font-medium transition-colors"
            >
              <BookOpen size={15} />
              Start a quick order
            </Link>
          </div>
        )}

        {lists.length > 0 && (
          <div className="bg-white rounded-xl border border-slate-200 divide-y divide-slate-100 overflow-hidden">
            {lists.map(list => (
              <div key={list.id} className="flex items-center gap-4 px-5 py-4 hover:bg-slate-50 transition-colors group">
                <div className="flex-1 min-w-0">
                  <Link
                    href={`/order/lists/${list.id}`}
                    className="font-medium text-slate-800 hover:text-amber-600 transition-colors"
                  >
                    {list.name}
                  </Link>
                  {list.description && (
                    <p className="text-xs text-slate-500 mt-0.5 truncate">{list.description}</p>
                  )}
                  <p className="text-xs text-slate-400 mt-1">
                    {list.item_count} ISBN{list.item_count !== 1 ? 's' : ''} · Updated {formatDate(list.updated_at)}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <button
                    onClick={() => handleDelete(list.id, list.name)}
                    disabled={deleting === list.id}
                    className="text-slate-300 hover:text-red-400 transition-colors opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 size={15} />
                  </button>
                  <Link
                    href={`/order/lists/${list.id}`}
                    className="text-slate-400 hover:text-amber-600 transition-colors"
                  >
                    <ChevronRight size={18} />
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
