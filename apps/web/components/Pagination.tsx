'use client'

import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { useTransition } from 'react'
import { cn } from '@/lib/utils'

interface PaginationProps {
  page: number
  pages: number
  total: number
}

export function Pagination({ page, pages, total }: PaginationProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [, startTransition] = useTransition()

  if (pages <= 1) return null

  const go = (p: number) => {
    const params = new URLSearchParams(searchParams.toString())
    params.set('page', String(p))
    startTransition(() => router.push(`${pathname}?${params}`))
  }

  return (
    <div className="flex items-center justify-between py-4">
      <p className="text-sm text-slate-500">
        Page {page} of {pages} ({total.toLocaleString()} titles)
      </p>
      <div className="flex gap-2">
        <button
          onClick={() => go(page - 1)}
          disabled={page <= 1}
          className={cn(
            'flex items-center gap-1 px-3 py-1.5 rounded text-sm border transition-colors',
            page <= 1
              ? 'border-slate-200 text-slate-300 cursor-not-allowed'
              : 'border-slate-300 text-slate-700 hover:bg-slate-50',
          )}
        >
          <ChevronLeft size={16} /> Prev
        </button>
        <button
          onClick={() => go(page + 1)}
          disabled={page >= pages}
          className={cn(
            'flex items-center gap-1 px-3 py-1.5 rounded text-sm border transition-colors',
            page >= pages
              ? 'border-slate-200 text-slate-300 cursor-not-allowed'
              : 'border-slate-300 text-slate-700 hover:bg-slate-50',
          )}
        >
          Next <ChevronRight size={16} />
        </button>
      </div>
    </div>
  )
}
