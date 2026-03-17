'use client'

import { Search, X } from 'lucide-react'
import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { useCallback, useState, useTransition } from 'react'

interface SearchBarProps {
  defaultValue?: string
  placeholder?: string
}

export function SearchBar({ defaultValue = '', placeholder = 'Search books, authors, topics…' }: SearchBarProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [value, setValue] = useState(defaultValue)
  const [isPending, startTransition] = useTransition()

  const updateSearch = useCallback(
    (q: string) => {
      const params = new URLSearchParams(searchParams.toString())
      if (q) {
        params.set('q', q)
      } else {
        params.delete('q')
      }
      params.delete('page') // reset to page 1 on new search
      startTransition(() => {
        router.push(`${pathname}?${params}`)
      })
    },
    [router, pathname, searchParams],
  )

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    updateSearch(value)
  }

  const handleClear = () => {
    setValue('')
    updateSearch('')
  }

  return (
    <form onSubmit={handleSubmit} className="relative flex-1">
      <Search
        className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-400 pointer-events-none"
        size={18}
      />
      <input
        type="search"
        value={value}
        onChange={(e) => setValue(e.target.value)}
        placeholder={placeholder}
        className="w-full pl-10 pr-10 py-2.5 rounded-lg border border-slate-300 bg-white text-sm text-slate-900 placeholder:text-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-500 focus:border-transparent"
        aria-label="Search catalog"
      />
      {value && (
        <button
          type="button"
          onClick={handleClear}
          className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
          aria-label="Clear search"
        >
          <X size={16} />
        </button>
      )}
      {isPending && (
        <div className="absolute right-10 top-1/2 -translate-y-1/2 h-4 w-4 animate-spin rounded-full border-2 border-amber-500 border-t-transparent" />
      )}
    </form>
  )
}
