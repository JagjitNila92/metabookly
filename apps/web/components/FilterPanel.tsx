'use client'

import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { useTransition, useState, useEffect, useRef } from 'react'
import { SlidersHorizontal, X, ChevronDown } from 'lucide-react'
import { cn } from '@/lib/utils'
import type { FacetsResponse } from '@/lib/types'

const SUBJECTS_DEFAULT_VISIBLE = 8

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

interface FilterPanelProps {
  facets: FacetsResponse
  isRetailer?: boolean
  current: {
    product_form: string
    subject_code: string
    pub_date_preset: string
    pub_date_from: string
    pub_date_to: string
    in_print_only: boolean
    uk_rights_only: boolean
    price_band: string
    with_trade_price: boolean
    author: string
    publisher: string
  }
}

export function FilterPanel({ facets, isRetailer = false, current }: FilterPanelProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [, startTransition] = useTransition()

  // Subject list collapse
  const [showAllSubjects, setShowAllSubjects] = useState(false)

  // Controlled inputs with debounced URL push
  const [authorInput, setAuthorInput] = useState(current.author)
  const [publisherInput, setPublisherInput] = useState(current.publisher)
  const [dateFromInput, setDateFromInput] = useState(current.pub_date_from)
  const [dateToInput, setDateToInput] = useState(current.pub_date_to)

  const authorTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const publisherTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const dateFromTimer = useRef<ReturnType<typeof setTimeout> | null>(null)
  const dateToTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Sync local state back from URL (e.g. when clear all fires)
  useEffect(() => { setAuthorInput(current.author) }, [current.author])
  useEffect(() => { setPublisherInput(current.publisher) }, [current.publisher])
  useEffect(() => { setDateFromInput(current.pub_date_from) }, [current.pub_date_from])
  useEffect(() => { setDateToInput(current.pub_date_to) }, [current.pub_date_to])

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

  // Selecting a preset clears any custom range
  const handlePresetClick = (value: string | null) => {
    const params = new URLSearchParams(searchParams.toString())
    params.delete('pub_date_from')
    params.delete('pub_date_to')
    params.delete('page')
    if (value) params.set('pub_date_preset', value)
    else params.delete('pub_date_preset')
    setDateFromInput('')
    setDateToInput('')
    startTransition(() => router.push(`${pathname}?${params}`))
  }

  // Setting a custom date clears any preset
  const handleDateFromChangeWithPresetClear = (value: string) => {
    setDateFromInput(value)
    if (dateFromTimer.current) clearTimeout(dateFromTimer.current)
    dateFromTimer.current = setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString())
      params.delete('pub_date_preset')
      params.delete('page')
      if (value) params.set('pub_date_from', value)
      else params.delete('pub_date_from')
      startTransition(() => router.push(`${pathname}?${params}`))
    }, 600)
  }

  const handleDateToChangeWithPresetClear = (value: string) => {
    setDateToInput(value)
    if (dateToTimer.current) clearTimeout(dateToTimer.current)
    dateToTimer.current = setTimeout(() => {
      const params = new URLSearchParams(searchParams.toString())
      params.delete('pub_date_preset')
      params.delete('page')
      if (value) params.set('pub_date_to', value)
      else params.delete('pub_date_to')
      startTransition(() => router.push(`${pathname}?${params}`))
    }, 600)
  }

  const activeFilterCount = [
    current.product_form,
    current.subject_code,
    current.pub_date_preset,
    current.pub_date_from,
    current.pub_date_to,
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
    setDateFromInput('')
    setDateToInput('')
    const params = new URLSearchParams(searchParams.toString())
    ;[
      'product_form', 'subject_code', 'pub_date_preset', 'pub_date_from', 'pub_date_to',
      'uk_rights_only', 'with_trade_price', 'price_band', 'sort', 'in_print_only',
      'author', 'publisher', 'page',
    ].forEach((k) => params.delete(k))
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

  // Subjects — collapse to SUBJECTS_DEFAULT_VISIBLE, expand on demand
  const visibleSubjects = showAllSubjects
    ? facets.subjects
    : facets.subjects.slice(0, SUBJECTS_DEFAULT_VISIBLE)
  const hiddenCount = facets.subjects.length - SUBJECTS_DEFAULT_VISIBLE

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
            {visibleSubjects.map((s) => (
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
          {hiddenCount > 0 && (
            <button
              onClick={() => setShowAllSubjects((v) => !v)}
              className="mt-1.5 flex items-center gap-1 text-xs text-amber-600 hover:text-amber-700 font-medium px-2"
            >
              <ChevronDown
                size={12}
                className={cn('transition-transform', showAllSubjects && 'rotate-180')}
              />
              {showAllSubjects ? 'Show fewer' : `Show ${hiddenCount} more`}
            </button>
          )}
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
              active={!current.pub_date_preset && !current.pub_date_from && !current.pub_date_to}
              onClick={() => handlePresetClick(null)}
            >
              Any time
            </FilterButton>
          </li>
          {DATE_PRESETS.map((d) => (
            <li key={d.value}>
              <FilterButton
                active={current.pub_date_preset === d.value}
                onClick={() => handlePresetClick(d.value)}
              >
                {d.label}
              </FilterButton>
            </li>
          ))}
        </ul>

        {/* Custom date range */}
        <div className="mt-2 space-y-1.5">
          <p className="text-[11px] text-slate-400 font-medium uppercase tracking-wide px-1">
            Custom range
          </p>
          <div>
            <label className="text-xs text-slate-500 px-1">From</label>
            <input
              type="date"
              value={dateFromInput}
              onChange={(e) => handleDateFromChangeWithPresetClear(e.target.value)}
              className="w-full mt-0.5 text-sm px-2 py-1.5 border border-slate-200 rounded bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-amber-400"
            />
          </div>
          <div>
            <label className="text-xs text-slate-500 px-1">To</label>
            <input
              type="date"
              value={dateToInput}
              onChange={(e) => handleDateToChangeWithPresetClear(e.target.value)}
              className="w-full mt-0.5 text-sm px-2 py-1.5 border border-slate-200 rounded bg-white text-slate-700 focus:outline-none focus:ring-2 focus:ring-amber-400"
            />
          </div>
        </div>
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
