export interface Publisher {
  id: string
  name: string
  imprint: string | null
}

export interface Contributor {
  id: string
  role_code: string
  person_name: string
  person_name_inverted: string | null
  bio: string | null
  sequence_number: number
}

export interface Subject {
  scheme_id: string
  subject_code: string
  subject_heading: string | null
  main_subject: boolean
}

export interface BookSummary {
  imprint: string | null
  id: string
  isbn13: string
  title: string
  subtitle: string | null
  product_form: string
  language_code: string
  publication_date: string | null
  cover_image_url: string | null
  out_of_print: boolean
  publishing_status: string | null
  uk_rights: boolean | null
  rrp_gbp: string | null
  rrp_usd: string | null
  publisher: Publisher | null
  contributors: Contributor[]
}

export interface BookDetail extends BookSummary {
  isbn10: string | null
  edition_number: number | null
  edition_statement: string | null
  page_count: number | null
  description: string | null
  toc: string | null
  excerpt: string | null
  audience_code: string | null
  product_form_detail: string | null
  height_mm: number | null
  width_mm: number | null
  subjects: Subject[]
  created_at: string
  updated_at: string
}

export interface SearchResponse {
  results: BookSummary[]
  total: number
  page: number
  page_size: number
  pages: number
  query: string | null
}

export interface SubjectFacet {
  code: string
  label: string
  count: number
}

export interface FormatFacet {
  code: string
  label: string
  count: number
}

export interface FacetsResponse {
  subjects: SubjectFacet[]
  formats: FormatFacet[]
}

// ─── Basket ───────────────────────────────────────────────────────────────────

export interface RoutedItem {
  isbn13: string
  title: string | null
  cover_image_url: string | null
  quantity: number
  preferred_distributor_code: string | null
  routed_distributor_code: string | null
  trade_price_gbp: string | null
  rrp_gbp: string | null
  margin_pct: string | null
}

export interface BasketResponse {
  item_count: number
  total_cost_gbp: string | null
  avg_margin_pct: string | null
  items: RoutedItem[]
}

// ─── Orders ───────────────────────────────────────────────────────────────────

export interface OrderLineItem {
  id: string
  isbn13: string
  title: string | null
  quantity_ordered: number
  quantity_confirmed: number | null
  quantity_despatched: number | null
  quantity_invoiced: number | null
  status: string
  expected_despatch_date: string | null
  trade_price_gbp: string | null
  rrp_gbp: string | null
}

export interface OrderLine {
  id: string
  distributor_code: string
  status: string
  transmission_attempts: number
  external_po_ref: string | null
  tracking_ref: string | null
  estimated_delivery_date: string | null
  subtotal_gbp: string | null
  items: OrderLineItem[]
}

export interface Order {
  id: string
  po_number: string
  status: string
  delivery_type: string
  total_lines: number | null
  total_gbp: string | null
  submitted_at: string | null
  created_at: string
  lines: OrderLine[]
}

export interface OrderSummary {
  id: string
  po_number: string
  status: string
  total_lines: number | null
  total_gbp: string | null
  submitted_at: string | null
  created_at: string
}

export interface OrdersPage {
  orders: OrderSummary[]
  next_cursor: string | null
}

export interface BackorderItem {
  order_id: string
  order_line_id: string
  item_id: string
  po_number: string
  distributor_code: string
  isbn13: string
  title: string | null
  quantity_ordered: number
  expected_despatch_date: string | null
}

export interface BackordersPage {
  items: BackorderItem[]
  next_cursor: string | null
}

export interface InvoiceResponse {
  id: string
  order_line_id: string
  invoice_number: string
  invoice_date: string
  net_gbp: string
  vat_gbp: string
  gross_gbp: string
}

// ─── Settings ─────────────────────────────────────────────────────────────────

export interface RetailerSettings {
  notify_order_submitted: boolean
  notify_backorder_alert: boolean
  notify_invoice_available: boolean
}

export interface Address {
  id: string
  address_type: 'billing' | 'delivery'
  label: string
  contact_name: string
  line1: string
  line2: string | null
  city: string
  county: string | null
  postcode: string
  country_code: string
  is_default: boolean
  created_at: string
}

export interface RetailerProfile {
  id: string
  company_name: string
  email: string
  country_code: string
  san: string | null
  accounts: LinkedAccount[]
}

export interface LinkedAccount {
  id: string
  distributor_code: string
  distributor_name: string
  account_number: string | null
  status: string
  rejection_reason: string | null
  created_at: string
}
