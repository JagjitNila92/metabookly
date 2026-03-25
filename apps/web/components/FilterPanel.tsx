'use client'

import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { useTransition, useState, useEffect, useRef } from 'react'
import { SlidersHorizontal, X } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { FacetsResponse } from '@/lib/types'

const DATE_PRESETS = [
  { value: 'new', label: 'New this month' },
  { value: 'recent', label: 'Last 3 months' },
  { value: 'coming_soon', label: 'Coming soon' },
  { value: 'backlist', label: 'Backlist' },
]

const PRICE_BANDS = [
  { value: 'under10', label: 'Under £10' },
  { value: '10to20', label: '£10 – £20' },
  { value: 'over20', label: 'Over £20' },
]

const SORT_OPTIONS = [
  { value: '', label: 'Relevance / Newest' },
  { value: 'popular', label: 'Most popular' },
  { value: 'newest', label: 'Newest first' },
  { value: 'oldest', label: 'Oldest first' },
  { value: 'title_az', label: 'Title A–Z' },
  { value: 'price_asc', label: 'Price: low–high' },
  { value: 'price_desc', label: 'Price: high–low' },
]

interface FilterPanelProps {
  facets: FacetsResponse
  isRetailer?: boolean
  current: {
    product_form: string
    subject_code: string
    pub_date_preset: string
    in_print_only: boolean
    uk_rights_only: boolean
    price_band: string
    with_trade_price: boolean
    sort: string
    author: string
    publisher: string
  }
}

export function FilterPanel({ facets, isRetailer = false, current }: FilterPanelProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [, startTransition] = useTransition()

  // Controlled inputs for author/publisher with debounced URL push
  const [authorInput, setAuthorInput] = useState(current.author)
  const [publisherInput, setPublisherInput] = useState(current.publisher)
  const authorTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const publisherTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Keep local state in sync when URL changes (e.g. clear all)
  useEffect(() => { setAuthorInput(current.author) }, [current.author])
  useEffect(() => { setPublisherInput(current.publisher) }, [current.publisher])

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

  const toggleParam = (key: string, currentValue: boolean) => {
    setParam(key, currentValue ? null : 'true')
  }

  const handleAuthorChange = (value: string) => {
    setAuthorInput(value)
    if (authorTimer.current) clearTimeout(authorTimer.current)
    authorTimer.current = setTimeout(() => setParam('author', value || null), 400)
  }

  const handlePublisherChange = (value: string) => {
    setPublisherInput(value)
    if (publisherTimer.current) clearTimeout(publisherTimer.current)
    publisherTimer.current = setTimeout(() => setParam('publisher', value || null), 400)
  }

  const activeFilterCount = [
    current.product_form,
    current.subject_code,
    current.pub_date_preset,
    current.uk_rights_only,
    current.with_trade_price,
    current.price_band,
    authorInput,
    publisherInput,
    !current.in_print_only ? 'oop' : null,
  ].filter(Boolean).length

  const clearAll = () => {
    setAuthorInput('')
    setPublisherInput('')
    const params = new URLSearchParams(searchParams.toString())
    ;['product_form', 'subject_code', 'pub_date_preset', 'uk_rights_only', 'with_trade_price',
      'price_band', 'sort', 'in_print_only', 'author', 'publisher', 'page'].forEach(k => params.delete(k))
    startTransition(() => router.push(`${pathname}?${params}`))
  }

  const SectionLabel = ({ children }: { children: React.ReactNode }) => (
    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">
      {children}
    </h3>
  )

  const FilterButton = ({
    active,
    onClick,
    children,
  }: {
    active: boolean
    onClick: () => void
    children: React.ReactNode
  }) => (
    <button
      onClick={onClick}
      className={cn(
        'w-full text-left text-sm px-2 py-1.5 rounded transition-colors',
        active
          ? 'bg-amber-100 text-amber-800 font-medium'
          : 'text-slate-600 hover:bg-slate-100',
      )}
    >
      {children}
    </button>
  )

  const TextInput = ({
    value,
    onChange,
    placeholder,
  }: {
    value: string
    onChange: (v: string) => void
    placeholder: string
  }) => (
    <input
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      className="w-full text-sm px-2 py-1.5 border border-slate-200 rounded bg-white text-slate-700 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-amber-400"
    />
  )

  return (
    <aside className="w-full md:w-56 shrink-0 space-y-6">

      {/* Header + clear */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-1.5 text-xs font-semibold text-slate-500 uppercase tracking-wide">
          <SlidersHorizontal size={13} />
          Filters
          {activeFilterCount > 0 && (
            <span className="ml-1 bg-amber-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center">
              {activeFilterCount}
            </span>
          )}
        </div>
        {activeFilterCount > 0 && (
          <button
            onClick={clearAll}
            className="flex items-center gap-1 text-xs text-slate-400 hover:text-slate-600"
          >
            <X size={11} /> Clear all
          </button>
        )}
      </div>

      {/* Sort */}
      <div>
        <SectionLabel>Sort by</SectionLabel>
        <select
          value={current.sort}
          onChange={(e) => setParam('sort', e.target.value || null)}
          className="w-full text-sm px-2 py-1.5 border border-slate-200 rounded bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-amber-400"
        >
          {SORT_OPTIONS.map((o) => (
            <option key={o.value} value={o.value}>{o.label}</option>
          ))}
        </select>
      </div>

      {/* Author */}
      <div>
        <SectionLabel>Author</SectionLabel>
        <TextInput
          value={authorInput}
          onChange={handleAuthorChange}
          placeholder="Search by author…"
        />
      </div>

      {/* Publisher */}
      <div>
        <SectionLabel>Publisher</SectionLabel>
        <TextInput
          value={publisherInput}
          onChange={handlePublisherChange}
          placeholder="Search by publisher…"
        />
      </div>

      {/* Subject categories */}
      {facets.subjects.length > 0 && (
        <div>
          <SectionLabel>Category</SectionLabel>
          <ul className="space-y-0.5">
            <li>
              <FilterButton
                active={!current.subject_code}
                onClick={() => setParam('subject_code', null)}
              >
                All categories
              </FilterButton>
            </li>
            {facets.subjects.map((s) => (
              <li key={s.code}>
                <FilterButton
                  active={current.subject_code === s.code}
                  onClick={() => setParam('subject_code', s.code)}
                >
                  <span className="flex items-center justify-between">
                    <span className="truncate pr-2">{s.label}</span>
                    <span className="text-xs text-slate-400 shrink-0">{s.count}</span>
                  </span>
                </FilterButton>
              </li>
            ))}
          </ul>
        </div>
      )}

      {/* Format */}
      <div>
        <SectionLabel>Format</SectionLabel>
        <ul className="space-y-0.5">
          <li>
            <FilterButton
              active={!current.product_form}
              onClick={() => setParam('product_form', null)}
            >
              All formats
            </FilterButton>
          </li>
          {facets.formats.map((f) => (
            <li key={f.code}>
              <FilterButton
                active={current.product_form === f.code}
                onClick={() => setParam('product_form', f.code)}
              >
                <span className="flex items-center justify-between">
                  <span>{f.label}</span>
                  <span className="text-xs text-slate-400">{f.count}</span>
                </span>
              </FilterButton>
            </li>
          ))}
        </ul>
      </div>

      {/* Publication date */}
      <div>
        <SectionLabel>Publication date</SectionLabel>
        <ul className="space-y-0.5">
          <li>
            <FilterButton
              active={!current.pub_date_preset}
              onClick={() => setParam('pub_date_preset', null)}
            >
              Any time
            </FilterButton>
          </li>
          {DATE_PRESETS.map((d) => (
            <li key={d.value}>
              <FilterButton
                active={current.pub_date_preset === d.value}
                onClick={() => setParam('pub_date_preset', d.value)}
              >
                {d.label}
              </FilterButton>
            </li>
          ))}
        </ul>
      </div>

      {/* Price band */}
      <div>
        <SectionLabel>Price (RRP)</SectionLabel>
        <ul className="space-y-0.5">
          <li>
            <FilterButton
              active={!current.price_band}
              onClick={() => setParam('price_band', null)}
            >
              Any price
            </FilterButton>
          </li>
          {PRICE_BANDS.map((p) => (
            <li key={p.value}>
              <FilterButton
                active={current.price_band === p.value}
                onClick={() => setParam('price_band', p.value)}
              >
                {p.label}
              </FilterButton>
            </li>
          ))}
        </ul>
      </div>

      {/* Trade options */}
      <div>
        <SectionLabel>Trade options</SectionLabel>
        <div className="space-y-2">
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={current.in_print_only}
              onChange={() => toggleParam('in_print_only', !current.in_print_only)}
              className="rounded border-slate-300 accent-amber-500"
            />
            In-print only
          </label>
          <label className="flex items-center gap-2 text-sm text-slate-600 cursor-pointer">
            <input
              type="checkbox"
              checked={current.uk_rights_only}
              onChange={() => toggleParam('uk_rights_only', current.uk_rights_only)}
              className="rounded border-slate-300 accent-amber-500"
            />
            UK rights only
          </label>
          {isRetailer && (
            <label className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                checked={current.with_trade_price}
                onChange={() => toggleParam('with_trade_price', current.with_trade_price)}
                className="rounded border-slate-300 accent-amber-500"
              />
              <span className="text-amber-700 font-medium">With my trade price</span>
            </label>
          )}
        </div>
      </div>

    </aside>
  )
}
