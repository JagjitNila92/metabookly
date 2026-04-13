'use client'

import { useParams } from 'next/navigation'
import { useEffect, useRef, useState } from 'react'
import {
  Upload, Trash2, Loader2, CheckCircle2, AlertCircle, ImageOff,
  History, ChevronDown, ChevronUp, RotateCcw, ArrowLeft,
  PenLine, Info, RefreshCw, FileDown,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type BookDetail = {
  isbn13: string
  isbn10: string | null
  title: string
  subtitle: string | null
  product_form: string | null
  page_count: number | null
  publication_date: string | null
  publishing_status: string | null
  uk_rights: boolean | null
  rrp_gbp: string | null
  cover_image_url: string | null
  height_mm: number | null
  width_mm: number | null
  metadata_score: number | null
  description: string | null
  toc: string | null
  excerpt: string | null
  field_sources: Record<string, string>
  onix_description: string | null
  onix_toc: string | null
  onix_excerpt: string | null
  arc_enabled: boolean
  arc_s3_key: string | null
}

type BookVersion = {
  id: string
  version_number: number
  changed_by: string
  snapshot: Record<string, unknown>
  created_at: string
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function formatDate(s: string) {
  return new Date(s).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function changedByLabel(raw: string) {
  if (raw.startsWith('onix:')) return 'ONIX feed upload'
  if (raw.startsWith('editorial:')) return 'Manually edited in portal'
  if (raw.startsWith('ai:')) return 'AI suggestion accepted'
  if (raw.startsWith('restore:')) return 'Rolled back to earlier version'
  return raw
}

function scoreBg(score: number | null) {
  if (score === null) return 'bg-slate-100 text-slate-500'
  if (score >= 80) return 'bg-green-100 text-green-700'
  if (score >= 60) return 'bg-amber-100 text-amber-700'
  return 'bg-red-100 text-red-600'
}

// ── Source badge ──────────────────────────────────────────────────────────────

function SourceBadge({ source }: { source: string | undefined }) {
  if (!source || source === 'onix') return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-blue-50 text-blue-600 border border-blue-100">from ONIX feed</span>
  )
  if (source === 'editorial') return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-purple-50 text-purple-600 border border-purple-100">manually edited</span>
  )
  if (source === 'ai_accepted') return (
    <span className="text-xs px-2 py-0.5 rounded-full bg-amber-50 text-amber-600 border border-amber-100">AI suggestion</span>
  )
  return null
}

// ── Read-only field row ───────────────────────────────────────────────────────

function ReadOnlyField({ label, value, tip }: { label: string; value: string | null | undefined; tip?: string }) {
  return (
    <div className="py-3 border-b border-slate-100 last:border-0">
      <div className="flex items-center gap-1.5 mb-0.5">
        <p className="text-xs font-medium text-slate-500">{label}</p>
        {tip && (
          <span className="group relative">
            <Info size={11} className="text-slate-300 cursor-help" />
            <span className="hidden group-hover:block absolute left-4 top-0 z-10 w-52 bg-slate-800 text-white text-xs rounded-md px-2.5 py-1.5 shadow-lg">
              {tip}
            </span>
          </span>
        )}
      </div>
      <p className={`text-sm ${value ? 'text-slate-800' : 'text-slate-300 italic'}`}>
        {value ?? 'Not set in ONIX feed'}
      </p>
    </div>
  )
}

// ── Editable text field ───────────────────────────────────────────────────────

function EditableField({
  label, value, source, onixValue, placeholder, multiline = false, rows = 4, saving, onSave,
}: {
  label: string
  value: string | null
  source: string | undefined
  onixValue: string | null
  placeholder: string
  multiline?: boolean
  rows?: number
  saving: boolean
  onSave: (val: string) => Promise<void>
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft]     = useState(value ?? '')
  const hasOverride = source === 'editorial' || source === 'ai_accepted'
  const showOnixDiff = hasOverride && onixValue && onixValue !== value

  return (
    <div className="py-4 border-b border-slate-100 last:border-0">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="flex items-center gap-2">
          <p className="text-sm font-medium text-slate-700">{label}</p>
          <SourceBadge source={source} />
        </div>
        {!editing && (
          <button
            onClick={() => { setDraft(value ?? ''); setEditing(true) }}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-purple-600 transition-colors"
          >
            <PenLine size={12} /> Edit
          </button>
        )}
      </div>

      {editing ? (
        <div>
          {multiline ? (
            <textarea
              value={draft}
              onChange={e => setDraft(e.target.value)}
              rows={rows}
              placeholder={placeholder}
              className="w-full text-sm border border-purple-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-400 resize-y"
            />
          ) : (
            <input
              value={draft}
              onChange={e => setDraft(e.target.value)}
              placeholder={placeholder}
              className="w-full text-sm border border-purple-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-purple-400"
            />
          )}
          <div className="flex items-center gap-2 mt-2">
            <button
              onClick={async () => { await onSave(draft); setEditing(false) }}
              disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-purple-600 hover:bg-purple-700 text-white text-xs rounded-md transition-colors disabled:opacity-50"
            >
              {saving ? <Loader2 size={11} className="animate-spin" /> : <CheckCircle2 size={11} />}
              Save change
            </button>
            <button
              onClick={() => setEditing(false)}
              className="text-xs text-slate-400 hover:text-slate-600"
            >
              Cancel
            </button>
          </div>
          <p className="text-xs text-slate-400 mt-2 flex items-start gap-1">
            <Info size={11} className="shrink-0 mt-0.5" />
            This saves to your Metabookly record only. To keep your ONIX feed in sync, update it in your publishing system too.
          </p>
        </div>
      ) : (
        <div>
          {value ? (
            <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{value}</p>
          ) : (
            <p className="text-sm text-slate-300 italic">{placeholder.replace('Enter ', 'No ')}</p>
          )}
          {showOnixDiff && (
            <details className="mt-2">
              <summary className="text-xs text-blue-500 cursor-pointer hover:text-blue-700">
                ONIX feed has a different value — click to see
              </summary>
              <p className="text-xs text-slate-500 mt-1 bg-blue-50 rounded p-2 border border-blue-100 leading-relaxed">
                {onixValue}
              </p>
            </details>
          )}
        </div>
      )}
    </div>
  )
}

// ── ARC panel ─────────────────────────────────────────────────────────────────

function ArcPanel({
  isbn13,
  arcEnabled,
  arcS3Key,
  onUpdate,
}: {
  isbn13: string
  arcEnabled: boolean
  arcS3Key: string | null
  onUpdate: () => void
}) {
  const arcFileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)
  const [removing, setRemoving] = useState(false)
  const [arcError, setArcError] = useState('')

  const handleArcUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (file.type !== 'application/pdf') { setArcError('Only PDF files are supported.'); return }
    setUploading(true)
    setArcError('')
    try {
      // 1. Get presigned URL
      const urlRes = await fetch(`/api/portal/books/${isbn13}/arc`)
      if (!urlRes.ok) throw new Error('Failed to get upload URL')
      const { upload_url, s3_key } = await urlRes.json()

      // 2. Upload directly to S3
      const putRes = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': 'application/pdf' },
      })
      if (!putRes.ok) throw new Error('Upload to S3 failed')

      // 3. Confirm
      const confirmRes = await fetch(`/api/portal/books/${isbn13}/arc`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ s3_key, original_filename: file.name }),
      })
      if (!confirmRes.ok) throw new Error('Failed to confirm upload')
      onUpdate()
    } catch (err: any) {
      setArcError(err.message ?? 'Upload failed')
    } finally {
      setUploading(false)
      if (arcFileRef.current) arcFileRef.current.value = ''
    }
  }

  const handleArcRemove = async () => {
    setRemoving(true)
    setArcError('')
    try {
      await fetch(`/api/portal/books/${isbn13}/arc`, { method: 'DELETE' })
      onUpdate()
    } catch { setArcError('Remove failed') } finally { setRemoving(false) }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl px-5 py-4">
      <div className="flex items-center justify-between mb-3">
        <div>
          <p className="text-sm font-semibold text-slate-800 flex items-center gap-1.5">
            <FileDown size={15} className="text-slate-400" />
            Advance Reading Copy (ARC)
          </p>
          <p className="text-xs text-slate-500 mt-0.5">
            Upload a PDF to enable ARC requests for this title. Booksellers and trade contacts can request access from the catalog page.
          </p>
        </div>
      </div>

      {arcError && (
        <div className="mb-3 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">
          {arcError}
        </div>
      )}

      {arcEnabled && arcS3Key ? (
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-2 bg-green-50 border border-green-200 rounded-lg text-xs text-green-800 font-medium">
            <CheckCircle2 size={13} /> ARC enabled — requests are open
          </div>
          <button
            onClick={handleArcRemove}
            disabled={removing}
            className="flex items-center gap-1.5 text-xs text-red-500 hover:text-red-700 border border-red-200 rounded-lg px-3 py-2 disabled:opacity-50"
          >
            <Trash2 size={12} /> {removing ? 'Removing…' : 'Remove ARC'}
          </button>
        </div>
      ) : (
        <>
          <input ref={arcFileRef} type="file" accept="application/pdf" className="hidden" onChange={handleArcUpload} />
          <button
            onClick={() => arcFileRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium border border-slate-300 rounded-lg hover:bg-slate-50 disabled:opacity-50"
          >
            {uploading ? <Loader2 size={14} className="animate-spin" /> : <Upload size={14} />}
            {uploading ? 'Uploading…' : 'Upload ARC PDF'}
          </button>
          <p className="text-xs text-slate-400 mt-1.5">PDF only. Max 50 MB recommended.</p>
        </>
      )}
    </div>
  )
}

// ── Version history ───────────────────────────────────────────────────────────

function VersionHistory({ isbn13, onRestore }: { isbn13: string; onRestore: () => void }) {
  const [open, setOpen]           = useState(false)
  const [versions, setVersions]   = useState<BookVersion[]>([])
  const [loading, setLoading]     = useState(false)
  const [restoring, setRestoring] = useState<string | null>(null)
  const [confirm, setConfirm]     = useState<string | null>(null)
  const [error, setError]         = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/portal/books/${isbn13}/versions`)
      if (!res.ok) throw new Error()
      setVersions(await res.json())
    } catch { setError('Could not load history') }
    finally { setLoading(false) }
  }

  const toggle = () => {
    if (!open && versions.length === 0) load()
    setOpen(o => !o)
  }

  const restore = async (id: string) => {
    setRestoring(id)
    try {
      const res = await fetch(`/api/portal/books/${isbn13}/versions/${id}/restore`, { method: 'POST' })
      if (!res.ok) throw new Error()
      setConfirm(null)
      onRestore()
    } catch { setError('Restore failed') }
    finally { setRestoring(null) }
  }

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <button onClick={toggle} className="w-full flex items-center justify-between px-5 py-4 hover:bg-slate-50 transition-colors">
        <span className="flex items-center gap-2 font-semibold text-slate-800 text-sm">
          <History size={15} className="text-slate-400" /> Version History
        </span>
        {open ? <ChevronUp size={14} className="text-slate-400" /> : <ChevronDown size={14} className="text-slate-400" />}
      </button>
      {open && (
        <div className="border-t border-slate-100">
          {error && <p className="px-5 py-3 text-sm text-red-500">{error}</p>}
          {loading && <div className="flex justify-center py-5"><Loader2 className="animate-spin text-slate-300" size={18} /></div>}
          {!loading && versions.length === 0 && <p className="px-5 py-4 text-sm text-slate-400">No version history yet.</p>}
          <div className="divide-y divide-slate-100 max-h-72 overflow-y-auto">
            {versions.map(v => (
              <div key={v.id} className="px-5 py-3 flex items-center justify-between gap-4">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="text-xs font-medium bg-slate-100 text-slate-600 px-1.5 py-0.5 rounded">v{v.version_number}</span>
                    <span className="text-sm text-slate-700">{changedByLabel(v.changed_by)}</span>
                  </div>
                  <p className="text-xs text-slate-400 mt-0.5">{formatDate(v.created_at)}</p>
                </div>
                {confirm === v.id ? (
                  <div className="flex gap-2 shrink-0">
                    <button onClick={() => restore(v.id)} disabled={!!restoring}
                      className="text-xs px-2 py-1 bg-amber-500 text-white rounded hover:bg-amber-600 disabled:opacity-50">
                      {restoring === v.id ? <Loader2 size={10} className="animate-spin" /> : 'Confirm'}
                    </button>
                    <button onClick={() => setConfirm(null)} className="text-xs text-slate-400 hover:text-slate-600">Cancel</button>
                  </div>
                ) : (
                  <button onClick={() => setConfirm(v.id)}
                    className="flex items-center gap-1 text-xs text-slate-400 hover:text-amber-600 transition-colors shrink-0">
                    <RotateCcw size={11} /> Restore
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function BookDetailPage() {
  const { isbn13 } = useParams<{ isbn13: string }>()

  const [book, setBook]           = useState<BookDetail | null>(null)
  const [loading, setLoading]     = useState(true)
  const [saving, setSaving]       = useState(false)
  const [notice, setNotice]       = useState<string | null>(null)
  const [error, setError]         = useState<string | null>(null)
  const [uploading, setUploading] = useState(false)
  const [deleting, setDeleting]   = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const loadBook = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/portal/books/${isbn13}`)
      if (!res.ok) throw new Error()
      setBook(await res.json())
    } catch { setError('Could not load book') }
    finally { setLoading(false) }
  }

  useEffect(() => { loadBook() }, [isbn13])

  const saveField = async (field: string, value: string) => {
    setSaving(true)
    setNotice(null)
    try {
      const res = await fetch(`/api/portal/books/${isbn13}/editorial`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ [field]: value }),
      })
      if (!res.ok) throw new Error()
      setNotice(`${field.charAt(0).toUpperCase() + field.slice(1)} saved.`)
      await loadBook()
    } catch { setError('Save failed') }
    finally { setSaving(false) }
  }

  const handleCoverUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    if (!['image/jpeg', 'image/png'].includes(file.type)) { setError('JPEG or PNG only'); return }
    if (file.size > 10 * 1024 * 1024) { setError('Max 10 MB'); return }
    setUploading(true)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch(`/api/portal/books/${isbn13}/cover`, { method: 'POST', body: form })
      if (!res.ok) throw new Error()
      setNotice('Cover uploaded.')
      await loadBook()
    } catch { setError('Cover upload failed') }
    finally { setUploading(false); if (fileRef.current) fileRef.current.value = '' }
  }

  const handleCoverDelete = async () => {
    setDeleting(true)
    try {
      await fetch(`/api/portal/books/${isbn13}/cover`, { method: 'DELETE' })
      setNotice('Cover removed.')
      await loadBook()
    } catch { setError('Delete failed') }
    finally { setDeleting(false) }
  }

  if (loading) return <div className="flex justify-center py-16"><Loader2 className="animate-spin text-slate-300" size={24} /></div>
  if (!book) return <div className="text-slate-500 py-12 text-center">Book not found.</div>

  const score = book.metadata_score

  return (
    <div className="max-w-3xl">
      {/* Back + header */}
      <div className="mb-6">
        <a href="/portal/quality" className="inline-flex items-center gap-1.5 text-sm text-slate-400 hover:text-amber-600 transition-colors mb-3">
          <ArrowLeft size={14} /> Back to Catalog Quality
        </a>
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900 leading-tight">{book.title}</h1>
            {book.subtitle && <p className="text-slate-500 text-sm mt-0.5">{book.subtitle}</p>}
            <p className="text-xs text-slate-400 font-mono mt-1">{book.isbn13}</p>
          </div>
          {score !== null && (
            <div className={`shrink-0 flex flex-col items-center px-4 py-2 rounded-xl ${scoreBg(score)}`}>
              <span className="text-2xl font-bold">{score}</span>
              <span className="text-xs">/ 100</span>
            </div>
          )}
        </div>
      </div>

      {/* Feedback banners */}
      {notice && (
        <div className="flex items-center gap-2 bg-green-50 border border-green-200 text-green-700 text-sm rounded-md p-3 mb-4">
          <CheckCircle2 size={14} className="shrink-0" /> {notice}
          <button onClick={() => setNotice(null)} className="ml-auto text-green-500 hover:text-green-700 text-xs">Dismiss</button>
        </div>
      )}
      {error && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 text-red-600 text-sm rounded-md p-3 mb-4">
          <AlertCircle size={14} className="shrink-0" /> {error}
          <button onClick={() => setError(null)} className="ml-auto text-red-400 hover:text-red-600 text-xs">Dismiss</button>
        </div>
      )}

      {/* ONIX-only fields notice */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl px-4 py-3 mb-5 flex items-start gap-2.5">
        <Info size={15} className="text-blue-400 shrink-0 mt-0.5" />
        <p className="text-xs text-blue-700 leading-relaxed">
          <strong>Fields like price, publication date, and rights</strong> come directly from your ONIX feed and can't be edited here.
          To update them, correct your ONIX file and upload a new feed. <strong>Description, TOC, and excerpt</strong> can be edited below — changes are saved to your Metabookly record and will survive future ONIX uploads.
        </p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">

        {/* Left column: cover + ONIX fields */}
        <div className="space-y-4">
          {/* Cover */}
          <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
            <div className="flex items-center justify-between px-4 py-3 border-b border-slate-100">
              <p className="text-sm font-semibold text-slate-800">Cover</p>
              <button onClick={() => fileRef.current?.click()} disabled={uploading}
                className="text-xs text-purple-600 hover:text-purple-800 flex items-center gap-1 disabled:opacity-50">
                <Upload size={11} /> {uploading ? 'Uploading…' : 'Upload'}
              </button>
              <input ref={fileRef} type="file" accept="image/jpeg,image/png" className="hidden" onChange={handleCoverUpload} />
            </div>
            <div className="flex items-center justify-center bg-slate-50 h-48">
              {book.cover_image_url ? (
                // eslint-disable-next-line @next/next/no-img-element
                <img src={book.cover_image_url} alt="Cover" className="max-h-44 max-w-full object-contain" />
              ) : (
                <div className="flex flex-col items-center gap-1 text-slate-300">
                  <ImageOff size={28} />
                  <span className="text-xs">No cover</span>
                </div>
              )}
            </div>
            {book.cover_image_url && (
              <button onClick={handleCoverDelete} disabled={deleting}
                className="w-full flex items-center justify-center gap-1.5 py-2 text-xs text-red-400 hover:text-red-600 hover:bg-red-50 transition-colors border-t border-slate-100 disabled:opacity-50">
                <Trash2 size={11} /> {deleting ? 'Removing…' : 'Remove cover'}
              </button>
            )}
          </div>

          {/* ONIX-sourced fields (read-only) */}
          <div className="bg-white border border-slate-200 rounded-xl px-5 py-2">
            <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide pt-3 pb-1">From ONIX feed</p>
            <ReadOnlyField label="Publication date" value={book.publication_date} tip="Update via <PublishingDate> DateRole 01 in your ONIX feed." />
            <ReadOnlyField label="RRP (GBP)" value={book.rrp_gbp ? `£${book.rrp_gbp}` : null} tip="Update via <Price> with CurrencyCode GBP in your ONIX feed." />
            <ReadOnlyField label="UK rights" value={book.uk_rights === true ? 'Yes' : book.uk_rights === false ? 'No' : null} tip="Update via <SalesRights> in your ONIX feed." />
            <ReadOnlyField label="Format" value={book.product_form} />
            <ReadOnlyField label="Pages" value={book.page_count?.toString()} />
            <ReadOnlyField label="Dimensions" value={book.height_mm && book.width_mm ? `${book.height_mm} × ${book.width_mm} mm` : null} />
          </div>
        </div>

        {/* Right column: editable fields */}
        <div className="md:col-span-2 space-y-4">
          <div className="bg-white border border-slate-200 rounded-xl px-5 py-2">
            <div className="flex items-center justify-between pt-3 pb-1">
              <p className="text-xs font-semibold text-slate-500 uppercase tracking-wide">Editable fields</p>
              <button onClick={loadBook} className="text-xs text-slate-400 hover:text-amber-600 flex items-center gap-1">
                <RefreshCw size={11} /> Refresh
              </button>
            </div>

            <EditableField
              label="Description"
              value={book.description}
              source={book.field_sources.description}
              onixValue={book.onix_description}
              placeholder="Enter a description of at least 150 characters"
              multiline rows={6}
              saving={saving}
              onSave={v => saveField('description', v)}
            />
            <EditableField
              label="Table of Contents"
              value={book.toc}
              source={book.field_sources.toc}
              onixValue={book.onix_toc}
              placeholder="Enter a table of contents (one chapter per line)"
              multiline rows={5}
              saving={saving}
              onSave={v => saveField('toc', v)}
            />
            <EditableField
              label="Excerpt"
              value={book.excerpt}
              source={book.field_sources.excerpt}
              onixValue={book.onix_excerpt}
              placeholder="Enter a short excerpt or sample passage"
              multiline rows={4}
              saving={saving}
              onSave={v => saveField('excerpt', v)}
            />
          </div>

          {/* ARC (Advance Reading Copy) */}
          <ArcPanel isbn13={isbn13} arcEnabled={book.arc_enabled} arcS3Key={book.arc_s3_key} onUpdate={loadBook} />

          {/* Version history */}
          <VersionHistory isbn13={isbn13} onRestore={() => { loadBook(); setNotice('Version restored.') }} />
        </div>
      </div>
    </div>
  )
}
