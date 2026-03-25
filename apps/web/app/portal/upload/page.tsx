'use client'

import { useState, useRef } from 'react'
import { Upload, CheckCircle2, AlertCircle, Loader2, FileText } from 'lucide-react'
import Link from 'next/link'

type Stage = 'idle' | 'uploading' | 'triggering' | 'done' | 'error'

export default function UploadPage() {
  const [file, setFile] = useState<File | null>(null)
  const [sequenceNumber, setSequenceNumber] = useState('')
  const [stage, setStage] = useState<Stage>('idle')
  const [feedId, setFeedId] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [progress, setProgress] = useState(0)
  const inputRef = useRef<HTMLInputElement>(null)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!file) return

    setError(null)
    setStage('uploading')
    setProgress(0)

    try {
      // Step 1: Get pre-signed upload URL
      const qs = new URLSearchParams({ filename: file.name })
      if (sequenceNumber) qs.set('sequence_number', sequenceNumber)

      const urlRes = await fetch(`/api/portal/upload-url?${qs}`, { method: 'POST' })
      if (!urlRes.ok) {
        const err = await urlRes.json()
        throw new Error(err.detail ?? err.error ?? 'Failed to get upload URL')
      }
      const { feed_id, upload_url } = await urlRes.json()

      // Step 2: PUT file directly to S3 (bypass our API for large files)
      setProgress(20)
      const putRes = await fetch(upload_url, {
        method: 'PUT',
        body: file,
        headers: { 'Content-Type': 'application/xml' },
      })
      if (!putRes.ok) {
        throw new Error('S3 upload failed — check file format and try again')
      }
      setProgress(70)

      // Step 3: Trigger processing
      setStage('triggering')
      const triggerRes = await fetch(`/api/portal/feeds/${feed_id}/trigger`, {
        method: 'POST',
      })
      if (!triggerRes.ok) {
        const err = await triggerRes.json()
        throw new Error(err.detail ?? 'Failed to trigger processing')
      }
      setProgress(100)
      setFeedId(feed_id)
      setStage('done')
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Upload failed')
      setStage('error')
    }
  }

  if (stage === 'done' && feedId) {
    return (
      <div>
        <h1 className="text-2xl font-bold text-slate-900 mb-6">Upload ONIX Feed</h1>
        <div className="bg-white border border-green-200 rounded-xl p-8 flex flex-col items-center text-center">
          <CheckCircle2 size={40} className="text-green-500 mb-3" />
          <h2 className="text-lg font-semibold text-slate-900 mb-1">Feed queued for processing</h2>
          <p className="text-slate-500 text-sm mb-6">
            Your ONIX file has been received. Processing typically takes 1–3 minutes.
          </p>
          <div className="flex gap-3">
            <Link
              href={`/portal/feeds`}
              className="px-4 py-2 bg-amber-500 text-white rounded-md text-sm font-medium hover:bg-amber-600 transition-colors"
            >
              View feed status
            </Link>
            <button
              onClick={() => {
                setFile(null)
                setSequenceNumber('')
                setFeedId(null)
                setStage('idle')
              }}
              className="px-4 py-2 border border-slate-300 text-slate-700 rounded-md text-sm font-medium hover:bg-slate-50 transition-colors"
            >
              Upload another
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-2">Upload ONIX Feed</h1>
      <p className="text-slate-500 mb-8">
        Submit an ONIX 2.1 or 3.0 XML file. Files up to 200 MB are supported.
        The file is uploaded directly to our secure storage — it never passes through a web server.
      </p>

      <form onSubmit={handleSubmit} className="bg-white border border-slate-200 rounded-xl p-6">
        {/* Drop zone */}
        <div
          onClick={() => inputRef.current?.click()}
          className="border-2 border-dashed border-slate-300 rounded-lg p-10 flex flex-col items-center text-center cursor-pointer hover:border-amber-400 hover:bg-amber-50/30 transition-colors mb-6"
        >
          {file ? (
            <>
              <FileText size={32} className="text-amber-500 mb-2" />
              <p className="font-medium text-slate-900">{file.name}</p>
              <p className="text-sm text-slate-400">{(file.size / 1024 / 1024).toFixed(1)} MB</p>
            </>
          ) : (
            <>
              <Upload size={32} className="text-slate-400 mb-2" />
              <p className="font-medium text-slate-700">Click to select ONIX XML file</p>
              <p className="text-sm text-slate-400">or drag and drop</p>
            </>
          )}
          <input
            ref={inputRef}
            type="file"
            accept=".xml,application/xml,text/xml"
            className="hidden"
            onChange={(e) => setFile(e.target.files?.[0] ?? null)}
          />
        </div>

        {/* Optional sequence number */}
        <div className="mb-6">
          <label className="block text-sm font-medium text-slate-700 mb-1">
            Sequence number <span className="text-slate-400 font-normal">(optional)</span>
          </label>
          <input
            type="number"
            value={sequenceNumber}
            onChange={(e) => setSequenceNumber(e.target.value)}
            placeholder="e.g. 42"
            className="w-40 px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent"
          />
          <p className="text-xs text-slate-400 mt-1">
            If you send numbered delta feeds, include the sequence so we can detect gaps.
          </p>
        </div>

        {/* Progress bar */}
        {(stage === 'uploading' || stage === 'triggering') && (
          <div className="mb-4">
            <div className="flex items-center justify-between text-xs text-slate-500 mb-1">
              <span>{stage === 'uploading' ? 'Uploading to secure storage…' : 'Queuing for processing…'}</span>
              <span>{progress}%</span>
            </div>
            <div className="h-1.5 bg-slate-200 rounded-full overflow-hidden">
              <div
                className="h-full bg-amber-500 rounded-full transition-all duration-500"
                style={{ width: `${progress}%` }}
              />
            </div>
          </div>
        )}

        {/* Error */}
        {stage === 'error' && error && (
          <div className="flex items-start gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-3 mb-4">
            <AlertCircle size={16} className="shrink-0 mt-0.5" />
            <span>{error}</span>
          </div>
        )}

        <button
          type="submit"
          disabled={!file || stage === 'uploading' || stage === 'triggering'}
          className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white font-medium rounded-md transition-colors"
        >
          {(stage === 'uploading' || stage === 'triggering') && (
            <Loader2 size={15} className="animate-spin" />
          )}
          {stage === 'idle' || stage === 'error' ? 'Upload feed' : 'Uploading…'}
        </button>
      </form>
    </div>
  )
}
