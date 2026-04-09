'use client'

import { useEffect, useState } from 'react'
import {
  Plus, AlertCircle, Loader2, CheckCircle2, Eye, EyeOff, X, Building2,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type Publisher = {
  id: string
  name: string
  contact_email: string | null
  source_type: string
  distributor_code: string | null
  managed_by: string
  active: boolean
  created_at: string
}

type CreateResult = {
  feed_source: Publisher
  temp_password: string
}

type FormState = {
  company_name: string
  contact_email: string
  contact_name: string
  distributor_code: string
  source_type: string
}

const EMPTY_FORM: FormState = {
  company_name: '',
  contact_email: '',
  contact_name: '',
  distributor_code: '',
  source_type: 'publisher',
}

// ── Success card (shown after creation) ──────────────────────────────────────

function CreatedCard({
  result,
  onDismiss,
}: { result: CreateResult; onDismiss: () => void }) {
  const [showPassword, setShowPassword] = useState(false)
  const [copied, setCopied] = useState(false)

  const copy = () => {
    navigator.clipboard.writeText(result.temp_password)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-6 mb-6">
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-2">
          <CheckCircle2 size={18} className="text-emerald-600 shrink-0" />
          <p className="text-sm font-semibold text-emerald-900">
            Publisher account created — {result.feed_source.name}
          </p>
        </div>
        <button onClick={onDismiss} className="text-emerald-400 hover:text-emerald-600 transition-colors">
          <X size={16} />
        </button>
      </div>
      <p className="text-xs text-emerald-700 mb-3">
        A welcome email with login instructions has been sent to{' '}
        <strong>{result.feed_source.contact_email}</strong>.
        The temporary password is shown below — save it now, it won&apos;t be shown again.
      </p>
      <div className="flex items-center gap-2">
        <div className="flex-1 flex items-center bg-white border border-emerald-300 rounded-lg px-3 py-2 font-mono text-sm">
          <span className="flex-1">{showPassword ? result.temp_password : '••••••••••••••••'}</span>
          <button
            onClick={() => setShowPassword(s => !s)}
            className="text-slate-400 hover:text-slate-600 ml-2"
          >
            {showPassword ? <EyeOff size={14} /> : <Eye size={14} />}
          </button>
        </div>
        <button
          onClick={copy}
          className={`px-3 py-2 rounded-lg text-xs font-medium transition-colors ${
            copied
              ? 'bg-emerald-600 text-white'
              : 'bg-white border border-emerald-300 text-emerald-700 hover:bg-emerald-100'
          }`}
        >
          {copied ? 'Copied!' : 'Copy'}
        </button>
      </div>
    </div>
  )
}

// ── Invite form panel ─────────────────────────────────────────────────────────

function InviteForm({
  onCreated,
  onCancel,
}: { onCreated: (result: CreateResult) => void; onCancel: () => void }) {
  const [form, setForm] = useState<FormState>(EMPTY_FORM)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (k: keyof FormState, v: string) => setForm(f => ({ ...f, [k]: v }))

  const submit = async (e: React.FormEvent) => {
    e.preventDefault()
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/admin/publishers', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          company_name: form.company_name,
          contact_email: form.contact_email,
          contact_name: form.contact_name,
          distributor_code: form.distributor_code || null,
          source_type: form.source_type,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail ?? data.error ?? 'Failed to create publisher')
      onCreated(data)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6">
      <div className="flex items-center justify-between mb-5">
        <h2 className="text-sm font-semibold text-slate-900">Invite Publisher</h2>
        <button onClick={onCancel} className="text-slate-400 hover:text-slate-600 transition-colors">
          <X size={16} />
        </button>
      </div>

      <form onSubmit={submit} className="space-y-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Company name" required>
            <input
              value={form.company_name}
              onChange={e => set('company_name', e.target.value)}
              required
              placeholder="e.g. Faber & Faber"
              className={INPUT}
            />
          </Field>
          <Field label="Contact name" required>
            <input
              value={form.contact_name}
              onChange={e => set('contact_name', e.target.value)}
              required
              placeholder="e.g. Sarah Jones"
              className={INPUT}
            />
          </Field>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Contact email" required hint="This becomes their login username">
            <input
              type="email"
              value={form.contact_email}
              onChange={e => set('contact_email', e.target.value)}
              required
              placeholder="sarah@faberfaber.com"
              className={INPUT}
            />
          </Field>
          <Field label="Distributor code" hint="Which distributor carries their titles (e.g. gardners)">
            <input
              value={form.distributor_code}
              onChange={e => set('distributor_code', e.target.value)}
              placeholder="gardners"
              className={INPUT}
            />
          </Field>
        </div>

        <Field label="Account type">
          <select
            value={form.source_type}
            onChange={e => set('source_type', e.target.value)}
            className={INPUT}
          >
            <option value="publisher">Publisher</option>
            <option value="aggregator">Aggregator</option>
          </select>
        </Field>

        {error && (
          <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-lg p-3">
            <AlertCircle size={14} className="shrink-0" />
            {error}
          </div>
        )}

        <div className="flex items-center gap-3 pt-1">
          <button
            type="submit"
            disabled={saving}
            className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white text-sm font-medium rounded-lg transition-colors"
          >
            {saving && <Loader2 size={14} className="animate-spin" />}
            {saving ? 'Creating account…' : 'Create publisher account'}
          </button>
          <button
            type="button"
            onClick={onCancel}
            className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900 transition-colors"
          >
            Cancel
          </button>
        </div>
      </form>
    </div>
  )
}

const INPUT = "w-full px-3 py-2 text-sm border border-slate-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-amber-400 bg-white"

function Field({
  label, required, hint, children,
}: { label: string; required?: boolean; hint?: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-xs font-medium text-slate-700 mb-1">
        {label}
        {required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
      {hint && <p className="text-xs text-slate-400 mt-1">{hint}</p>}
    </div>
  )
}

// ── Publisher row ─────────────────────────────────────────────────────────────

const SOURCE_TYPE_BADGE: Record<string, string> = {
  publisher:   'bg-blue-100 text-blue-700',
  aggregator:  'bg-violet-100 text-violet-700',
  distributor: 'bg-amber-100 text-amber-700',
}

function PublisherRow({ pub }: { pub: Publisher }) {
  return (
    <div className="grid grid-cols-12 px-5 py-3 items-center hover:bg-slate-50 transition-colors border-b border-slate-100 last:border-0">
      <div className="col-span-4 min-w-0 pr-3">
        <div className="flex items-center gap-2">
          <Building2 size={14} className="text-slate-400 shrink-0" />
          <p className="text-sm font-medium text-slate-900 truncate">{pub.name}</p>
        </div>
        {!pub.active && (
          <span className="text-[10px] font-medium text-red-500 uppercase">Inactive</span>
        )}
      </div>
      <div className="col-span-3 min-w-0 pr-3">
        <p className="text-sm text-slate-500 truncate">{pub.contact_email ?? '—'}</p>
      </div>
      <div className="col-span-2 min-w-0 pr-3">
        <p className="text-sm text-slate-500 font-mono text-xs">{pub.distributor_code ?? '—'}</p>
      </div>
      <div className="col-span-2">
        <span className={`inline-block px-2 py-0.5 rounded-full text-xs font-medium ${SOURCE_TYPE_BADGE[pub.source_type] ?? 'bg-slate-100 text-slate-600'}`}>
          {pub.source_type}
        </span>
      </div>
      <div className="col-span-1 text-right">
        <p className="text-xs text-slate-400">
          {new Date(pub.created_at).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: '2-digit' })}
        </p>
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminPublishersPage() {
  const [publishers, setPublishers] = useState<Publisher[]>([])
  const [loading, setLoading]       = useState(true)
  const [error, setError]           = useState<string | null>(null)
  const [showForm, setShowForm]     = useState(false)
  const [created, setCreated]       = useState<CreateResult | null>(null)

  const load = async () => {
    try {
      const res = await fetch('/api/admin/publishers')
      if (!res.ok) throw new Error('Failed to load')
      setPublishers(await res.json())
    } catch {
      setError('Failed to load publishers')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreated = (result: CreateResult) => {
    setShowForm(false)
    setCreated(result)
    setPublishers(prev => [result.feed_source, ...prev])
  }

  return (
    <div className="max-w-6xl mx-auto px-4 sm:px-6 py-10">

      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Publishers</h1>
          {!loading && (
            <p className="text-sm text-slate-500 mt-0.5">{publishers.length} feed source{publishers.length !== 1 ? 's' : ''}</p>
          )}
        </div>
        {!showForm && (
          <button
            onClick={() => { setShowForm(true); setCreated(null) }}
            className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium rounded-lg transition-colors"
          >
            <Plus size={14} />
            Invite publisher
          </button>
        )}
      </div>

      {/* Success card (one-time password display) */}
      {created && (
        <CreatedCard result={created} onDismiss={() => setCreated(null)} />
      )}

      {/* Invite form */}
      {showForm && (
        <InviteForm
          onCreated={handleCreated}
          onCancel={() => setShowForm(false)}
        />
      )}

      {/* Error */}
      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm flex items-center gap-2 mb-4">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {/* Publisher list */}
      <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
        {/* Header row */}
        <div className="grid grid-cols-12 px-5 py-2.5 text-xs font-medium text-slate-400 uppercase tracking-wider bg-slate-50 border-b border-slate-100">
          <div className="col-span-4">Company</div>
          <div className="col-span-3">Email</div>
          <div className="col-span-2">Distributor</div>
          <div className="col-span-2">Type</div>
          <div className="col-span-1 text-right">Added</div>
        </div>

        {loading ? (
          <div className="flex justify-center py-16">
            <Loader2 className="animate-spin text-slate-400" size={20} />
          </div>
        ) : publishers.length === 0 ? (
          <div className="flex flex-col items-center py-16 text-center">
            <Building2 size={28} className="text-slate-200 mb-3" />
            <p className="text-sm text-slate-400 mb-4">No publishers yet</p>
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 text-white text-sm font-medium rounded-lg transition-colors"
            >
              <Plus size={14} />
              Invite your first publisher
            </button>
          </div>
        ) : (
          <div>
            {publishers.map(p => <PublisherRow key={p.id} pub={p} />)}
          </div>
        )}
      </div>

    </div>
  )
}
