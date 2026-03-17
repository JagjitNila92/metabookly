'use client'

import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { useTransition } from 'react'
import { cn } from '@/lib/utils'

const FORMATS = [
  { value: '', label: 'All formats' },
  { value: 'BB', label: 'Hardback' },
  { value: 'BC', label: 'Paperback' },
]

interface FilterPanelProps {
  currentForm?: string
  currentInPrintOnly?: boolean
}

export function FilterPanel({ currentForm = '', currentInPrintOnly = true }: FilterPanelProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [, startTransition] = useTransition()

  const setParam = (key: string, value: string | null) => {
    const params = new URLSearchParams(searchParams.toString())
    if (value === null || value === '') {
      params.delete(key)
    } else {
      params.set(key, value)
    }
    params.delete('page')
    startTransition(() => router.push(`${pathname}?${params}`))
  }

  return (
    <aside className="w-full md:w-52 shrink-0 space-y-6">
      {/* Format filter */}
      <div>
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Format
        </h3>
        <ul className="space-y-1">
          {FORMATS.map((f) => (
            <li key={f.value}>
              <button
                onClick={() => setParam('product_form', f.value || null)}
                className={cn(
                  'w-full text-left text-sm px-2 py-1.5 rounded transition-colors',
                  currentForm === f.value
                    ? 'bg-amber-100 text-amber-800 font-medium'
                    : 'text-slate-600 hover:bg-slate-100',
                )}
              >
                {f.label}
              </button>
            </li>
          ))}
        </ul>
      </div>

      {/* In-print filter */}
      <div>
        <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
          Availability
        </h3>
        <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
          <input
            type="checkbox"
            checked={currentInPrintOnly}
            onChange={(e) => setParam('in_print_only', e.target.checked ? 'true' : 'false')}
            className="rounded border-slate-300 accent-amber-500"
          />
          In-print only
        </label>
      </div>
    </aside>
  )
}
