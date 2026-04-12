'use client'

import { useEffect, useState } from 'react'
import {
  CheckCircle2, XCircle, Clock, AlertTriangle, RefreshCw,
  Loader2, ChevronDown, ChevronUp, Download, ShieldCheck, ShieldAlert,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type ValidationError = {
  isbn13: string | null
  field: string
  message: string
  line: number | null
  severity: 'error' | 'warning'
}

type Feed = {
  id: string
  original_filename: string | null
  file_size_bytes: number | null
  onix_version: string | null
  sequence_number: number | null
  gaps_detected: boolean
  status: string
  records_found: number | null
  records_upserted: number | null
  records_failed: number | null
  records_conflicted: number | null
  error_detail: string | null
  triggered_by: string | null
  created_at: string
  completed_at: string | null
  validation_passed: boolean | null
  validation_errors_count: number | null
  validation_warnings_count: number | null
}

type FeedDetail = Feed & {
  sample_errors: string[] | null
  validation_errors: ValidationError[] | null
}

type FeedList = { feeds: Feed[]; total: number }

// ── Status display ─────────────────────────────────────────────────────────────

const STATUS_ICON: Record<string, React.ReactNode> = {
  completed:             <CheckCircle2 size={14} className="text-green-500" />,
  completed_with_errors: <AlertTriangle size={14} className="text-amber-500" />,
  failed:                <XCircle size={14} className="text-red-500" />,
  processing:            <Loader2 size={14} className="text-blue-500 animate-spin" />,
  pending:               <Clock size={14} className="text-slate-400" />,
}

const STATUS_LABEL: Record<string, string> = {
  completed:             'Completed',
  completed_with_errors: 'Errors',
  failed:                'Failed',
  processing:            'Processing…',
  pending:               'Pending',
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatBytes(n: number | null): string {
  if (!n) return '—'
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(0)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

function formatDate(s: string | null): string {
  if (!s) return '—'
  return new Date(s).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function downloadCsv(feedId: string, errors: ValidationError[]) {
  const header = 'ISBN-13,Field,Severity,Message,Line\n'
  const rows = errors.map(e =>
    [e.isbn13 ?? '', `"${e.field}"`, e.severity, `"${e.message.replace(/"/g, '""')}"`, e.line ?? ''].join(',')
  )
  const blob = new Blob([header + rows.join('\n')], { type: 'text/csv' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `validation-errors-${feedId.slice(0, 8)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

// ── Validation error drawer ────────────────────────────────────────────────────

function ValidationDrawer({ feedId, errors }: { feedId: string; errors: ValidationError[] }) {
  const hardErrors = errors.filter(e => e.severity === 'error')
  const warnings   = errors.filter(e => e.severity === 'warning')

  return (
    <div className="px-4 pb-4 bg-slate-50 border-t border-slate-100">
      <div className="flex items-center justify-between py-2">
        <div className="flex items-center gap-3">
          {hardErrors.length > 0 && (
            <span className="text-xs font-medium text-red-600">
              {hardErrors.length} error{hardErrors.length !== 1 ? 's' : ''}
            </span>
          )}
          {warnings.length > 0 && (
            <span className="text-xs font-medium text-amber-600">
              {warnings.length} warning{warnings.length !== 1 ? 's' : ''}
            </span>
          )}
        </div>
        <button
          onClick={() => downloadCsv(feedId, errors)}
          className="flex items-center gap-1 text-xs text-slate-500 hover:text-amber-600 transition-colors"
        >
          <Download size={12} />
          Download CSV
        </button>
      </div>

      <div className="space-y-1 max-h-64 overflow-y-auto">
        {errors.map((e, i) => (
          <div
            key={i}
            className={`text-xs rounded px-3 py-2 flex gap-3 ${
              e.severity === 'error'
                ? 'bg-red-50 border border-red-100'
                : 'bg-amber-50 border border-amber-100'
            }`}
          >
            <span className={`shrink-0 font-medium w-12 ${e.severity === 'error' ? 'text-red-500' : 'text-amber-500'}`}>
              {e.severity === 'error' ? 'ERROR' : 'WARN'}
            </span>
            <div className="flex-1 min-w-0">
              <span className="font-mono text-slate-500">{e.isbn13 ?? 'No ISBN'}</span>
              {' · '}
              <span className="text-slate-600 font-medium">{e.field}</span>
              {e.line && <span className="text-slate-400"> (line {e.line})</span>}
              <p className="text-slate-700 mt-0.5">{e.message}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

// ── Feed row ──────────────────────────────────────────────────────────────────

function FeedRow({ feed }: { feed: Feed }) {
  const [expanded, setExpanded]     = useState(false)
  const [detail, setDetail]         = useState<FeedDetail | null>(null)
  const [loadingDetail, setLoading] = useState(false)

  const hasValidationIssues = (feed.validation_errors_count ?? 0) > 0 || (feed.validation_warnings_count ?? 0) > 0

  const toggleExpand = async () => {
    if (!expanded && !detail) {
      setLoading(true)
      try {
        const res = await fetch(`/api/portal/feeds/${feed.id}`)
        if (res.ok) setDetail(await res.json())
      } finally {
        setLoading(false)
      }
    }
    setExpanded(e => !e)
  }

  const allErrors: ValidationError[] = detail?.validation_errors ?? []

  return (
    <>
      <tr
        className={`border-b border-slate-100 transition-colors ${hasValidationIssues ? 'cursor-pointer hover:bg-slate-50' : 'hover:bg-slate-50'}`}
        onClick={hasValidationIssues ? toggleExpand : undefined}
      >
        {/* File info */}
        <td className="px-4 py-3">
          <p className="font-medium text-slate-900 truncate max-w-48">
            {feed.original_filename ?? 'Untitled'}
          </p>
          <p className="text-xs text-slate-400">
            {feed.onix_version ? `ONIX ${feed.onix_version}` : ''}
            {feed.onix_version && ' · '}
            {formatBytes(feed.file_size_bytes)}
            {feed.gaps_detected && (
              <span className="ml-2 text-amber-500 font-medium">⚠ sequence gap</span>
            )}
          </p>
        </td>

        {/* Ingest status */}
        <td className="px-4 py-3">
          <span className="flex items-center gap-1.5 text-sm">
            {STATUS_ICON[feed.status] ?? STATUS_ICON.pending}
            {STATUS_LABEL[feed.status] ?? feed.status}
          </span>
          {feed.error_detail && (
            <p className="text-xs text-red-500 mt-0.5 truncate max-w-48" title={feed.error_detail}>
              {feed.error_detail}
            </p>
          )}
        </td>

        {/* Validation badge */}
        <td className="px-4 py-3">
          {feed.validation_passed === null ? (
            <span className="text-xs text-slate-300">—</span>
          ) : feed.validation_passed && (feed.validation_warnings_count ?? 0) === 0 ? (
            <span className="flex items-center gap-1 text-xs text-green-600">
              <ShieldCheck size={13} /> Valid
            </span>
          ) : (
            <span className="flex items-center gap-1 text-xs text-amber-600">
              <ShieldAlert size={13} />
              {(feed.validation_errors_count ?? 0) > 0 && (
                <span className="text-red-500">{feed.validation_errors_count}E</span>
              )}
              {(feed.validation_errors_count ?? 0) > 0 && (feed.validation_warnings_count ?? 0) > 0 && ' '}
              {(feed.validation_warnings_count ?? 0) > 0 && (
                <span>{feed.validation_warnings_count}W</span>
              )}
            </span>
          )}
        </td>

        {/* Counts */}
        <td className="px-4 py-3 text-right text-slate-700">{feed.records_found ?? '—'}</td>
        <td className="px-4 py-3 text-right text-green-600 font-medium">{feed.records_upserted ?? '—'}</td>
        <td className="px-4 py-3 text-right text-red-500">{feed.records_failed ?? '—'}</td>
        <td className="px-4 py-3 text-right text-amber-500">{feed.records_conflicted ?? '—'}</td>
        <td className="px-4 py-3 text-slate-500 text-xs">{formatDate(feed.created_at)}</td>

        {/* Expand toggle */}
        <td className="px-4 py-3">
          {hasValidationIssues && (
            loadingDetail
              ? <Loader2 size={14} className="animate-spin text-slate-400" />
              : expanded
                ? <ChevronUp size={14} className="text-slate-400" />
                : <ChevronDown size={14} className="text-slate-400" />
          )}
        </td>
      </tr>

      {expanded && allErrors.length > 0 && (
        <tr>
          <td colSpan={9} className="p-0">
            <ValidationDrawer feedId={feed.id} errors={allErrors} />
          </td>
        </tr>
      )}
    </>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function FeedsPage() {
  const [data, setData]     = useState<FeedList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/portal/feeds?limit=50')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setData(await res.json())
    } catch {
      setError('Could not load feed history')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Feed History</h1>
          {data && <p className="text-sm text-slate-500">{data.total} feeds submitted</p>}
        </div>
        <button
          onClick={load}
          className="flex items-center gap-1.5 text-sm text-slate-600 hover:text-amber-600 transition-colors"
        >
          <RefreshCw size={14} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 text-red-600 text-sm rounded-md p-3 mb-4">
          {error}
        </div>
      )}

      {loading && !data && (
        <div className="flex justify-center py-16">
          <Loader2 className="animate-spin text-slate-400" size={24} />
        </div>
      )}

      {data && data.feeds.length === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <p className="text-slate-500">No feeds submitted yet.</p>
          <a href="/portal/upload" className="mt-3 inline-block text-sm text-amber-600 hover:underline">
            Upload your first feed →
          </a>
        </div>
      )}

      {data && data.feeds.length > 0 && (
        <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-200 bg-slate-50 text-left">
                <th className="px-4 py-3 font-medium text-slate-600">File</th>
                <th className="px-4 py-3 font-medium text-slate-600">Status</th>
                <th className="px-4 py-3 font-medium text-slate-600">Validation</th>
                <th className="px-4 py-3 font-medium text-slate-600 text-right">Found</th>
                <th className="px-4 py-3 font-medium text-slate-600 text-right">Ingested</th>
                <th className="px-4 py-3 font-medium text-slate-600 text-right">Failed</th>
                <th className="px-4 py-3 font-medium text-slate-600 text-right">Conflicts</th>
                <th className="px-4 py-3 font-medium text-slate-600">Submitted</th>
                <th className="px-4 py-3 w-6" />
              </tr>
            </thead>
            <tbody>
              {data.feeds.map(feed => <FeedRow key={feed.id} feed={feed} />)}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
