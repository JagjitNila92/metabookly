'use client'

import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Sparkles, Loader2, Zap, RefreshCw } from 'lucide-react'

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
  high:   'bg-green-50 text-green-700 border-green-200',
  medium: 'bg-amber-50 text-amber-700 border-amber-200',
  low:    'bg-slate-100 text-slate-600 border-slate-200',
}

const FIELD_LABELS: Record<string, string> = {
  description: 'Description',
  toc:         'Table of Contents',
  excerpt:     'Excerpt',
}

const FIELDS = ['description', 'toc', 'excerpt'] as const
type Field = typeof FIELDS[number]

function truncate(s: string | null, max = 200): string {
  if (!s) return '(none)'
  return s.length > max ? s.slice(0, max) + '…' : s
}

export default function SuggestionsPage() {
  const [data, setData]               = useState<SuggestionList | null>(null)
  const [loading, setLoading]         = useState(true)
  const [actionId, setActionId]       = useState<string | null>(null)
  const [bulkLoading, setBulkLoading] = useState(false)
  const [generating, setGenerating]   = useState<Field | null>(null)
  const [error, setError]             = useState<string | null>(null)
  const [notice, setNotice]           = useState<string | null>(null)
  const [confidenceFilter, setConfidenceFilter] = useState<string>('')
  const [fieldFilter, setFieldFilter] = useState<Field | ''>('')

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
      setData(prev =>
        prev ? { ...prev, suggestions: prev.suggestions.filter(s => s.id !== id), total: prev.total - 1 } : prev
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
      await load(confidenceFilter || undefined)
      setNotice(`${accepted} suggestion${accepted !== 1 ? 's' : ''} accepted.`)
    } catch {
      setError('Bulk accept failed')
    } finally {
      setBulkLoading(false)
    }
  }

  const generate = async (field: Field) => {
    setGenerating(field)
    setError(null)
    setNotice(null)
    try {
      const res = await fetch('/api/portal/suggestions/generate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ field, limit: 20 }),
      })
      if (!res.ok) throw new Error()
      setNotice(`Generating ${FIELD_LABELS[field].toLowerCase()} suggestions in the background. Refresh in a moment.`)
    } catch {
      setError(`Failed to trigger generation for ${FIELD_LABELS[field]}`)
    } finally {
      setGenerating(null)
    }
  }

  const displayed = data?.suggestions.filter(s =>
    (fieldFilter ? s.field_name === fieldFilter : true)
  ) ?? []

  return (
    <div>
      {/* Header */}
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
        <button
          onClick={() => load(confidenceFilter || undefined)}
          className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-amber-600 transition-colors"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* Notice / error banners */}
      {notice && (
        <div className="bg-blue-50 border border-blue-200 text-blue-700 text-sm rounded-md p-3 mb-4">
          {notice}
        </div>
      )}
      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-md p-3 mb-4">
          {error}
        </div>
      )}

      {/* Field type tabs + generate buttons */}
      <div className="flex items-center gap-2 mb-5 flex-wrap">
        <button
          onClick={() => setFieldFilter('')}
          className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
            fieldFilter === '' ? 'bg-purple-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300'
          }`}
        >
          All fields
        </button>
        {FIELDS.map(f => (
          <button
            key={f}
            onClick={() => setFieldFilter(f)}
            className={`px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
              fieldFilter === f ? 'bg-purple-600 text-white' : 'bg-white border border-slate-200 text-slate-600 hover:border-slate-300'
            }`}
          >
            {FIELD_LABELS[f]}
          </button>
        ))}

        <div className="ml-auto flex items-center gap-2">
          <span className="text-xs text-slate-400">Generate:</span>
          {FIELDS.map(f => (
            <button
              key={f}
              onClick={() => generate(f)}
              disabled={generating !== null}
              className="flex items-center gap-1 px-2.5 py-1.5 border border-purple-200 text-purple-600 hover:bg-purple-50 text-xs rounded-md transition-colors disabled:opacity-50"
            >
              {generating === f ? <Loader2 size={11} className="animate-spin" /> : <Sparkles size={11} />}
              {FIELD_LABELS[f]}
            </button>
          ))}
        </div>
      </div>

      {/* Confidence stats */}
      {data && (
        <div className="grid grid-cols-3 gap-3 mb-5">
          {(['high', 'medium', 'low'] as const).map(level => (
            <button
              key={level}
              onClick={() => {
                const next = confidenceFilter === level ? '' : level
                setConfidenceFilter(next)
                load(next || undefined)
              }}
              className={`rounded-lg border px-4 py-3 text-left transition-all ${
                confidenceFilter === level ? CONFIDENCE_STYLE[level] : 'bg-white border-slate-200 hover:border-slate-300'
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
        <div className="bg-green-50 border border-green-200 rounded-lg px-4 py-3 flex items-center justify-between mb-5">
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

      {loading && (
        <div className="flex justify-center py-16">
          <Loader2 className="animate-spin text-slate-400" size={24} />
        </div>
      )}

      {!loading && displayed.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <Sparkles size={32} className="text-slate-300 mx-auto mb-3" />
          <p className="text-slate-600 font-medium">No pending suggestions</p>
          <p className="text-slate-400 text-sm mt-1">
            {fieldFilter
              ? `No ${FIELD_LABELS[fieldFilter].toLowerCase()} suggestions — use Generate above to create some`
              : 'AI suggestions will appear here after feeds are processed or you trigger generation'}
          </p>
        </div>
      )}

      <div className="space-y-4">
        {displayed.map(s => (
          <div key={s.id} className="bg-white border border-slate-200 rounded-xl p-5">
            <div className="flex items-center gap-2 mb-3">
              <span className={`text-xs font-semibold px-2 py-0.5 rounded-full border uppercase tracking-wider ${CONFIDENCE_STYLE[s.confidence]}`}>
                {s.confidence}
              </span>
              <span className="text-xs font-medium text-slate-700 bg-slate-100 px-2 py-0.5 rounded">
                {FIELD_LABELS[s.field_name] ?? s.field_name}
              </span>
              {s.reasoning && (
                <span className="text-xs text-slate-400 italic ml-auto truncate max-w-xs">{s.reasoning}</span>
              )}
            </div>

            <div className="grid grid-cols-2 gap-4 mb-4">
              <div className="bg-slate-50 border border-slate-200 rounded-lg p-3">
                <p className="text-xs font-semibold text-slate-500 mb-1.5">Original</p>
                <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-wrap">
                  {truncate(s.original_value)}
                </p>
              </div>
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3">
                <p className="text-xs font-semibold text-purple-600 mb-1.5">AI suggestion</p>
                <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">
                  {truncate(s.suggested_value)}
                </p>
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
