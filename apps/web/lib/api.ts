import type { BookDetail, SearchResponse } from './types'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    next: { revalidate: 60 }, // cache for 60s on server components
  })
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${path}`)
  }
  return res.json()
}

export interface SearchParams {
  q?: string
  author?: string
  publisher?: string
  product_form?: string
  subject_code?: string
  in_print_only?: boolean
  page?: number
  page_size?: number
}

export function searchBooks(params: SearchParams): Promise<SearchResponse> {
  const qs = new URLSearchParams()
  if (params.q) qs.set('q', params.q)
  if (params.author) qs.set('author', params.author)
  if (params.publisher) qs.set('publisher', params.publisher)
  if (params.product_form) qs.set('product_form', params.product_form)
  if (params.subject_code) qs.set('subject_code', params.subject_code)
  if (params.in_print_only !== undefined) qs.set('in_print_only', String(params.in_print_only))
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))
  return apiFetch<SearchResponse>(`/api/v1/catalog/search?${qs}`)
}

export function getBook(isbn13: string): Promise<BookDetail> {
  return apiFetch<BookDetail>(`/api/v1/books/${isbn13}`)
}
