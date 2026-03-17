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
