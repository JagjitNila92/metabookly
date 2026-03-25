'use client'

import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Clock, AlertTriangle, RefreshCw, Loader2 } from 'lucide-react'

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
}

type FeedList = { feeds: Feed[]; total: number }

const STATUS_ICON: Record<string, React.ReactNode> = {
  completed: <CheckCircle2 size={14} className="text-green-500" />,
  completed_with_errors: <AlertTriangle size={14} className="text-amber-500" />,
  failed: <XCircle size={14} className="text-red-500" />,
  processing: <Loader2 size={14} className="text-blue-500 animate-spin" />,
  pending: <Clock size={14} className="text-slate-400" />,
}

const STATUS_LABEL: Record<string, string> = {
  completed: 'Completed',
  completed_with_errors: 'Completed with errors',
  failed: 'Failed',
  processing: 'Processing…',
  pending: 'Pending',
}

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

export default function FeedsPage() {
  const [data, setData] = useState<FeedList | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

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
                <th className="px-4 py-3 font-medium text-slate-600 text-right">Found</th>
                <th className="px-4 py-3 font-medium text-slate-600 text-right">Ingested</th>
                <th className="px-4 py-3 font-medium text-slate-600 text-right">Failed</th>
                <th className="px-4 py-3 font-medium text-slate-600 text-right">Conflicts</th>
                <th className="px-4 py-3 font-medium text-slate-600">Submitted</th>
              </tr>
            </thead>
            <tbody>
              {data.feeds.map((feed) => (
                <tr key={feed.id} className="border-b border-slate-100 hover:bg-slate-50 transition-colors">
                  <td className="px-4 py-3">
                    <p className="font-medium text-slate-900 truncate max-w-48">
                      {feed.original_filename ?? 'Untitled'}
                    </p>
                    <p className="text-xs text-slate-400">
                      {feed.onix_version ? `ONIX ${feed.onix_version}` : ''}{' '}
                      {formatBytes(feed.file_size_bytes)}
                      {feed.gaps_detected && (
                        <span className="ml-2 text-amber-500 font-medium">⚠ sequence gap</span>
                      )}
                    </p>
                  </td>
                  <td className="px-4 py-3">
                    <span className="flex items-center gap-1.5">
                      {STATUS_ICON[feed.status] ?? STATUS_ICON.pending}
                      {STATUS_LABEL[feed.status] ?? feed.status}
                    </span>
                    {feed.error_detail && (
                      <p className="text-xs text-red-500 mt-0.5 truncate max-w-48" title={feed.error_detail}>
                        {feed.error_detail}
                      </p>
                    )}
                  </td>
                  <td className="px-4 py-3 text-right text-slate-700">{feed.records_found ?? '—'}</td>
                  <td className="px-4 py-3 text-right text-green-600 font-medium">
                    {feed.records_upserted ?? '—'}
                  </td>
                  <td className="px-4 py-3 text-right text-red-500">{feed.records_failed ?? '—'}</td>
                  <td className="px-4 py-3 text-right text-amber-500">{feed.records_conflicted ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-500 text-xs">{formatDate(feed.created_at)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
