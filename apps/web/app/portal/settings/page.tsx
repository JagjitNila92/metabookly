'use client'

import { useEffect, useState } from 'react'
import { Key, Plus, Trash2, Copy, Check, AlertTriangle, Loader2 } from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ApiKey {
  id: string
  key_prefix: string
  label: string | null
  created_at: string
  last_used_at: string | null
}

interface NewKey extends ApiKey {
  plaintext_key: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function fmtDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

// ── Copy button ───────────────────────────────────────────────────────────────

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  const copy = async () => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }
  return (
    <button onClick={copy} className="ml-2 text-slate-400 hover:text-slate-600 transition-colors" title="Copy">
      {copied ? <Check size={14} className="text-green-500" /> : <Copy size={14} />}
    </button>
  )
}

// ── New key reveal banner ─────────────────────────────────────────────────────

function NewKeyBanner({ newKey, onDismiss }: { newKey: NewKey; onDismiss: () => void }) {
  return (
    <div className="bg-green-50 border border-green-300 rounded-lg p-4 mb-6">
      <div className="flex items-start gap-3">
        <Check size={18} className="text-green-600 mt-0.5 shrink-0" />
        <div className="flex-1 min-w-0">
          <p className="text-sm font-semibold text-green-800 mb-1">API key created — copy it now</p>
          <p className="text-xs text-green-700 mb-3">
            This is the only time the full key will be shown. Store it somewhere safe.
          </p>
          <div className="flex items-center gap-2 bg-white border border-green-200 rounded px-3 py-2">
            <code className="text-xs font-mono text-slate-800 break-all flex-1">
              {newKey.plaintext_key}
            </code>
            <CopyButton text={newKey.plaintext_key} />
          </div>
        </div>
      </div>
      <button
        onClick={onDismiss}
        className="mt-3 text-xs text-green-700 underline hover:no-underline"
      >
        I've saved the key — dismiss
      </button>
    </div>
  )
}

// ── Create key modal ──────────────────────────────────────────────────────────

function CreateKeyModal({ onClose, onCreate }: { onClose: () => void; onCreate: (key: NewKey) => void }) {
  const [label, setLabel] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleCreate = async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/portal/api-keys', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ label: label.trim() || null }),
      })
      const data = await res.json()
      if (!res.ok) {
        setError(data.detail ?? data.error ?? 'Could not create key')
        return
      }
      onCreate(data as NewKey)
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-xl shadow-xl max-w-md w-full p-6">
        <h2 className="text-base font-semibold text-slate-900 mb-1">Create API key</h2>
        <p className="text-sm text-slate-500 mb-4">
          Use API keys to upload ONIX feeds programmatically without signing in.
        </p>
        <label className="block text-sm font-medium text-slate-700 mb-1">
          Label <span className="text-slate-400 font-normal">(optional)</span>
        </label>
        <input
          type="text"
          value={label}
          onChange={e => setLabel(e.target.value)}
          placeholder="e.g. CI pipeline, FTP automation"
          className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 mb-4"
        />
        {error && (
          <p className="text-sm text-red-600 bg-red-50 border border-red-200 rounded px-3 py-2 mb-4">{error}</p>
        )}
        <div className="flex gap-3 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-800">Cancel</button>
          <button
            onClick={handleCreate}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white text-sm font-medium rounded-md transition-colors"
          >
            {loading && <Loader2 size={14} className="animate-spin" />}
            {loading ? 'Creating…' : 'Create key'}
          </button>
        </div>
      </div>
    </div>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function PortalSettingsPage() {
  const [keys, setKeys]           = useState<ApiKey[]>([])
  const [loading, setLoading]     = useState(true)
  const [showCreate, setShowCreate] = useState(false)
  const [newKey, setNewKey]       = useState<NewKey | null>(null)
  const [revoking, setRevoking]   = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/portal/api-keys', { cache: 'no-store' })
      if (res.ok) setKeys(await res.json())
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  const handleCreated = (key: NewKey) => {
    setShowCreate(false)
    setNewKey(key)
    load()
  }

  const handleRevoke = async (prefix: string) => {
    if (!confirm(`Revoke key ${prefix}? Any automation using it will stop working immediately.`)) return
    setRevoking(prefix)
    try {
      await fetch(`/api/portal/api-keys/${encodeURIComponent(prefix)}`, { method: 'DELETE' })
      setKeys(prev => prev.filter(k => k.key_prefix !== prefix))
      if (newKey?.key_prefix === prefix) setNewKey(null)
    } finally {
      setRevoking(null)
    }
  }

  return (
    <div className="max-w-2xl">
      <h1 className="text-xl font-semibold text-slate-900 mb-1">Settings</h1>
      <p className="text-sm text-slate-500 mb-8">Manage your publisher account settings.</p>

      {/* API Keys section */}
      <section>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <Key size={16} className="text-slate-500" />
            <h2 className="text-sm font-semibold text-slate-900">API Keys</h2>
          </div>
          <button
            onClick={() => setShowCreate(true)}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white font-medium rounded-md transition-colors"
          >
            <Plus size={13} />
            New key
          </button>
        </div>

        <p className="text-xs text-slate-500 mb-4">
          API keys let you upload ONIX feeds programmatically. A key is shown only once at creation —
          store it securely. Maximum 5 active keys.
        </p>

        {newKey && (
          <NewKeyBanner newKey={newKey} onDismiss={() => setNewKey(null)} />
        )}

        {loading ? (
          <div className="flex items-center gap-2 text-sm text-slate-400 py-4">
            <Loader2 size={14} className="animate-spin" /> Loading…
          </div>
        ) : keys.length === 0 ? (
          <div className="border border-dashed border-slate-300 rounded-lg p-6 text-center">
            <Key size={20} className="text-slate-300 mx-auto mb-2" />
            <p className="text-sm text-slate-500">No API keys yet.</p>
            <p className="text-xs text-slate-400 mt-1">Create one to upload feeds programmatically.</p>
          </div>
        ) : (
          <div className="border border-slate-200 rounded-lg divide-y divide-slate-100 overflow-hidden">
            {keys.map(k => (
              <div key={k.id} className="flex items-center gap-4 px-4 py-3 bg-white">
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <code className="text-xs font-mono text-slate-700 bg-slate-100 px-1.5 py-0.5 rounded">
                      {k.key_prefix}…
                    </code>
                    {k.label && (
                      <span className="text-xs text-slate-500">{k.label}</span>
                    )}
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Created {fmtDate(k.created_at)}
                    {k.last_used_at && ` · Last used ${fmtDate(k.last_used_at)}`}
                    {!k.last_used_at && ' · Never used'}
                  </p>
                </div>
                <button
                  onClick={() => handleRevoke(k.key_prefix)}
                  disabled={revoking === k.key_prefix}
                  className="flex items-center gap-1 text-xs text-red-500 hover:text-red-700 disabled:opacity-50 transition-colors"
                  title="Revoke key"
                >
                  {revoking === k.key_prefix
                    ? <Loader2 size={13} className="animate-spin" />
                    : <Trash2 size={13} />
                  }
                  Revoke
                </button>
              </div>
            ))}
          </div>
        )}

        {/* Usage guidance */}
        <div className="mt-4 bg-slate-50 border border-slate-200 rounded-lg p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle size={14} className="text-amber-500 mt-0.5 shrink-0" />
            <div className="text-xs text-slate-600 space-y-1">
              <p><strong>How to use:</strong> Pass your key as the <code className="bg-slate-100 px-1 rounded">X-API-Key</code> header when requesting an upload URL.</p>
              <p className="font-mono bg-slate-100 rounded px-2 py-1 text-slate-700 break-all">
                POST /api/v1/portal/upload-url?filename=catalog.xml
              </p>
              <p>Then PUT your ONIX file to the returned pre-signed S3 URL, and call the trigger endpoint to process it.</p>
            </div>
          </div>
        </div>
      </section>

      {showCreate && (
        <CreateKeyModal
          onClose={() => setShowCreate(false)}
          onCreate={handleCreated}
        />
      )}
    </div>
  )
}
