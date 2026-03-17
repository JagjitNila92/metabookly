import type { Metadata } from 'next'
import { notFound } from 'next/navigation'
import Link from 'next/link'
import { ChevronLeft, Calendar, Hash, BookOpen, Globe, Tag, Ruler } from 'lucide-react'
import { getBook } from '@/lib/api'
import { BookCover } from '@/components/BookCover'
import { PricingPanel } from '@/components/PricingPanel'
import {
  PRODUCT_FORM,
  PUBLISHING_STATUS,
  formatRRP,
  formatDate,
  contributorsByRole,
} from '@/lib/utils'

interface Props {
  params: { isbn13: string }
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  try {
    const book = await getBook(params.isbn13)
    return { title: book.title }
  } catch {
    return { title: 'Book not found' }
  }
}

const SCHEME_LABELS: Record<string, string> = {
  '10': 'BISAC',
  '12': 'BIC',
  '93': 'Thema',
  '20': 'Keywords',
}

export default async function BookDetailPage({ params }: Props) {
  let book
  try {
    book = await getBook(params.isbn13)
  } catch {
    notFound()
  }

  const status = book.publishing_status ? PUBLISHING_STATUS[book.publishing_status] : null
  const form = PRODUCT_FORM[book.product_form] ?? book.product_form
  const rrpGbp = formatRRP(book.rrp_gbp, 'GBP')
  const rrpUsd = formatRRP(book.rrp_usd, 'USD')
  const pubDate = formatDate(book.publication_date)
  const roleGroups = contributorsByRole(book.contributors)

  const allSubjects = book.subjects.filter((s) => s.subject_heading)

  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-8">
      {/* Back */}
      <Link
        href="/catalog"
        className="inline-flex items-center gap-1 text-sm text-slate-500 hover:text-amber-600 mb-6 transition-colors"
      >
        <ChevronLeft size={16} /> Back to catalog
      </Link>

      <div className="flex flex-col md:flex-row gap-8">
        {/* Cover column */}
        <div className="shrink-0 w-40 md:w-52">
          <div className="relative w-full aspect-[2/3]">
            <BookCover
              url={book.cover_image_url}
              isbn13={book.isbn13}
              title={book.title}
              className="absolute inset-0 shadow-md"
              priority
            />
          </div>

          {/* RRP pricing card */}
          {(rrpGbp || rrpUsd) && (
            <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-3">
              <p className="text-xs font-semibold text-amber-700 mb-1 uppercase tracking-wide">
                Publisher RRP
              </p>
              {rrpGbp && (
                <p className="text-lg font-bold text-slate-900">{rrpGbp}</p>
              )}
              {rrpUsd && (
                <p className="text-sm text-slate-500">{rrpUsd}</p>
              )}
              <p className="text-[10px] text-slate-400 mt-1">
                Cover/list price only. Your trade price comes from your distributor account.
              </p>
            </div>
          )}

          {/* Trade pricing panel — auth-gated, client-side */}
          <PricingPanel isbn13={book.isbn13} rrpGbp={book.rrp_gbp} />

          {/* UK rights */}
          {book.uk_rights !== null && (
            <div className="mt-3 flex items-center gap-1.5 text-xs text-slate-500">
              <Globe size={13} />
              UK rights:{' '}
              <span className={book.uk_rights ? 'text-green-600 font-medium' : 'text-red-500 font-medium'}>
                {book.uk_rights ? 'Yes' : 'No'}
              </span>
            </div>
          )}
        </div>

        {/* Main content */}
        <div className="flex-1 min-w-0">
          {/* Status badge */}
          <div className="flex items-center gap-2 mb-2 flex-wrap">
            <span className="text-xs font-medium text-amber-600 uppercase tracking-wide">{form}</span>
            {status && (
              <span
                className={`text-xs px-2 py-0.5 rounded-full font-medium ${
                  status.color === 'green'
                    ? 'bg-green-100 text-green-700'
                    : status.color === 'amber'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-red-100 text-red-600'
                }`}
              >
                {status.label}
              </span>
            )}
            {book.uk_rights === false && (
              <span className="text-xs px-2 py-0.5 rounded-full bg-red-100 text-red-600 font-medium">
                No UK rights
              </span>
            )}
          </div>

          {/* Title */}
          <h1 className="text-2xl sm:text-3xl font-bold text-slate-900 leading-tight mb-1">
            {book.title}
          </h1>
          {book.subtitle && (
            <p className="text-lg text-slate-500 mb-3">{book.subtitle}</p>
          )}

          {/* Contributors */}
          {roleGroups.length > 0 && (
            <div className="flex flex-wrap gap-x-4 gap-y-1 mb-4">
              {roleGroups.map(({ label, names }) => (
                <p key={label} className="text-sm text-slate-600">
                  <span className="text-slate-400">{label}: </span>
                  {names.join(', ')}
                </p>
              ))}
            </div>
          )}

          {/* Publisher / imprint */}
          {book.publisher && (
            <p className="text-sm text-slate-500 mb-4">
              {book.publisher.name}
              {book.imprint && book.imprint !== book.publisher.name && (
                <> · {book.imprint}</>
              )}
            </p>
          )}

          {/* Key metadata row */}
          <div className="flex flex-wrap gap-4 text-sm text-slate-500 mb-6 border-t border-slate-100 pt-4">
            {pubDate && (
              <span className="flex items-center gap-1">
                <Calendar size={14} /> {pubDate}
              </span>
            )}
            {book.page_count && (
              <span className="flex items-center gap-1">
                <BookOpen size={14} /> {book.page_count} pages
              </span>
            )}
            <span className="flex items-center gap-1">
              <Hash size={14} /> {book.isbn13}
            </span>
            {book.language_code !== 'eng' && (
              <span className="flex items-center gap-1">
                <Globe size={14} /> {book.language_code.toUpperCase()}
              </span>
            )}
            {book.edition_statement && (
              <span>{book.edition_statement}</span>
            )}
            {book.height_mm && book.width_mm && (
              <span className="flex items-center gap-1">
                <Ruler size={14} /> {book.height_mm} × {book.width_mm} mm
              </span>
            )}
          </div>

          {/* Description */}
          {book.description && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-slate-700 mb-2">About this book</h2>
              <p className="text-sm text-slate-600 leading-relaxed whitespace-pre-line">
                {book.description}
              </p>
            </div>
          )}

          {/* TOC */}
          {book.toc && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-slate-700 mb-2">Contents</h2>
              <p className="text-sm text-slate-500 leading-relaxed whitespace-pre-line">{book.toc}</p>
            </div>
          )}

          {/* Excerpt */}
          {book.excerpt && (
            <div className="mb-6 bg-slate-50 border border-slate-200 rounded-lg p-4">
              <h2 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-2">Extract</h2>
              <p className="text-sm text-slate-600 italic leading-relaxed line-clamp-3">{book.excerpt}</p>
            </div>
          )}

          {/* Subjects */}
          {allSubjects.length > 0 && (
            <div className="mb-6">
              <h2 className="text-sm font-semibold text-slate-700 mb-2 flex items-center gap-1">
                <Tag size={14} /> Subject classification
              </h2>
              <div className="flex flex-wrap gap-2">
                {allSubjects.map((s) => (
                  <Link
                    key={`${s.scheme_id}-${s.subject_code}`}
                    href={`/catalog?subject_code=${s.subject_code}`}
                    className={`text-xs px-2.5 py-1 rounded-full border transition-colors ${
                      s.main_subject
                        ? 'bg-amber-100 border-amber-300 text-amber-800 font-medium'
                        : 'bg-slate-100 border-slate-200 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {s.subject_heading}
                    <span className="ml-1 text-slate-400">
                      ({SCHEME_LABELS[s.scheme_id] ?? s.scheme_id})
                    </span>
                  </Link>
                ))}
              </div>
            </div>
          )}

          {/* Contributor bios */}
          {book.contributors.filter((c) => c.bio).length > 0 && (
            <div className="border-t border-slate-100 pt-6">
              <h2 className="text-sm font-semibold text-slate-700 mb-3">About the author</h2>
              {book.contributors
                .filter((c) => c.bio)
                .map((c) => (
                  <div key={c.id} className="mb-3">
                    <p className="text-sm font-medium text-slate-800">{c.person_name}</p>
                    <p className="text-sm text-slate-500 leading-relaxed mt-0.5">{c.bio}</p>
                  </div>
                ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
