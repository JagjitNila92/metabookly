'use client'

import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { useTransition } from 'react'

const SORT_OPTIONS = [
  { value: '', label: 'Relevance / Newest' },
  { value: 'popular', label: 'Most popular' },
  { value: 'newest', label: 'Newest first' },
  { value: 'oldest', label: 'Oldest first' },
  { value: 'title_az', label: 'Title A–Z' },
  { value: 'price_asc', label: 'Price: low–high' },
  { value: 'price_desc', label: 'Price: high–low' },
]

interface ResultsToolbarProps {
  total: number
  query?: string
}

export function ResultsToolbar({ total, query }: ResultsToolbarProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [, startTransition] = useTransition()

  const currentSort = searchParams.get('sort') ?? ''

  const setSort = (value: string) => {
    const params = new URLSearchParams(searchParams.toString())
    if (value) params.set('sort', value)
    else params.delete('sort')
    params.delete('page')
    startTransition(() => router.push(`${pathname}?${params}`))
  }

  return (
    <div className="flex items-center justify-between mb-4">
      <p className="text-sm text-slate-500">
        <span className="font-medium text-slate-700">{total.toLocaleString()}</span>
        {' '}title{total !== 1 ? 's' : ''}
        {query ? (
          <> for <span className="font-medium text-slate-700">&ldquo;{query}&rdquo;</span></>
        ) : null}
      </p>
      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400">Sort:</span>
        <select
          value={currentSort}
          onChange={(e) => setSort(e.target.value)}
          className="text-sm px-2 py-1 border border-slate-200 rounded bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-amber-400"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>
              {o.label}
            </option>
          ))}
        </select>
      </div>
    </div>
  )
}
