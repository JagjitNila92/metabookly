'use client'

import { useEffect, useState } from 'react'
import { CheckCircle2, XCircle, Clock, Loader2, ChevronDown, ChevronUp } from 'lucide-react'

type ArcRequest = {
  id: string
  book_id: string
  isbn13: string
  title: string
  requester_type: string
  requester_name: string
  requester_email: string
  requester_company: string | null
  requester_message: string | null
  status: string
  decline_reason: string | null
  approved_expires_at: string | null
  reviewed_at: string | null
  created_at: string
}

type ArcList = { items: ArcRequest[]; total: number; pending_count: number }

const TYPE_LABELS: Record<string, string> = {
  retailer: 'Bookseller',
  trade_press: 'Trade Press',
  blogger: 'Book Blogger',
  other: 'Other',
}

function StatusBadge({ status }: { status: string }) {
  if (status === 'pending') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-amber-100 text-amber-800">
      <Clock size={11} /> Pending
    </span>
  )
  if (status === 'approved') return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-green-100 text-green-800">
      <CheckCircle2 size={11} /> Approved
    </span>
  )
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs font-medium bg-red-100 text-red-800">
      <XCircle size={11} /> Declined
    </span>
  )
}

function DeclineModal({
  onConfirm,
  onCancel,
  loading,
}: {
  onConfirm: (reason: string) => void
  onCancel: () => void
  loading: boolean
}) {
  const [reason, setReason] = useState('')
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h3 className="text-base font-semibold text-slate-900 mb-1">Decline ARC Request</h3>
        <p className="text-sm text-slate-500 mb-4">
          Provide a reason — this will be sent to the requester. Be brief and professional.
        </p>
        <textarea
          className="w-full border border-slate-300 rounded-lg px-3 py-2 text-sm text-slate-800 min-h-[100px] resize-none focus:outline-none focus:ring-2 focus:ring-amber-400"
          placeholder="e.g. We are not distributing ARCs for this title at this stage."
          value={reason}
          onChange={e => setReason(e.target.value)}
        />
        <div className="flex gap-3 mt-4 justify-end">
          <button onClick={onCancel} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900">
            Cancel
          </button>
          <button
            onClick={() => onConfirm(reason)}
            disabled={!reason.trim() || loading}
            className="px-4 py-2 text-sm font-medium bg-red-600 text-white rounded-lg hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            Decline with reason
          </button>
        </div>
      </div>
    </div>
  )
}

function RequestRow({ req, onDecide }: { req: ArcRequest; onDecide: (r: ArcRequest) => void }) {
  const [expanded, setExpanded] = useState(false)
  return (
    <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
      <div className="flex items-start gap-4 px-5 py-4">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="text-sm font-medium text-slate-900 truncate">{req.requester_name}</span>
            <span className="text-xs text-slate-400">·</span>
            <span className="text-xs text-slate-500">{TYPE_LABELS[req.requester_type] ?? req.requester_type}</span>
            {req.requester_company && (
              <span className="text-xs text-slate-400">· {req.requester_company}</span>
            )}
          </div>
          <p className="text-xs text-slate-500 mb-1">{req.requester_email}</p>
          <p className="text-xs text-slate-600 font-medium truncate">{req.title}</p>
          <p className="text-xs text-slate-400">ISBN {req.isbn13} · {new Date(req.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</p>
        </div>
        <div className="flex items-center gap-3 shrink-0">
          <StatusBadge status={req.status} />
          {req.requester_message && (
            <button
              onClick={() => setExpanded(v => !v)}
              className="text-slate-400 hover:text-slate-600"
              title="View message"
            >
              {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
            </button>
          )}
          {req.status === 'pending' && (
            <button
              onClick={() => onDecide(req)}
              className="text-xs text-slate-500 hover:text-slate-800 underline underline-offset-2"
            >
              Review
            </button>
          )}
        </div>
      </div>
      {expanded && req.requester_message && (
        <div className="px-5 pb-4 pt-0">
          <div className="bg-slate-50 border border-slate-100 rounded-lg px-4 py-3">
            <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Message</p>
            <p className="text-sm text-slate-700">{req.requester_message}</p>
          </div>
        </div>
      )}
      {req.status === 'declined' && req.decline_reason && (
        <div className="px-5 pb-4 pt-0">
          <div className="bg-red-50 border border-red-100 rounded-lg px-4 py-3">
            <p className="text-xs font-semibold text-red-400 uppercase tracking-wider mb-1">Decline reason sent to requester</p>
            <p className="text-sm text-red-700">{req.decline_reason}</p>
          </div>
        </div>
      )}
    </div>
  )
}

type DeclineTarget = { req: ArcRequest; action: 'approve' | 'decline' } | null

export default function ArcRequestsPage() {
  const [data, setData] = useState<ArcList | null>(null)
  const [filter, setFilter] = useState<string>('')
  const [declineTarget, setDeclineTarget] = useState<DeclineTarget>(null)
  const [acting, setActing] = useState(false)
  const [error, setError] = useState('')

  async function load(status?: string) {
    const qs = status ? `?status=${status}` : ''
    const res = await fetch(`/api/portal/arcs${qs}`)
    if (res.ok) setData(await res.json())
  }

  useEffect(() => { load(filter || undefined) }, [filter])

  async function handleReview(req: ArcRequest) {
    // Approve immediately; decline opens modal
    setDeclineTarget({ req, action: 'approve' })
    setActing(true)
    await doDecide(req.id, 'approve', undefined)
    setActing(false)
    setDeclineTarget(null)
  }

  async function openDecline(req: ArcRequest) {
    setDeclineTarget({ req, action: 'decline' })
  }

  async function doDecide(requestId: string, action: string, declineReason?: string) {
    setActing(true)
    setError('')
    try {
      const res = await fetch(`/api/portal/arcs/${requestId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ action, decline_reason: declineReason }),
      })
      if (!res.ok) {
        const d = await res.json()
        setError(d.detail ?? 'Something went wrong')
        return
      }
      await load(filter || undefined)
      setDeclineTarget(null)
    } finally {
      setActing(false)
    }
  }

  const FILTERS = [
    { value: '', label: 'All' },
    { value: 'pending', label: 'Pending' },
    { value: 'approved', label: 'Approved' },
    { value: 'declined', label: 'Declined' },
  ]

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">ARC Requests</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Advance Reading Copy requests from booksellers and trade contacts.
          </p>
        </div>
        {data && data.pending_count > 0 && (
          <span className="inline-flex items-center gap-1.5 px-3 py-1.5 bg-amber-100 text-amber-800 text-sm font-medium rounded-full">
            <Clock size={13} />
            {data.pending_count} pending
          </span>
        )}
      </div>

      {/* Filter tabs */}
      <div className="flex gap-1 mb-5 bg-white border border-slate-200 rounded-lg p-1 w-fit">
        {FILTERS.map(f => (
          <button
            key={f.value}
            onClick={() => setFilter(f.value)}
            className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
              filter === f.value
                ? 'bg-slate-900 text-white font-medium'
                : 'text-slate-600 hover:text-slate-900'
            }`}
          >
            {f.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-sm text-red-700">
          {error}
        </div>
      )}

      {!data ? (
        <div className="flex items-center gap-2 text-slate-400 py-8">
          <Loader2 size={16} className="animate-spin" />
          Loading…
        </div>
      ) : data.items.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <p className="text-base">No ARC requests yet</p>
          <p className="text-sm mt-1">
            Requests appear here once you enable ARC on a title and upload a PDF.
          </p>
        </div>
      ) : (
        <div className="space-y-3">
          {data.items.map(req => (
            <div key={req.id}>
              {/* Quick approve / open decline modal inline */}
              {req.status === 'pending' ? (
                <div className="bg-white border border-slate-200 rounded-lg overflow-hidden">
                  <div className="flex items-start gap-4 px-5 py-4">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-sm font-medium text-slate-900 truncate">{req.requester_name}</span>
                        <span className="text-xs text-slate-400">·</span>
                        <span className="text-xs text-slate-500">{TYPE_LABELS[req.requester_type] ?? req.requester_type}</span>
                        {req.requester_company && <span className="text-xs text-slate-400">· {req.requester_company}</span>}
                      </div>
                      <p className="text-xs text-slate-500 mb-1">{req.requester_email}</p>
                      <p className="text-xs text-slate-600 font-medium truncate">{req.title}</p>
                      <p className="text-xs text-slate-400">ISBN {req.isbn13} · {new Date(req.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })}</p>
                      {req.requester_message && (
                        <div className="mt-2 bg-slate-50 rounded-lg px-3 py-2">
                          <p className="text-xs text-slate-600 italic">"{req.requester_message}"</p>
                        </div>
                      )}
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <StatusBadge status={req.status} />
                      <button
                        onClick={() => doDecide(req.id, 'approve')}
                        disabled={acting}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:opacity-50"
                      >
                        <CheckCircle2 size={13} /> Approve
                      </button>
                      <button
                        onClick={() => setDeclineTarget({ req, action: 'decline' })}
                        disabled={acting}
                        className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white border border-red-300 text-red-600 rounded-lg hover:bg-red-50 disabled:opacity-50"
                      >
                        <XCircle size={13} /> Decline
                      </button>
                    </div>
                  </div>
                </div>
              ) : (
                <RequestRow req={req} onDecide={() => {}} />
              )}
            </div>
          ))}
        </div>
      )}

      {declineTarget?.action === 'decline' && (
        <DeclineModal
          loading={acting}
          onCancel={() => setDeclineTarget(null)}
          onConfirm={reason => doDecide(declineTarget.req.id, 'decline', reason)}
        />
      )}
    </div>
  )
}
