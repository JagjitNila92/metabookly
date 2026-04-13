'use client'

import { useEffect, useRef, useState } from 'react'
import { Upload, Trash2, Loader2, FileText, Image, Archive, Eye, EyeOff, Plus, Download } from 'lucide-react'

type Asset = {
  id: string
  asset_type: string
  label: string
  original_filename: string | null
  file_size_bytes: number | null
  content_type: string | null
  public: boolean
  created_at: string
  download_url: string | null
}

const TYPE_OPTIONS = [
  { value: 'press_kit', label: 'Press Kit' },
  { value: 'author_photo', label: 'Author Photo' },
  { value: 'sell_sheet', label: 'Sell Sheet' },
  { value: 'media_pack', label: 'Media Pack' },
  { value: 'other', label: 'Other' },
]

const TYPE_ICON: Record<string, React.ReactNode> = {
  press_kit: <FileText size={14} className="text-blue-500" />,
  author_photo: <Image size={14} className="text-purple-500" />,
  sell_sheet: <FileText size={14} className="text-green-500" />,
  media_pack: <Archive size={14} className="text-amber-500" />,
  other: <FileText size={14} className="text-slate-400" />,
}

function formatBytes(bytes: number | null): string {
  if (!bytes) return ''
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function UploadModal({
  isbn13,
  onClose,
  onUploaded,
}: {
  isbn13: string
  onClose: () => void
  onUploaded: () => void
}) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [assetType, setAssetType] = useState('press_kit')
  const [label, setLabel] = useState('')
  const [isPublic, setIsPublic] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0] ?? null
    setFile(f)
    if (f && !label) setLabel(f.name.replace(/\.[^.]+$/, ''))
  }

  const handleUpload = async () => {
    if (!file) return
    setUploading(true)
    setError('')
    try {
      // 1. Get presigned URL
      const urlRes = await fetch(
        `/api/portal/books/${isbn13}/assets/upload-url?asset_type=${assetType}&content_type=${encodeURIComponent(file.type || 'application/octet-stream')}`
      )
      if (!urlRes.ok) throw new Error('Failed to get upload URL')
      const { upload_url, s3_key } = await urlRes.json()

      // 2. Upload to S3
      const putRes = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': file.type || 'application/octet-stream' },
      })
      if (!putRes.ok) throw new Error('S3 upload failed')

      // 3. Confirm
      const confirmRes = await fetch(`/api/portal/books/${isbn13}/assets`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          s3_key,
          asset_type: assetType,
          label: label || file.name,
          original_filename: file.name,
          file_size_bytes: file.size,
          content_type: file.type,
          public: isPublic,
        }),
      })
      if (!confirmRes.ok) throw new Error('Failed to register asset')
      onUploaded()
      onClose()
    } catch (err: any) {
      setError(err.message ?? 'Upload failed')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white rounded-xl shadow-xl p-6 w-full max-w-md">
        <h3 className="text-base font-semibold text-slate-900 mb-4">Upload Marketing Asset</h3>

        {error && (
          <div className="mb-3 text-xs text-red-600 bg-red-50 border border-red-200 rounded-lg px-3 py-2">{error}</div>
        )}

        <div className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Asset type</label>
            <select
              value={assetType}
              onChange={e => setAssetType(e.target.value)}
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400"
            >
              {TYPE_OPTIONS.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">Label</label>
            <input
              value={label}
              onChange={e => setLabel(e.target.value)}
              placeholder="e.g. Press Kit Spring 2026"
              className="w-full border border-slate-300 rounded-md px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400"
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-slate-700 mb-1">File</label>
            <input ref={fileRef} type="file" className="hidden" onChange={handleFileChange} />
            <button
              onClick={() => fileRef.current?.click()}
              className="flex items-center gap-2 w-full px-3 py-2 text-sm border border-dashed border-slate-300 rounded-lg hover:border-amber-400 hover:bg-amber-50 text-slate-600 transition-colors"
            >
              <Upload size={14} />
              {file ? file.name : 'Choose file…'}
            </button>
            {file && (
              <p className="text-xs text-slate-400 mt-1">{formatBytes(file.size)}</p>
            )}
          </div>

          <label className="flex items-center gap-2 text-sm text-slate-700 cursor-pointer">
            <input
              type="checkbox"
              checked={isPublic}
              onChange={e => setIsPublic(e.target.checked)}
              className="rounded border-slate-300 text-amber-500 focus:ring-amber-400"
            />
            Visible to retailers on the catalog
          </label>
        </div>

        <div className="flex gap-3 mt-6 justify-end">
          <button onClick={onClose} className="px-4 py-2 text-sm text-slate-600 hover:text-slate-900">
            Cancel
          </button>
          <button
            onClick={handleUpload}
            disabled={!file || uploading}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50"
          >
            {uploading && <Loader2 size={14} className="animate-spin" />}
            {uploading ? 'Uploading…' : 'Upload'}
          </button>
        </div>
      </div>
    </div>
  )
}

function AssetRow({
  asset,
  isbn13,
  onUpdate,
  onDelete,
}: {
  asset: Asset
  isbn13: string
  onUpdate: (id: string, changes: Partial<Asset>) => void
  onDelete: (id: string) => void
}) {
  const [deleting, setDeleting] = useState(false)
  const [toggling, setToggling] = useState(false)

  const handleDelete = async () => {
    if (!confirm(`Delete "${asset.label}"?`)) return
    setDeleting(true)
    await fetch(`/api/portal/books/${isbn13}/assets/${asset.id}`, { method: 'DELETE' })
    onDelete(asset.id)
  }

  const handleTogglePublic = async () => {
    setToggling(true)
    await fetch(`/api/portal/books/${isbn13}/assets/${asset.id}`, {
      method: 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ public: !asset.public }),
    })
    onUpdate(asset.id, { public: !asset.public })
    setToggling(false)
  }

  return (
    <div className="flex items-center gap-4 px-4 py-3 bg-white border border-slate-200 rounded-lg">
      <div className="shrink-0">{TYPE_ICON[asset.asset_type] ?? TYPE_ICON.other}</div>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-slate-900 truncate">{asset.label}</p>
        <p className="text-xs text-slate-400">
          {TYPE_OPTIONS.find(t => t.value === asset.asset_type)?.label ?? asset.asset_type}
          {asset.file_size_bytes ? ` · ${formatBytes(asset.file_size_bytes)}` : ''}
          {asset.original_filename ? ` · ${asset.original_filename}` : ''}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <button
          onClick={handleTogglePublic}
          disabled={toggling}
          title={asset.public ? 'Visible to retailers — click to hide' : 'Hidden — click to make public'}
          className={`flex items-center gap-1 text-xs px-2 py-1 rounded border transition-colors ${
            asset.public
              ? 'border-green-200 text-green-700 bg-green-50 hover:bg-green-100'
              : 'border-slate-200 text-slate-500 bg-white hover:bg-slate-50'
          }`}
        >
          {asset.public ? <Eye size={11} /> : <EyeOff size={11} />}
          {asset.public ? 'Public' : 'Private'}
        </button>
        {asset.download_url && (
          <a
            href={asset.download_url}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-1 text-xs px-2 py-1 rounded border border-slate-200 text-slate-600 hover:bg-slate-50"
          >
            <Download size={11} /> Download
          </a>
        )}
        <button
          onClick={handleDelete}
          disabled={deleting}
          className="text-slate-400 hover:text-red-500 transition-colors"
        >
          {deleting ? <Loader2 size={14} className="animate-spin" /> : <Trash2 size={14} />}
        </button>
      </div>
    </div>
  )
}

// The main page shows assets grouped by title.
// We fetch the publisher's books list from the portal, then load assets per book.

type BookSummary = { isbn13: string; title: string }
type BookAssets = { book: BookSummary; assets: Asset[] }

export default function AssetsPage() {
  const [bookAssets, setBookAssets] = useState<BookAssets[]>([])
  const [loading, setLoading] = useState(true)
  const [uploadTarget, setUploadTarget] = useState<BookSummary | null>(null)
  const [searchIsbn, setSearchIsbn] = useState('')

  async function loadAllAssets() {
    setLoading(true)
    try {
      // Fetch publisher's feed summary to get their books
      const feedRes = await fetch('/api/portal/feeds')
      if (!feedRes.ok) return

      // We need the list of ISBNs from the catalog — use the portal quality endpoint
      // which returns their titles. For now fetch from quality summary's worst_titles.
      const qualityRes = await fetch('/api/portal/quality')
      if (!qualityRes.ok) return
      const quality = await qualityRes.json()

      // Build book list from quality summary
      const books: BookSummary[] = (quality.worst_titles ?? []).map((t: any) => ({
        isbn13: t.isbn13,
        title: t.title,
      }))

      // Fetch assets for each book in parallel (first 20)
      const slice = books.slice(0, 20)
      const assetResults = await Promise.all(
        slice.map(async (book) => {
          const res = await fetch(`/api/portal/books/${book.isbn13}/assets`)
          const assets = res.ok ? await res.json() : []
          return { book, assets }
        })
      )
      setBookAssets(assetResults)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadAllAssets() }, [])

  const handleUpdate = (isbn13: string, assetId: string, changes: Partial<Asset>) => {
    setBookAssets(prev => prev.map(ba =>
      ba.book.isbn13 === isbn13
        ? { ...ba, assets: ba.assets.map(a => a.id === assetId ? { ...a, ...changes } : a) }
        : ba
    ))
  }

  const handleDelete = (isbn13: string, assetId: string) => {
    setBookAssets(prev => prev.map(ba =>
      ba.book.isbn13 === isbn13
        ? { ...ba, assets: ba.assets.filter(a => a.id !== assetId) }
        : ba
    ))
  }

  const totalAssets = bookAssets.reduce((n, ba) => n + ba.assets.length, 0)
  const booksWithAssets = bookAssets.filter(ba => ba.assets.length > 0)

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-xl font-semibold text-slate-900">Marketing Assets</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Press kits, author photos, sell sheets, and other materials — per title.
          </p>
        </div>
        {totalAssets > 0 && (
          <span className="text-sm text-slate-500">{totalAssets} asset{totalAssets !== 1 ? 's' : ''} across {booksWithAssets.length} title{booksWithAssets.length !== 1 ? 's' : ''}</span>
        )}
      </div>

      {/* Add asset for a specific ISBN */}
      <div className="mb-6 bg-white border border-slate-200 rounded-xl p-4">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">Upload asset for a title</p>
        <div className="flex gap-2">
          <input
            value={searchIsbn}
            onChange={e => setSearchIsbn(e.target.value.trim())}
            placeholder="Enter ISBN-13"
            className="flex-1 border border-slate-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-1 focus:ring-amber-400"
          />
          <button
            onClick={() => {
              if (searchIsbn.length === 13) {
                setUploadTarget({ isbn13: searchIsbn, title: searchIsbn })
              }
            }}
            disabled={searchIsbn.length !== 13}
            className="flex items-center gap-2 px-4 py-2 text-sm font-medium bg-amber-500 text-white rounded-lg hover:bg-amber-600 disabled:opacity-50"
          >
            <Plus size={14} /> Add Asset
          </button>
        </div>
      </div>

      {loading ? (
        <div className="flex items-center gap-2 text-slate-400 py-8">
          <Loader2 size={16} className="animate-spin" /> Loading…
        </div>
      ) : booksWithAssets.length === 0 ? (
        <div className="text-center py-16 text-slate-400">
          <p className="text-base">No assets yet</p>
          <p className="text-sm mt-1">Enter an ISBN above to upload your first press kit or author photo.</p>
        </div>
      ) : (
        <div className="space-y-6">
          {booksWithAssets.map(({ book, assets }) => (
            <div key={book.isbn13}>
              <div className="flex items-center justify-between mb-2">
                <div>
                  <p className="text-sm font-semibold text-slate-800">{book.title}</p>
                  <p className="text-xs text-slate-400">{book.isbn13}</p>
                </div>
                <button
                  onClick={() => setUploadTarget(book)}
                  className="flex items-center gap-1.5 text-xs text-amber-600 hover:text-amber-700 border border-amber-200 rounded-lg px-2.5 py-1.5"
                >
                  <Upload size={11} /> Add asset
                </button>
              </div>
              <div className="space-y-2">
                {assets.map(asset => (
                  <AssetRow
                    key={asset.id}
                    asset={asset}
                    isbn13={book.isbn13}
                    onUpdate={(id, changes) => handleUpdate(book.isbn13, id, changes)}
                    onDelete={(id) => handleDelete(book.isbn13, id)}
                  />
                ))}
              </div>
            </div>
          ))}
        </div>
      )}

      {uploadTarget && (
        <UploadModal
          isbn13={uploadTarget.isbn13}
          onClose={() => setUploadTarget(null)}
          onUploaded={() => { loadAllAssets(); setUploadTarget(null) }}
        />
      )}
    </div>
  )
}
