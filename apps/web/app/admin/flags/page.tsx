'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, Loader2, ToggleLeft, ToggleRight } from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type Flag = {
  flag_name: string
  enabled: boolean
  description: string | null
  updated_at: string
  updated_by: string | null
}

// ── Human-readable names + descriptions ──────────────────────────────────────

const FLAG_META: Record<string, { label: string; hint: string }> = {
  ordering_enabled: {
    label: 'Ordering',
    hint: 'Show basket, orders, and quick order to all retailers. Flip once 50+ publishers are onboard.',
  },
  publisher_analytics: {
    label: 'Publisher Analytics',
    hint: 'Publishers can view their dashboard analytics.',
  },
  ai_suggestions: {
    label: 'AI Suggestions',
    hint: 'Enable AI-powered metadata review for publishers (Bedrock).',
  },
}

// ── Toggle row ────────────────────────────────────────────────────────────────

function FlagRow({ flag, onToggle }: { flag: Flag; onToggle: (name: string, enabled: boolean) => void }) {
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const meta = FLAG_META[flag.flag_name]

  const toggle = async () => {
    setSaving(true)
    setError(null)
    try {
      const res = await fetch('/api/admin/flags/global', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ flag_name: flag.flag_name, enabled: !flag.enabled }),
      })
      if (!res.ok) throw new Error((await res.json()).detail ?? 'Failed')
      onToggle(flag.flag_name, !flag.enabled)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="flex items-start justify-between py-5 px-6 border-b border-slate-100 last:border-0">
      <div className="flex-1 min-w-0 pr-8">
        <div className="flex items-center gap-2 mb-0.5">
          <p className="text-sm font-semibold text-slate-900">
            {meta?.label ?? flag.flag_name}
          </p>
          <code className="text-[10px] font-mono text-slate-400 bg-slate-100 px-1.5 py-0.5 rounded">
            {flag.flag_name}
          </code>
        </div>
        <p className="text-xs text-slate-500 mb-2">
          {meta?.hint ?? flag.description ?? 'No description'}
        </p>
        <p className="text-[10px] text-slate-400">
          Last updated {new Date(flag.updated_at).toLocaleString('en-GB', { dateStyle: 'medium', timeStyle: 'short' })}
          {flag.updated_by && ` by ${flag.updated_by.slice(0, 8)}…`}
        </p>
        {error && <p className="text-xs text-red-500 mt-1">{error}</p>}
      </div>
      <button
        onClick={toggle}
        disabled={saving}
        className={`flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
          ${flag.enabled
            ? 'bg-emerald-50 text-emerald-700 hover:bg-emerald-100'
            : 'bg-slate-100 text-slate-500 hover:bg-slate-200'
          }
          ${saving ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}
        `}
      >
        {saving ? (
          <Loader2 size={16} className="animate-spin" />
        ) : flag.enabled ? (
          <ToggleRight size={18} className="text-emerald-600" />
        ) : (
          <ToggleLeft size={18} />
        )}
        {flag.enabled ? 'On' : 'Off'}
      </button>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function AdminFlagsPage() {
  const [flags, setFlags] = useState<Flag[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/api/admin/flags/global')
      .then(r => r.json())
      .then(d => { setFlags(d); setLoading(false) })
      .catch(() => { setError('Failed to load flags'); setLoading(false) })
  }, [])

  const handleToggle = (name: string, enabled: boolean) => {
    setFlags(prev => prev.map(f => f.flag_name === name ? { ...f, enabled } : f))
  }

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-10">

      <div className="mb-8">
        <h1 className="text-2xl font-bold text-slate-900">Feature Flags</h1>
        <p className="text-sm text-slate-500 mt-1">Global toggles — changes apply immediately to all users</p>
      </div>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm flex items-center gap-2 mb-6">
          <AlertCircle size={14} /> {error}
        </div>
      )}

      {loading ? (
        <div className="flex justify-center py-24">
          <Loader2 className="animate-spin text-slate-400" size={24} />
        </div>
      ) : (
        <div className="bg-white border border-slate-200 rounded-xl divide-y divide-slate-100">
          {flags.length === 0 ? (
            <p className="text-sm text-slate-400 text-center py-12">No flags found</p>
          ) : (
            flags.map(f => (
              <FlagRow key={f.flag_name} flag={f} onToggle={handleToggle} />
            ))
          )}
        </div>
      )}

      <p className="text-xs text-slate-400 mt-4 text-center">
        Per-account overrides are managed via the API and apply on top of these global settings.
      </p>
    </div>
  )
}
