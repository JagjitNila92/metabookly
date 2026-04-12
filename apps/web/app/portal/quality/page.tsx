'use client'

import { useEffect, useState } from 'react'
import {
  Loader2, RefreshCw, ImageOff, FileText, PoundSterling,
  Calendar, ChevronDown, ChevronUp, ArrowRight, CheckCircle2,
  TrendingUp,
} from 'lucide-react'

// ── Types ─────────────────────────────────────────────────────────────────────

type Issue = {
  issue: string
  count: number
  points: number
  tip: string
  how_to_fix: string
}

type WorstTitle = {
  isbn13: string
  title: string
  score: number | null
  missing: string[]
}

type QualitySummary = {
  total_titles: number
  avg_score: number
  titles_below_60: number
  top_issues: Issue[]
  worst_titles: WorstTitle[]
}

// ── Score health banner ───────────────────────────────────────────────────────

function HealthBanner({ score, total, below60 }: { score: number; total: number; below60: number }) {
  const pct = Math.round((below60 / total) * 100)

  const { bg, bar, label, sublabel } =
    score >= 80
      ? { bg: 'bg-green-50 border-green-200', bar: 'bg-green-500', label: 'Your catalog is in great shape', sublabel: 'Booksellers can find and order your titles with confidence.' }
      : score >= 60
      ? { bg: 'bg-amber-50 border-amber-200', bar: 'bg-amber-500', label: 'Your catalog needs some attention', sublabel: `${pct}% of your titles are missing key information that booksellers rely on.` }
      : { bg: 'bg-red-50 border-red-200', bar: 'bg-red-500', label: 'Your catalog needs urgent work', sublabel: `${pct}% of titles are poorly described — booksellers are unlikely to order them.` }

  return (
    <div className={`rounded-xl border p-6 ${bg} mb-6`}>
      <div className="flex items-start justify-between gap-6">
        <div className="flex-1">
          <p className="text-lg font-bold text-slate-900 mb-1">{label}</p>
          <p className="text-sm text-slate-600 mb-4">{sublabel}</p>
          {/* Progress bar */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-3 bg-white/60 rounded-full overflow-hidden border border-slate-200">
              <div
                className={`h-full rounded-full transition-all duration-700 ${bar}`}
                style={{ width: `${score}%` }}
              />
            </div>
            <span className="text-2xl font-bold text-slate-900 shrink-0">{score}<span className="text-sm font-normal text-slate-500">/100</span></span>
          </div>
          <p className="text-xs text-slate-500 mt-1.5">Average metadata score across {total.toLocaleString()} title{total !== 1 ? 's' : ''}</p>
        </div>
        {/* Quick stats */}
        <div className="shrink-0 text-right hidden sm:block">
          <p className="text-3xl font-bold text-slate-900">{below60}</p>
          <p className="text-xs text-slate-500 mt-0.5">title{below60 !== 1 ? 's' : ''} need fixing</p>
        </div>
      </div>
    </div>
  )
}

// ── Score pill ────────────────────────────────────────────────────────────────

function ScorePill({ score }: { score: number | null }) {
  if (score === null) return <span className="text-slate-300 text-xs">—</span>
  const { bg, text } =
    score >= 80 ? { bg: 'bg-green-100', text: 'text-green-700' }
    : score >= 60 ? { bg: 'bg-amber-100', text: 'text-amber-700' }
    : { bg: 'bg-red-100', text: 'text-red-600' }
  return (
    <span className={`inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold ${bg} ${text}`}>
      {score}
    </span>
  )
}

// ── Missing field tags ────────────────────────────────────────────────────────

function MissingTag({ label }: { label: string }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 text-xs border border-slate-200">
      {label}
    </span>
  )
}

// ── Issue card ────────────────────────────────────────────────────────────────

const ISSUE_ICONS: Record<string, React.ReactNode> = {
  description: <FileText size={18} className="text-purple-500" />,
  cover:       <ImageOff size={18} className="text-blue-500" />,
  price:       <PoundSterling size={18} className="text-green-600" />,
  date:        <Calendar size={18} className="text-amber-500" />,
}

function getIssueIcon(issue: string) {
  if (issue.toLowerCase().includes('description')) return ISSUE_ICONS.description
  if (issue.toLowerCase().includes('cover')) return ISSUE_ICONS.cover
  if (issue.toLowerCase().includes('price') || issue.toLowerCase().includes('gbp')) return ISSUE_ICONS.price
  if (issue.toLowerCase().includes('date')) return ISSUE_ICONS.date
  return ISSUE_ICONS.date
}

function IssueCard({ issue, total }: { issue: Issue; total: number }) {
  const [expanded, setExpanded] = useState(false)
  const pct = Math.round((issue.count / total) * 100)

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <div className="p-5">
        <div className="flex items-start gap-4">
          <div className="p-2 bg-slate-50 rounded-lg border border-slate-100 shrink-0">
            {getIssueIcon(issue.issue)}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center justify-between gap-2 mb-1">
              <p className="font-semibold text-slate-900 text-sm">{issue.issue}</p>
              <span className="shrink-0 text-xs font-bold text-red-600 bg-red-50 px-2 py-0.5 rounded-full border border-red-100">
                {issue.count} title{issue.count !== 1 ? 's' : ''}
              </span>
            </div>
            <p className="text-sm text-slate-600 leading-relaxed">{issue.tip}</p>
            {/* Mini progress */}
            <div className="mt-3 flex items-center gap-2">
              <div className="flex-1 h-1.5 bg-slate-100 rounded-full overflow-hidden">
                <div className="h-full bg-red-400 rounded-full" style={{ width: `${pct}%` }} />
              </div>
              <span className="text-xs text-slate-400 shrink-0">{pct}% of catalog</span>
              <span className="text-xs font-medium text-amber-600 shrink-0">+{issue.points} pts each</span>
            </div>
          </div>
        </div>
      </div>
      {/* How to fix toggle */}
      <button
        onClick={() => setExpanded(e => !e)}
        className="w-full flex items-center justify-between px-5 py-2.5 bg-slate-50 border-t border-slate-100 text-xs text-slate-500 hover:text-amber-600 hover:bg-amber-50 transition-colors"
      >
        <span className="font-medium">How to fix this in your ONIX feed</span>
        {expanded ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
      </button>
      {expanded && (
        <div className="px-5 py-3 bg-slate-50 border-t border-slate-100">
          <p className="text-xs text-slate-600 leading-relaxed font-mono bg-white border border-slate-200 rounded p-2.5">
            {issue.how_to_fix}
          </p>
        </div>
      )}
    </div>
  )
}

// ── What affects score explainer ──────────────────────────────────────────────

function ScoreExplainer() {
  const [open, setOpen] = useState(false)

  const items = [
    {
      label: 'Full description (up to +20 pts)',
      detail: 'The single most important field. A description of 150+ characters helps booksellers understand what the book is about and recommend it to customers. Short or missing descriptions are the #1 reason titles get overlooked.',
      icon: <FileText size={15} className="text-purple-500 shrink-0 mt-0.5" />,
    },
    {
      label: 'Cover image (up to +10 pts)',
      detail: 'Titles without covers are significantly less likely to be ordered. Your cover URL should point to a high-resolution JPEG or PNG (at least 600px on the longest side).',
      icon: <ImageOff size={15} className="text-blue-500 shrink-0 mt-0.5" />,
    },
    {
      label: 'GBP price (up to +10 pts)',
      detail: 'Booksellers need to know your recommended retail price in GBP to calculate margin and decide whether to stock the title.',
      icon: <PoundSterling size={15} className="text-green-600 shrink-0 mt-0.5" />,
    },
    {
      label: 'Publication date (up to +10 pts)',
      detail: 'Required for new release promotions, seasonal buying, and event planning. Use YYYYMMDD format in your ONIX feed.',
      icon: <Calendar size={15} className="text-amber-500 shrink-0 mt-0.5" />,
    },
    {
      label: 'UK rights, publisher name, subjects, contributor bio, TOC, dimensions',
      detail: 'Each of these adds points and helps booksellers trust and discover your titles. UK rights tells shops they can legally stock the book. Subject headings power search and category pages. Contributor bios drive author event bookings.',
      icon: <TrendingUp size={15} className="text-slate-400 shrink-0 mt-0.5" />,
    },
  ]

  return (
    <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-6 py-4 text-left hover:bg-slate-50 transition-colors"
      >
        <div>
          <p className="font-semibold text-slate-900 text-sm">What affects your score?</p>
          <p className="text-xs text-slate-400 mt-0.5">Learn what booksellers actually look for</p>
        </div>
        {open ? <ChevronUp size={15} className="text-slate-400 shrink-0" /> : <ChevronDown size={15} className="text-slate-400 shrink-0" />}
      </button>
      {open && (
        <div className="border-t border-slate-100 divide-y divide-slate-100">
          {items.map((item, i) => (
            <div key={i} className="px-6 py-4 flex gap-3">
              {item.icon}
              <div>
                <p className="text-sm font-medium text-slate-800 mb-0.5">{item.label}</p>
                <p className="text-xs text-slate-500 leading-relaxed">{item.detail}</p>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function QualityPage() {
  const [data, setData]       = useState<QualitySummary | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]     = useState<string | null>(null)

  const load = async () => {
    setLoading(true)
    setError(null)
    try {
      const res = await fetch('/api/portal/quality')
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      setData(await res.json())
    } catch {
      setError('Could not load quality data')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  return (
    <div>
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Catalog Quality</h1>
          <p className="text-sm text-slate-500 mt-0.5">
            Better metadata means more booksellers discover and stock your titles.
          </p>
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

      {data && data.total_titles === 0 && (
        <div className="bg-white border border-slate-200 rounded-xl p-12 text-center">
          <TrendingUp size={36} className="text-slate-300 mx-auto mb-3" />
          <p className="text-slate-700 font-medium mb-1">No titles yet</p>
          <p className="text-slate-400 text-sm mb-4">Upload your first ONIX feed to see quality scores and improvement tips.</p>
          <a href="/portal/upload" className="inline-flex items-center gap-1.5 text-sm font-medium text-amber-600 hover:text-amber-700">
            Upload a feed <ArrowRight size={14} />
          </a>
        </div>
      )}

      {data && data.total_titles > 0 && (
        <div className="space-y-6">

          {/* Health banner */}
          <HealthBanner
            score={data.avg_score}
            total={data.total_titles}
            below60={data.titles_below_60}
          />

          {/* Issues */}
          {data.top_issues.length > 0 && (
            <div>
              <h2 className="font-semibold text-slate-900 mb-1">Fix these to improve your score</h2>
              <p className="text-sm text-slate-500 mb-3">Each fix adds points to every affected title — and makes them more visible to booksellers.</p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {data.top_issues.map((issue, i) => (
                  <IssueCard key={i} issue={issue} total={data.total_titles} />
                ))}
              </div>
            </div>
          )}

          {data.top_issues.length === 0 && (
            <div className="flex items-center gap-3 bg-green-50 border border-green-200 rounded-xl px-5 py-4">
              <CheckCircle2 size={20} className="text-green-500 shrink-0" />
              <div>
                <p className="font-medium text-green-800 text-sm">No major issues found</p>
                <p className="text-xs text-green-600 mt-0.5">All titles have the key fields booksellers need. Keep it up.</p>
              </div>
            </div>
          )}

          {/* Titles needing attention */}
          {data.worst_titles.length > 0 && (
            <div>
              <h2 className="font-semibold text-slate-900 mb-1">Titles to prioritise</h2>
              <p className="text-sm text-slate-500 mb-3">These titles have the lowest scores. The tags show exactly what each one is missing.</p>
              <div className="bg-white border border-slate-200 rounded-xl overflow-hidden">
                <div className="divide-y divide-slate-100">
                  {data.worst_titles.map((t, i) => (
                    <div
                      key={t.isbn13}
                      className="px-5 py-4 flex items-start gap-4 hover:bg-amber-50 cursor-pointer transition-colors group"
                      onClick={() => window.location.href = `/portal/books/${t.isbn13}`}
                    >
                      {/* Rank */}
                      <span className="text-xs text-slate-400 font-medium w-5 shrink-0 mt-1">{i + 1}</span>

                      {/* Title + missing tags */}
                      <div className="flex-1 min-w-0">
                        <p className="font-medium text-slate-900 text-sm truncate group-hover:text-amber-700 transition-colors">
                          {t.title}
                        </p>
                        <p className="text-xs text-slate-400 font-mono mt-0.5 mb-2">{t.isbn13}</p>
                        {t.missing.length > 0 ? (
                          <div className="flex flex-wrap gap-1.5">
                            {t.missing.map(m => <MissingTag key={m} label={m} />)}
                          </div>
                        ) : (
                          <span className="text-xs text-green-600 flex items-center gap-1">
                            <CheckCircle2 size={11} /> All key fields present
                          </span>
                        )}
                      </div>

                      {/* Score + arrow */}
                      <div className="flex items-center gap-2 shrink-0">
                        <ScorePill score={t.score} />
                        <ArrowRight size={14} className="text-slate-300 group-hover:text-amber-500 transition-colors" />
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* Score explainer accordion */}
          <ScoreExplainer />

        </div>
      )}
    </div>
  )
}
