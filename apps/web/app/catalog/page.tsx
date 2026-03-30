import { Suspense } from 'react'
import type { Metadata } from 'next'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'
import { searchBooks, getCatalogFacets } from '@/lib/api'
import { BookCard } from '@/components/BookCard'
import { SearchBar } from '@/components/SearchBar'
import { FilterPanel } from '@/components/FilterPanel'
import { Pagination } from '@/components/Pagination'
import { ActiveFilters } from '@/components/ActiveFilters'
import { ResultsToolbar } from '@/components/ResultsToolbar'

export const metadata: Metadata = { title: 'Catalog' }

interface PageProps {
  searchParams: {
    q?: string
    author?: string
    publisher?: string
    product_form?: string
    subject_code?: string
    pub_date_preset?: string
    pub_date_from?: string
    pub_date_to?: string
    in_print_only?: string
    uk_rights_only?: string
    price_band?: string
    with_trade_price?: string
    sort?: string
    page?: string
  }
}

export default async function CatalogPage({ searchParams }: PageProps) {
  const session = await getServerSession(authOptions)
  const isRetailer = (session?.groups ?? []).some(
    (g: string) => g === 'retailers' || g === 'admins',
  )

  const page = Number(searchParams.page ?? 1)
  const inPrintOnly = searchParams.in_print_only !== 'false'
  const ukRightsOnly = searchParams.uk_rights_only === 'true'
  const withTradePrice = isRetailer && searchParams.with_trade_price === 'true'

  const [data, facets] = await Promise.all([
    searchBooks({
      q: searchParams.q,
      author: searchParams.author,
      publisher: searchParams.publisher,
      product_form: searchParams.product_form,
      subject_code: searchParams.subject_code,
      pub_date_preset: searchParams.pub_date_preset,
      pub_date_from: searchParams.pub_date_from,
      pub_date_to: searchParams.pub_date_to,
      in_print_only: inPrintOnly,
      uk_rights_only: ukRightsOnly,
      price_band: searchParams.price_band,
      with_trade_price: withTradePrice,
      sort: searchParams.sort,
      page,
      page_size: 24,
      accessToken: withTradePrice ? (session?.accessToken ?? undefined) : undefined,
    }),
    getCatalogFacets(),
  ])

  const currentFilters = {
    author: searchParams.author ?? '',
    publisher: searchParams.publisher ?? '',
    product_form: searchParams.product_form ?? '',
    subject_code: searchParams.subject_code ?? '',
    pub_date_preset: searchParams.pub_date_preset ?? '',
    pub_date_from: searchParams.pub_date_from ?? '',
    pub_date_to: searchParams.pub_date_to ?? '',
    in_print_only: inPrintOnly,
    uk_rights_only: ukRightsOnly,
    price_band: searchParams.price_band ?? '',
    with_trade_price: withTradePrice,
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Search bar */}
      <div className="mb-6">
        <Suspense>
          <SearchBar defaultValue={searchParams.q ?? ''} />
        </Suspense>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Filter sidebar */}
        <Suspense>
          <FilterPanel
            facets={facets}
            isRetailer={isRetailer}
            current={currentFilters}
          />
        </Suspense>

        {/* Results column */}
        <div className="flex-1 min-w-0">
          {/* Active filter chips */}
          <Suspense>
            <ActiveFilters facets={facets} current={currentFilters} />
          </Suspense>

          {/* Results count + sort */}
          <Suspense>
            <ResultsToolbar total={data.total} query={searchParams.q} />
          </Suspense>

          {data.results.length === 0 ? (
            <div className="text-center py-20 text-slate-400">
              <p className="text-lg font-medium mb-1">No books found</p>
              <p className="text-sm">Try a different search term or adjust the filters.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 mb-6">
                {data.results.map((book) => (
                  <BookCard key={book.id} book={book} isAuthenticated={!!session} />
                ))}
              </div>
              <Suspense>
                <Pagination page={data.page} pages={data.pages} total={data.total} />
              </Suspense>
            </>
          )}
        </div>
      </div>
    </div>
  )
}
