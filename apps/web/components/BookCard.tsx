import Link from 'next/link'
import { BookCover } from './BookCover'
import { PRODUCT_FORM, formatRRP, primaryAuthor } from '@/lib/utils'
import type { BookSummary } from '@/lib/types'

interface BookCardProps {
  book: BookSummary
  isAuthenticated?: boolean
}

export function BookCard({ book, isAuthenticated = false }: BookCardProps) {
  const author = primaryAuthor(book.contributors)
  const form = PRODUCT_FORM[book.product_form] ?? book.product_form
  const rrp = formatRRP(book.rrp_gbp)

  return (
    <Link
      href={`/books/${book.isbn13}`}
      className="group flex flex-col bg-white rounded-lg border border-slate-200 overflow-hidden hover:border-amber-400 hover:shadow-md transition-all duration-150"
    >
      {/* Cover */}
      <div className="relative w-full aspect-[2/3] bg-slate-50">
        <BookCover url={book.cover_image_url} isbn13={book.isbn13} title={book.title} className="absolute inset-0" />
        {/* Out-of-print ribbon */}
        {book.out_of_print && (
          <div className="absolute top-2 left-0 bg-red-500 text-white text-[10px] font-medium px-2 py-0.5 rounded-r">
            Out of print
          </div>
        )}
        {book.publishing_status === '02' && !book.out_of_print && (
          <div className="absolute top-2 left-0 bg-amber-500 text-white text-[10px] font-medium px-2 py-0.5 rounded-r">
            Forthcoming
          </div>
        )}
      </div>

      {/* Metadata */}
      <div className="flex flex-col flex-1 p-3 gap-1">
        <p className="text-xs font-medium text-amber-600 uppercase tracking-wide truncate">
          {form}
        </p>
        <h3 className="text-sm font-semibold text-slate-900 leading-snug line-clamp-2 group-hover:text-amber-700 transition-colors">
          {book.title}
        </h3>
        {author && (
          <p className="text-xs text-slate-500 truncate">{author}</p>
        )}
        {book.publisher && (
          <p className="text-xs text-slate-400 truncate">{book.publisher.name}</p>
        )}
        <div className="flex items-center justify-between mt-auto pt-2">
          {rrp ? (
            <span
              className="text-sm font-semibold text-slate-800"
              style={!isAuthenticated ? { filter: 'blur(4px)', opacity: 0.6, userSelect: 'none' } : undefined}
              aria-hidden={!isAuthenticated}
            >
              {rrp}
            </span>
          ) : (
            <span />
          )}
          {book.publication_date && (
            <span className="text-xs text-slate-400">
              {new Date(book.publication_date).getFullYear()}
            </span>
          )}
        </div>
      </div>
    </Link>
  )
}
