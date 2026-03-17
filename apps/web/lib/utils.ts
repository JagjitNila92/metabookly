import { type ClassValue, clsx } from 'clsx'
import { twMerge } from 'tailwind-merge'

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs))
}

/** ONIX ProductForm code → human label */
export const PRODUCT_FORM: Record<string, string> = {
  BA: 'Book',
  BB: 'Hardback',
  BC: 'Paperback',
  BG: 'Spiral-bound',
  BJ: 'Loose-leaf',
  DG: 'E-book',
  DH: 'E-book (subscription)',
  PI: 'Audiobook CD',
  AJ: 'Audiobook download',
}

/** ONIX ContributorRole → human label */
export const CONTRIBUTOR_ROLE: Record<string, string> = {
  A01: 'Author',
  A02: 'With',
  A03: 'Screenplay',
  A06: 'Composer',
  A11: 'Illustrated by',
  A12: 'Illustrated by',
  A36: 'Translated by',
  A38: 'Adapted by',
  B01: 'Edited by',
  B02: 'Edited by',
  B06: 'Edited by',
  D04: 'Read by',
}

/** ONIX PublishingStatus → badge label */
export const PUBLISHING_STATUS: Record<string, { label: string; color: string }> = {
  '02': { label: 'Forthcoming', color: 'amber' },
  '04': { label: 'Active', color: 'green' },
  '06': { label: 'Out of print', color: 'red' },
  '07': { label: 'Recalled', color: 'red' },
  '11': { label: 'Withdrawn', color: 'red' },
}

export function formatRRP(value: string | null, currency = 'GBP'): string | null {
  if (!value) return null
  const num = parseFloat(value)
  if (isNaN(num)) return null
  return new Intl.NumberFormat('en-GB', {
    style: 'currency',
    currency,
    minimumFractionDigits: 2,
  }).format(num)
}

export function formatDate(iso: string | null): string | null {
  if (!iso) return null
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  })
}

export function primaryAuthor(contributors: { role_code: string; person_name: string }[]): string {
  const author = contributors.find((c) => c.role_code === 'A01')
  return author?.person_name ?? ''
}

export function contributorsByRole(
  contributors: { role_code: string; person_name: string }[],
): { label: string; names: string[] }[] {
  const groups: Record<string, string[]> = {}
  for (const c of contributors) {
    const label = CONTRIBUTOR_ROLE[c.role_code] ?? 'Contributor'
    if (!groups[label]) groups[label] = []
    groups[label].push(c.person_name)
  }
  return Object.entries(groups).map(([label, names]) => ({ label, names }))
}
