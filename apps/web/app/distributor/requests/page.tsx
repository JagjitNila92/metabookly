'use client'

import { useEffect, useState } from 'react'
import { Loader2, CheckCircle2, XCircle, Clock, ChevronDown } from 'lucide-react'

type Request = {
  id: string
  distributor_code: string
  distributor_name: string
  account_number: string | null
  status: string
  rejection_reason: string | null
  retailer: {
    id: string
    company_name: string
    email: string
  }
  created_at: string
  updated_at: string
}

const STATUS_TABS = [
  { label: 'Pending', value: 'pending' },
  { label: 'Approved', value: 'approved' },
  { label: 'Rejected', value: 'rejected' },
]

export default function DistributorRequestsPage() {
  const [requests, setRequests] = useState<Request[]>([])
  const [activeTab, setActiveTab] = useState('pending')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [actionId, setActionId] = useState<string | null>(null)
  const [rejectingId, setRejectingId] = useState<string | null>(null)
  const [rejectionReason, setRejectionReason] = useState('')

  const loadRequests = async (statusFilter: string) => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch(`/api/distributor/requests?status=${statusFilter}`)
      if (!res.ok) throw new Error(res.status === 403 ? 'Admin access required' : 'Failed to load requests')
      setRequests(await res.json())
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to load requests')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadRequests(activeTab)
  }, [activeTab])

  const approve = async (requestId: string) => {
    setActionId(requestId)
    try {
      const res = await fetch(`/api/distributor/requests/${requestId}/approve`, { method: 'POST' })
      if (!res.ok) throw new Error()
      setRequests((prev) => prev.filter((r) => r.id !== requestId))
    } catch {
      setError('Failed to approve request')
    } finally {
      setActionId(null)
    }
  }

  const reject = async (requestId: string) => {
    setActionId(requestId)
    try {
      const res = await fetch(`/api/distributor/requests/${requestId}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ rejection_reason: rejectionReason || null }),
      })
      if (!res.ok) throw new Error()
      setRequests((prev) => prev.filter((r) => r.id !== requestId))
      setRejectingId(null)
      setRejectionReason('')
    } catch {
      setError('Failed to reject request')
    } finally {
      setActionId(null)
    }
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Account Link Requests</h1>
        <p className="text-sm text-slate-500 mt-1">
          Review and approve retailer requests to link their trade accounts.
        </p>
      </div>

      {/* Status tabs */}
      <div className="flex gap-1 bg-slate-100 rounded-lg p-1 mb-6 w-fit">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.value}
            onClick={() => setActiveTab(tab.value)}
            className={`px-4 py-1.5 text-sm rounded-md transition-colors font-medium ${
              activeTab === tab.value
                ? 'bg-white text-slate-900 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-600 text-sm mb-6">
          {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-16">
          <Loader2 className="animate-spin text-slate-400" size={24} />
        </div>
      ) : requests.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <Clock size={32} className="mx-auto mb-3 opacity-50" />
          <p className="text-sm">No {activeTab} requests</p>
        </div>
      ) : (
        <div className="space-y-3">
          {requests.map((req) => (
            <div
              key={req.id}
              className="bg-white border border-slate-200 rounded-xl p-5"
            >
              <div className="flex items-start justify-between gap-4">
                <div className="min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <p className="text-sm font-semibold text-slate-900">{req.retailer.company_name}</p>
                    <span className="text-xs text-slate-400">{req.retailer.email}</span>
                  </div>
                  <p className="text-sm text-slate-600">
                    Requesting to link with <span className="font-medium">{req.distributor_name}</span>
                  </p>
                  {req.account_number && (
                    <p className="text-xs text-slate-500 mt-1">
                      Account number: <span className="font-mono">{req.account_number}</span>
                    </p>
                  )}
                  {req.rejection_reason && (
                    <p className="text-xs text-red-600 mt-1">Rejection reason: {req.rejection_reason}</p>
                  )}
                  <p className="text-xs text-slate-400 mt-2">
                    Submitted {new Date(req.created_at).toLocaleDateString('en-GB', {
                      day: 'numeric', month: 'short', year: 'numeric',
                    })}
                  </p>
                </div>

                {activeTab === 'pending' && (
                  <div className="flex flex-col gap-2 shrink-0">
                    <button
                      onClick={() => approve(req.id)}
                      disabled={actionId === req.id}
                      className="flex items-center gap-1.5 px-3 py-1.5 bg-green-500 hover:bg-green-600 disabled:opacity-60 text-white text-sm rounded-md"
                    >
                      {actionId === req.id
                        ? <Loader2 size={13} className="animate-spin" />
                        : <CheckCircle2 size={13} />}
                      Approve
                    </button>

                    {rejectingId === req.id ? (
                      <div className="w-56">
                        <input
                          value={rejectionReason}
                          onChange={(e) => setRejectionReason(e.target.value)}
                          placeholder="Reason (optional)"
                          className="w-full px-2 py-1.5 text-xs border border-slate-300 rounded-md mb-1.5 focus:outline-none focus:ring-1 focus:ring-red-400"
                          autoFocus
                        />
                        <div className="flex gap-1.5">
                          <button
                            onClick={() => reject(req.id)}
                            disabled={actionId === req.id}
                            className="flex-1 py-1.5 bg-red-500 hover:bg-red-600 disabled:opacity-60 text-white text-xs rounded-md"
                          >
                            Confirm reject
                          </button>
                          <button
                            onClick={() => { setRejectingId(null); setRejectionReason('') }}
                            className="px-2 py-1.5 border border-slate-300 text-slate-600 hover:bg-slate-50 text-xs rounded-md"
                          >
                            Cancel
                          </button>
                        </div>
                      </div>
                    ) : (
                      <button
                        onClick={() => setRejectingId(req.id)}
                        className="flex items-center gap-1.5 px-3 py-1.5 border border-red-300 text-red-600 hover:bg-red-50 text-sm rounded-md"
                      >
                        <XCircle size={13} />
                        Reject
                      </button>
                    )}
                  </div>
                )}

                {activeTab === 'approved' && (
                  <span className="flex items-center gap-1.5 text-xs text-green-700 font-medium shrink-0">
                    <CheckCircle2 size={14} /> Approved
                  </span>
                )}

                {activeTab === 'rejected' && (
                  <span className="flex items-center gap-1.5 text-xs text-red-600 font-medium shrink-0">
                    <XCircle size={14} /> Rejected
                  </span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
