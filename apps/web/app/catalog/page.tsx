import { Suspense } from 'react'
import type { Metadata } from 'next'
import { searchBooks } from '@/lib/api'
import { BookCard } from '@/components/BookCard'
import { SearchBar } from '@/components/SearchBar'
import { FilterPanel } from '@/components/FilterPanel'
import { Pagination } from '@/components/Pagination'

export const metadata: Metadata = { title: 'Catalog' }

interface PageProps {
  searchParams: {
    q?: string
    author?: string
    publisher?: string
    product_form?: string
    in_print_only?: string
    page?: string
  }
}

export default async function CatalogPage({ searchParams }: PageProps) {
  const page = Number(searchParams.page ?? 1)
  const inPrintOnly = searchParams.in_print_only !== 'false'

  const data = await searchBooks({
    q: searchParams.q,
    author: searchParams.author,
    publisher: searchParams.publisher,
    product_form: searchParams.product_form,
    in_print_only: inPrintOnly,
    page,
    page_size: 24,
  })

  const hasQuery = !!(searchParams.q || searchParams.author || searchParams.publisher || searchParams.product_form)

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6">
      {/* Search header */}
      <div className="mb-6 flex flex-col sm:flex-row gap-3 items-start sm:items-center">
        <div className="flex-1 w-full">
          <Suspense>
            <SearchBar defaultValue={searchParams.q ?? ''} />
          </Suspense>
        </div>
        <p className="text-sm text-slate-500 shrink-0">
          {data.total.toLocaleString()} title{data.total !== 1 ? 's' : ''}
          {hasQuery && searchParams.q ? ` for "${searchParams.q}"` : ''}
        </p>
      </div>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Filters */}
        <Suspense>
          <FilterPanel
            currentForm={searchParams.product_form ?? ''}
            currentInPrintOnly={inPrintOnly}
          />
        </Suspense>

        {/* Results */}
        <div className="flex-1 min-w-0">
          {data.results.length === 0 ? (
            <div className="text-center py-20 text-slate-400">
              <p className="text-lg font-medium mb-1">No books found</p>
              <p className="text-sm">Try a different search term or adjust the filters.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4 mb-6">
                {data.results.map((book) => (
                  <BookCard key={book.id} book={book} />
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
