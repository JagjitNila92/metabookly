import type {
  Address, BackordersPage, BasketResponse, BookDetail, FacetsResponse,
  InvoiceResponse, Order, OrdersPage, RetailerProfile, RetailerSettings, SearchResponse,
} from './types'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${API}${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    next: { revalidate: 60 },
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
  language_code?: string
  pub_date_from?: string
  pub_date_to?: string
  pub_date_preset?: string   // "new" | "recent" | "coming_soon" | "backlist"
  in_print_only?: boolean
  uk_rights_only?: boolean
  price_band?: string        // "under10" | "10to20" | "over20"
  with_trade_price?: boolean // filter to titles the retailer's approved distributors carry
  sort?: string              // "newest" | "oldest" | "title_az" | "price_asc" | "price_desc" | "relevance" | "popular"
  page?: number
  page_size?: number
  accessToken?: string       // forwarded as Authorization header for auth-aware filters
}

export function searchBooks(params: SearchParams): Promise<SearchResponse> {
  const qs = new URLSearchParams()
  if (params.q) qs.set('q', params.q)
  if (params.author) qs.set('author', params.author)
  if (params.publisher) qs.set('publisher', params.publisher)
  if (params.product_form) qs.set('product_form', params.product_form)
  if (params.subject_code) qs.set('subject_code', params.subject_code)
  if (params.language_code) qs.set('language_code', params.language_code)
  if (params.pub_date_from) qs.set('pub_date_from', params.pub_date_from)
  if (params.pub_date_to) qs.set('pub_date_to', params.pub_date_to)
  if (params.pub_date_preset) qs.set('pub_date_preset', params.pub_date_preset)
  if (params.in_print_only !== undefined) qs.set('in_print_only', String(params.in_print_only))
  if (params.uk_rights_only) qs.set('uk_rights_only', 'true')
  if (params.price_band) qs.set('price_band', params.price_band)
  if (params.with_trade_price) qs.set('with_trade_price', 'true')
  if (params.sort) qs.set('sort', params.sort)
  if (params.page) qs.set('page', String(params.page))
  if (params.page_size) qs.set('page_size', String(params.page_size))

  const headers: Record<string, string> = {}
  if (params.accessToken) headers['Authorization'] = `Bearer ${params.accessToken}`

  return apiFetch<SearchResponse>(`/api/v1/catalog/search?${qs}`, {
    headers,
  })
}

export function getBook(isbn13: string): Promise<BookDetail> {
  return apiFetch<BookDetail>(`/api/v1/books/${isbn13}`)
}

export function getCatalogFacets(): Promise<FacetsResponse> {
  return apiFetch<FacetsResponse>('/api/v1/catalog/facets', {
    next: { revalidate: 300 }, // cache facets for 5 minutes
  } as RequestInit)
}

// ─── Client-side auth'd fetch (used in client components) ─────────────────────

export async function authFetch<T>(
  path: string,
  options?: RequestInit,
): Promise<T> {
  // Client-side: calls Next.js API routes which add the auth header server-side
  const res = await fetch(path, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail ?? err.error ?? `Error ${res.status}`)
  }
  return res.json()
}

// ─── Basket ───────────────────────────────────────────────────────────────────

export const getBasket = () => authFetch<BasketResponse>('/api/basket')

export const addToBasket = (isbn13: string, quantity = 1, preferred_distributor_code?: string) =>
  authFetch<BasketResponse>('/api/basket/items', {
    method: 'POST',
    body: JSON.stringify({ isbn13, quantity, preferred_distributor_code }),
  })

export const updateBasketItem = (isbn13: string, updates: { quantity?: number; preferred_distributor_code?: string }) =>
  authFetch<BasketResponse>(`/api/basket/items/${isbn13}`, {
    method: 'PATCH',
    body: JSON.stringify(updates),
  })

export const removeFromBasket = (isbn13: string) =>
  authFetch<BasketResponse>(`/api/basket/items/${isbn13}`, { method: 'DELETE' })

export const clearBasket = () =>
  fetch('/api/basket', { method: 'DELETE' })

export const submitBasket = (body: {
  delivery_address_id?: string
  delivery_address?: { contact_name: string; line1: string; line2?: string; city: string; county?: string; postcode: string; country_code?: string }
  billing_address_id?: string
}) => authFetch<Order>('/api/basket/submit', { method: 'POST', body: JSON.stringify(body) })

// ─── Orders ───────────────────────────────────────────────────────────────────

export const getOrders = (params?: { status?: string; from_date?: string; to_date?: string; distributor_code?: string; cursor?: string }) => {
  const qs = new URLSearchParams()
  if (params?.status) qs.set('status', params.status)
  if (params?.from_date) qs.set('from_date', params.from_date)
  if (params?.to_date) qs.set('to_date', params.to_date)
  if (params?.distributor_code) qs.set('distributor_code', params.distributor_code)
  if (params?.cursor) qs.set('cursor', params.cursor)
  return authFetch<OrdersPage>(`/api/orders?${qs}`)
}

export const getBackorders = (params?: { distributor_code?: string; cursor?: string }) => {
  const qs = new URLSearchParams()
  if (params?.distributor_code) qs.set('distributor_code', params.distributor_code)
  if (params?.cursor) qs.set('cursor', params.cursor)
  return authFetch<BackordersPage>(`/api/orders/backorders?${qs}`)
}

export const getOrder = (id: string) => authFetch<Order>(`/api/orders/${id}`)

export const cancelOrder = (id: string) =>
  fetch(`/api/orders/${id}`, { method: 'DELETE' })

export const cancelOrderLine = (orderId: string, lineId: string) =>
  fetch(`/api/orders/${orderId}/lines/${lineId}`, { method: 'DELETE' })

export const getInvoice = (orderId: string) =>
  authFetch<InvoiceResponse>(`/api/orders/${orderId}/invoice`)

export const advanceOrder = (id: string) =>
  authFetch<Order>(`/api/orders/${id}/advance`, { method: 'POST' })

// ─── Settings ─────────────────────────────────────────────────────────────────

export const getRetailerProfile = () => authFetch<RetailerProfile>('/api/retailer/me')

export const updateRetailerProfile = (body: { company_name?: string; country_code?: string; san?: string }) =>
  authFetch<RetailerProfile>('/api/retailer/me', { method: 'PATCH', body: JSON.stringify(body) })

export const getSettings = () => authFetch<RetailerSettings>('/api/settings')

export const updateSettings = (body: Partial<RetailerSettings>) =>
  authFetch<RetailerSettings>('/api/settings', { method: 'PATCH', body: JSON.stringify(body) })

export const getAddresses = (type?: 'billing' | 'delivery') => {
  const qs = type ? `?address_type=${type}` : ''
  return authFetch<Address[]>(`/api/settings/addresses${qs}`)
}

export const createAddress = (body: Omit<Address, 'id' | 'created_at'>) =>
  authFetch<Address>('/api/settings/addresses', { method: 'POST', body: JSON.stringify(body) })

export const updateAddress = (id: string, body: Partial<Omit<Address, 'id' | 'created_at'>>) =>
  authFetch<Address>(`/api/settings/addresses/${id}`, { method: 'PATCH', body: JSON.stringify(body) })

export const deleteAddress = (id: string) =>
  fetch(`/api/settings/addresses/${id}`, { method: 'DELETE' })
