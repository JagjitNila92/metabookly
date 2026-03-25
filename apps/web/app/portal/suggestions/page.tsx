'use client'

import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Sparkles, Loader2, Zap } from 'lucide-react'

type Suggestion = {
  id: string
  book_id: string
  field_name: string
  original_value: string | null
  suggested_value: string
  confidence: string
  reasoning: string | null
  status: string
  created_at: string
}

type SuggestionList = {
  suggestions: Suggestion[]
  total: number
  by_confidence: Record<string, number>
}

const CONFIDENCE_STYLE: Record<string, string> = {
  high: 'bg-green-50 text-green-700 border-green-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  low: 'bg-slate-100 text-slate-600 border-slate-200',
}

const FIELD_LABELS: Record<string, string> = {
  description: 'Description',
  toc: 'Table of Contents',
  excerpt: 'Excerpt',
}

function truncate(s: string | null, max = 180): string {
  if (!s) return '(none)'
  return s.length > max ? s.slice(0, max) + '…' : s
}

export default function SuggestionsPage() {
  const [data, setData] = useState<SuggestionList | null>(null)
  const [loading, setLoading] = useState(true)
  const [actionId, setActionId] = useState<string | null>(null)
  const [bulkLoading, setBulkLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [confidenceFilter, setConfidenceFilter] = useState<string>('')

  const load = async (conf?: string) => {
    setLoading(true)
    setError(null)
    try {
      const qs = new URLSearchParams({ limit: '100' })
      if (conf) qs.set('confidence', conf)
      const res = await fetch(`/api/portal/suggestions?${qs}`)
      if (!res.ok) throw new Error()
      setData(await res.json())
    } catch {
      setError('Could not load suggestions')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const act = async (id: string, action: 'accept' | 'reject') => {
    setActionId(id)
    try {
      const res = await fetch(`/api/portal/suggestions/${id}/${action}`, { method: 'POST' })
      if (!res.ok) throw new Error()
      setData((prev) =>
        prev
          ? {
              ...prev,
              suggestions: prev.suggestions.filter((s) => s.id !== id),
              total: prev.total - 1,
            }
          : prev,
      )
    } catch {
      setError(`Failed to ${action} suggestion`)
    } finally {
      setActionId(null)
    }
  }

  const bulkAccept = async (confidence: string) => {
    setBulkLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/portal/suggestions/bulk-accept', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ confidence }),
      })
      if (!res.ok) throw new Error()
      const { accepted } = await res.json()
      // Reload list
      await load(confidenceFilter || undefined)
      alert(`${accepted} suggestion${accepted !== 1 ? 's' : ''} accepted`)
    } catch {
      setError('Bulk accept failed')
    } finally {
      setBulkLoading(false)
    }
  }

  return (
    <div>
      <div className="flex items-start justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2">
            <Sparkles size={22} className="text-purple-500" />
            AI Metadata Suggestions
          </h1>
          <p className="text-slate-500 text-sm">
            AI-generated improvements to thin or missing metadata. Review and accept the ones that look right.
          </p>
        </div>
      </div>

      {/* Stats bar */}
      {data && (
        <div className="grid grid-cols-3 gap-3 mb-6">
          {(['high', 'medium', 'low'] as const).map((level) => (
            <button
              key={level}
              onClick={() => {
                const next = confidenceFilter === level ? '' : level
                setConfidenceFilter(next)
                load(next || undefined)
              }}
              className={`rounded-lg border px-4 py-3 text-left transition-all ${
                confidenceFilter === level
                  ? CONFIDENCE_STYLE[level]
                  : 'bg-white border-slate-200 hover:border-slate-300'
              }`}
            >
              <p className="text-xs font-semibold uppercase tracking-wider mb-0.5 capitalize">{level} confidence</p>
              <p className="text-2xl font-bold">{data.by_confidence[level] ?? 0}</p>
            </button>
          ))}
        </div>
      )}

      {/* Bulk accept bar */}
      {data && (data.by_confidence.high ?? 0) > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 flex items-center justify-between mb-6">
          <span className="text-sm text-green-700">
            <strong>{data.by_confidence.high}</strong> high-confidence suggestions ready to apply
          </span>
          <button
            onClick={() => bulkAccept('high')}
            disabled={bulkLoading}
            className="flex items-center gap-1.5 px-3 py-1.5 bg-green-600 hover:bg-green-700 disabled:opacity-60 text-white text-sm rounded-md transition-colors"
          >
            {bulkLoading ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
            Accept all high-confidence
          </button>
        </div>
      )}

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

      {!loading && data?.suggestions.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <Sparkles size={32} className="text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600 font-medium">No pending suggestions</p>
          <p className="text-slate-400 text-sm">
            {confidenceFilter
              ? `No ${confidenceFilter}-confidence suggestions — try another filter`
              : 'AI suggestions will appear here after feeds are processed'}
          </p>
        </div>
      )}

      <div className="space-y-4">
        {data?.suggestions.map((s) => (
          <div key={s.id} className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider ${CONFIDENCE_STYLE[s.confidence]}`}>
                {s.confidence}
              </span>
              <span className="text-xs text-slate-500 font-medium">
                {FIELD_LABELS[s.field_name] ?? s.field_name}
              </span>
              {s.reasoning && (
                <span className="text-xs text-slate-400 italic ml-auto">{s.reasoning}</span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <p className="text-xs font-semibold text-slate-500 mb-1.5">Original</p>
                <p className="text-sm text-slate-600 leading-relaxed">{truncate(s.original_value)}</p>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <p className="text-xs font-semibold text-purple-600 mb-1.5">AI suggestion</p>
                <p className="text-sm text-slate-700 leading-relaxed">{truncate(s.suggested_value)}</p>
              </div>
            </div>

            <div className="flex gap-2">
              <button
                onClick={() => act(s.id, 'accept')}
                disabled={actionId === s.id}
                className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 disabled:opacity-60 text-white text-sm rounded-md transition-colors"
              >
                {actionId === s.id ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle2 size={12} />}
                Accept
              </button>
              <button
                onClick={() => act(s.id, 'reject')}
                disabled={actionId === s.id}
                className="flex items-center gap-1.5 px-3 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-50 disabled:opacity-60 text-sm rounded-md transition-colors"
              >
                <XCircle size={12} />
                Reject
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
