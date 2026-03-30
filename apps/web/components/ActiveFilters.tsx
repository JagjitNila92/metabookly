'use client'

import { useRouter, usePathname, useSearchParams } from 'next/navigation'
import { useTransition } from 'react'
import { X } from 'lucide-react'
import type { FacetsResponse } from '@/lib/types'

const DATE_LABELS: Record<string, string> = {
  new: 'New this month',
  recent: 'Last 3 months',
  coming_soon: 'Coming soon',
  backlist: 'Backlist',
}

const PRICE_LABELS: Record<string, string> = {
  under10: 'Under £10',
  '10to20': '£10–£20',
  over20: 'Over £20',
}

const FORM_LABELS: Record<string, string> = {
  BB: 'Hardback',
  BC: 'Paperback',
  BA: 'Trade paperback',
  BG: 'Spiral bound',
  AC: 'Audio CD',
  AJ: 'Downloadable audio',
  DG: 'E-book',
  DH: 'E-book',
  PI: 'Illustrated',
  ZZ: 'Other',
}

interface ActiveFiltersProps {
  facets: FacetsResponse
  current: {
    author: string
    publisher: string
    product_form: string
    subject_code: string
    pub_date_preset: string
    pub_date_from: string
    pub_date_to: string
    in_print_only: boolean
    uk_rights_only: boolean
    price_band: string
    with_trade_price: boolean
  }
}

export function ActiveFilters({ facets, current }: ActiveFiltersProps) {
  const router = useRouter()
  const pathname = usePathname()
  const searchParams = useSearchParams()
  const [, startTransition] = useTransition()

  const removeParam = (...keys: string[]) => {
    const params = new URLSearchParams(searchParams.toString())
    keys.forEach((k) => params.delete(k))
    params.delete('page')
    startTransition(() => router.push(`${pathname}?${params}`))
  }

  const chips: { label: string; onRemove: () => void }[] = []

  if (current.author) {
    chips.push({ label: `Author: ${current.author}`, onRemove: () => removeParam('author') })
  }
  if (current.publisher) {
    chips.push({ label: `Publisher: ${current.publisher}`, onRemove: () => removeParam('publisher') })
  }
  if (current.product_form) {
    const label = FORM_LABELS[current.product_form] ?? current.product_form
    chips.push({ label: `Format: ${label}`, onRemove: () => removeParam('product_form') })
  }
  if (current.subject_code) {
    const subject = facets.subjects.find((s) => s.code === current.subject_code)
    chips.push({
      label: `Category: ${subject?.label ?? current.subject_code}`,
      onRemove: () => removeParam('subject_code'),
    })
  }
  if (current.pub_date_preset) {
    chips.push({
      label: DATE_LABELS[current.pub_date_preset] ?? current.pub_date_preset,
      onRemove: () => removeParam('pub_date_preset'),
    })
  }
  if (current.pub_date_from) {
    chips.push({ label: `From: ${current.pub_date_from}`, onRemove: () => removeParam('pub_date_from') })
  }
  if (current.pub_date_to) {
    chips.push({ label: `To: ${current.pub_date_to}`, onRemove: () => removeParam('pub_date_to') })
  }
  if (!current.in_print_only) {
    chips.push({ label: 'Including out of print', onRemove: () => removeParam('in_print_only') })
  }
  if (current.uk_rights_only) {
    chips.push({ label: 'UK rights only', onRemove: () => removeParam('uk_rights_only') })
  }
  if (current.price_band) {
    chips.push({
      label: PRICE_LABELS[current.price_band] ?? current.price_band,
      onRemove: () => removeParam('price_band'),
    })
  }
  if (current.with_trade_price) {
    chips.push({ label: 'With my trade price', onRemove: () => removeParam('with_trade_price') })
  }

  if (chips.length === 0) return null

  return (
    <div className="flex flex-wrap gap-2 mb-4">
      {chips.map((chip) => (
        <span
          key={chip.label}
          className="inline-flex items-center gap-1 bg-amber-50 border border-amber-200 text-amber-800 text-xs font-medium px-2.5 py-1 rounded-full"
        >
          {chip.label}
          <button
            onClick={chip.onRemove}
            className="hover:text-amber-600 transition-colors ml-0.5"
            aria-label={`Remove ${chip.label} filter`}
          >
            <X size={11} />
          </button>
        </span>
      ))}
    </div>
  )
}
