'use client'

import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Loader2 } from 'lucide-react'

type Conflict = {
  id: string
  book_id: string
  field_name: string
  onix_value: string | null
  editorial_value: string | null
  status: string
  created_at: string
}

type ConflictList = { conflicts: Conflict[]; total: number }

const FIELD_LABELS: Record<string, string> = {
  description: 'Book Description',
  toc: 'Table of Contents',
  excerpt: 'Excerpt / Sample',
}

function truncate(s: string | null, max = 140): string {
  if (!s) return '(empty)'
  return s.length > max ? s.slice(0, max) + '…' : s
}

export default function ConflictsPage() {
  const [data, setData] = useState<ConflictList | null>(null)
  const [loading, setLoading] = useState(true)
  const [resolving, setResolving] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/portal/conflicts?status=pending&limit=50')
      if (!res.ok) throw new Error()
      setData(await res.json())
    } catch {
      setError('Could not load conflicts')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const resolve = async (conflictId: string, resolution: string) => {
    setResolving(conflictId)
    try {
      const res = await fetch(`/api/portal/conflicts/${conflictId}/resolve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ resolution }),
      })
      if (!res.ok) throw new Error()
      // Remove from list
      setData((prev) =>
        prev
          ? { ...prev, conflicts: prev.conflicts.filter((c) => c.id !== conflictId), total: prev.total - 1 }
          : prev,
      )
    } catch {
      setError('Failed to resolve conflict')
    } finally {
      setResolving(null)
    }
  }

  return (
    <div>
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-slate-900">Metadata Conflicts</h1>
        <p className="text-slate-500 text-sm">
          These fields were modified in your ONIX feed but conflict with existing editorial changes.
          Choose which version to keep.
        </p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-md p-3 mb-4">
          {error}
        </div>
      )}

      {loading && (
        <div className="flex justify-center py-16">
          <Loader2 className="animate-spin text-slate-400" size={24} />
        </div>
      )}

      {!loading && data?.conflicts.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <CheckCircle2 size={32} className="text-green-400 mx-auto mb-3" />
          <p className="text-slate-600 font-medium">No pending conflicts</p>
          <p className="text-slate-400 text-sm">All metadata conflicts have been resolved.</p>
        </div>
      )}

      <div className="space-y-4">
        {data?.conflicts.map((conflict) => (
          <div key={conflict.id} className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="flex items-center justify-between mb-3">
              <span className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                {FIELD_LABELS[conflict.field_name] ?? conflict.field_name}
              </span>
              <span className="text-xs text-slate-400">
                {new Date(conflict.created_at).toLocaleDateString('en-GB')}
              </span>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              {/* ONIX value */}
              <div className="bg-blue-50 border border-blue-200 rounded-lg p-3">
                <p className="text-xs font-semibold text-blue-600 mb-1.5">From feed (ONIX)</p>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {truncate(conflict.onix_value)}
                </p>
              </div>
              {/* Editorial value */}
              <div className="bg-amber-50 border border-amber-200 rounded-lg p-3">
                <p className="text-xs font-semibold text-amber-600 mb-1.5">Current editorial</p>
                <p className="text-sm text-slate-700 leading-relaxed">
                  {truncate(conflict.editorial_value)}
                </p>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => resolve(conflict.id, 'accept_onix')}
                disabled={resolving === conflict.id}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-blue-600 hover:bg-blue-700 disabled:opacity-60 text-white text-sm rounded-md transition-colors"
              >
                {resolving === conflict.id ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                Use feed version
              </button>
              <button
                onClick={() => resolve(conflict.id, 'keep_editorial')}
                disabled={resolving === conflict.id}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white text-sm rounded-md transition-colors"
              >
                {resolving === conflict.id ? <Loader2 size={12} className="animate-spin" /> : <XCircle size={12} />}
                Keep editorial
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
