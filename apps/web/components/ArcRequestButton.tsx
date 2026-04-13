'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { FileDown, Loader2, CheckCircle2, XCircle, ChevronDown, ChevronUp } from 'lucide-react'

type ArcStatus = {
  has_request: boolean
  status: string | null
  decline_reason: string | null
  download_url: string | null
}

const TYPE_OPTIONS = [
  { value: 'retailer', label: 'Bookseller / Retailer' },
  { value: 'trade_press', label: 'Trade Press' },
  { value: 'blogger', label: 'Book Blogger' },
  { value: 'other', label: 'Other' },
]

export function ArcRequestButton({ isbn13, title }: { isbn13: string; title: string }) {
  const { data: session } = useSession()
  const [open, setOpen] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [submitted, setSubmitted] = useState(false)
  const [arcStatus, setArcStatus] = useState<ArcStatus | null>(null)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    requester_type: 'retailer',
    requester_name: session?.user?.name ?? '',
    requester_email: session?.user?.email ?? '',
    requester_company: '',
    requester_message: '',
  })

  async function checkStatus() {
    if (!form.requester_email) return
    const res = await fetch(`/api/arc/books/${isbn13}?email=${encodeURIComponent(form.requester_email)}`)
    if (res.ok) setArcStatus(await res.json())
  }

  async function handleOpen() {
    setOpen(o => !o)
    if (!open && form.requester_email) await checkStatus()
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSubmitting(true)
    setError('')
    try {
      const res = await fetch(`/api/arc/books/${isbn13}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(form),
      })
      if (res.status === 409) {
        const d = await res.json()
        setError(d.detail ?? 'You already have an active request for this title.')
        return
      }
      if (!res.ok) throw new Error('Request failed')
      setSubmitted(true)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  // If they already have an approved request with a download link
  if (arcStatus?.status === 'approved' && arcStatus.download_url) {
    return (
      <div className="mt-3 rounded-lg bg-green-50 border border-green-200 p-3">
        <div className="flex items-center gap-1.5 text-xs text-green-800 font-medium mb-2">
          <CheckCircle2 size={13} /> ARC approved
        </div>
        <a
          href={arcStatus.download_url}
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center justify-center gap-2 w-full py-2 text-xs font-medium bg-green-600 text-white rounded-lg hover:bg-green-700"
        >
          <FileDown size={13} /> Download ARC (PDF)
        </a>
      </div>
    )
  }

  if (arcStatus?.status === 'pending') {
    return (
      <div className="mt-3 rounded-lg bg-amber-50 border border-amber-200 p-3 text-xs text-amber-800">
        <div className="flex items-center gap-1.5 font-medium">
          <Loader2 size={12} className="animate-spin" /> ARC request pending
        </div>
        <p className="mt-1 text-amber-700">Your request is under review. We'll email you when the publisher decides.</p>
      </div>
    )
  }

  if (arcStatus?.status === 'declined') {
    return (
      <div className="mt-3 rounded-lg bg-red-50 border border-red-200 p-3 text-xs text-red-800">
        <div className="flex items-center gap-1.5 font-medium mb-1">
          <XCircle size={12} /> ARC request declined
        </div>
        {arcStatus.decline_reason && (
          <p className="text-red-700">{arcStatus.decline_reason}</p>
        )}
      </div>
    )
  }

  if (submitted) {
    return (
      <div className="mt-3 rounded-lg bg-green-50 border border-green-200 p-3 text-xs text-green-800">
        <div className="flex items-center gap-1.5 font-medium">
          <CheckCircle2 size={13} /> Request submitted
        </div>
        <p className="mt-1 text-green-700">The publisher will review and email you their decision.</p>
      </div>
    )
  }

  return (
    <div className="mt-3">
      <button
        onClick={handleOpen}
        className="flex items-center justify-between w-full gap-2 px-3 py-2 text-xs font-medium border border-slate-200 rounded-lg bg-white hover:bg-slate-50 text-slate-700 transition-colors"
      >
        <span className="flex items-center gap-1.5">
          <FileDown size={13} className="text-slate-400" /> Request Advance Reading Copy
        </span>
        {open ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>

      {open && (
        <form
          onSubmit={handleSubmit}
          className="mt-2 border border-slate-200 rounded-lg bg-white p-4 space-y-3"
        >
          <p className="text-xs text-slate-500">
            Request a PDF ARC of <em>{title}</em>. The publisher will review and email you.
          </p>

          {error && (
            <p className="text-xs text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2">{error}</p>
          )}

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">I am a</label>
            <select
              value={form.requester_type}
              onChange={e => setForm(f => ({ ...f, requester_type: e.target.value }))}
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-xs text-slate-800 focus:outline-none focus:ring-1 focus:ring-amber-400"
            >
              {TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Name <span className="text-red-500">*</span></label>
            <input
              required
              value={form.requester_name}
              onChange={e => setForm(f => ({ ...f, requester_name: e.target.value }))}
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-amber-400"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Email <span className="text-red-500">*</span></label>
            <input
              required
              type="email"
              value={form.requester_email}
              onChange={e => setForm(f => ({ ...f, requester_email: e.target.value }))}
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-amber-400"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Company / Publication</label>
            <input
              value={form.requester_company}
              onChange={e => setForm(f => ({ ...f, requester_company: e.target.value }))}
              placeholder="Optional"
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-xs focus:outline-none focus:ring-1 focus:ring-amber-400"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Why do you want this ARC?</label>
            <textarea
              value={form.requester_message}
              onChange={e => setForm(f => ({ ...f, requester_message: e.target.value }))}
              placeholder="Optional — helps the publisher decide"
              rows={2}
              className="w-full border border-slate-300 rounded-md px-2 py-1.5 text-xs resize-none focus:outline-none focus:ring-1 focus:ring-amber-400"
            />
          </div>

          <button
            type="submit"
            disabled={submitting}
            className="w-full flex items-center justify-center gap-2 py-2 text-xs font-medium bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50"
          >
            {submitting && <Loader2 size={12} className="animate-spin" />}
            {submitting ? 'Sending…' : 'Send ARC Request'}
          </button>
        </form>
      )}
    </div>
  )
}
