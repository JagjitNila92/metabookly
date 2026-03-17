'use client'

import Image from 'next/image'
import { useState } from 'react'
import { BookOpen } from 'lucide-react'
import { cn } from '@/lib/utils'

interface BookCoverProps {
  url: string | null
  isbn13: string
  title: string
  className?: string
  priority?: boolean
}

/**
 * Renders a book cover image with a two-stage fallback:
 *   1. ONIX cover URL (from publisher/distributor feed)
 *   2. Open Library Covers API (free, based on ISBN-13)
 *   3. Illustrated placeholder (amber gradient + book icon)
 */
export function BookCover({ url, isbn13, title, className, priority = false }: BookCoverProps) {
  const olUrl = `https://covers.openlibrary.org/b/isbn/${isbn13}-M.jpg`
  // stage 0 = try primary url, stage 1 = try OL, stage 2 = placeholder
  const [stage, setStage] = useState(url ? 0 : 1)

  const src = stage === 0 ? url! : olUrl

  if (stage < 2) {
    return (
      <div className={cn('relative overflow-hidden rounded', className)}>
        <Image
          src={src}
          alt={`Cover of ${title}`}
          fill
          className="object-cover"
          sizes="(max-width: 768px) 120px, 200px"
          priority={priority}
          onError={() => setStage((s) => s + 1)}
        />
      </div>
    )
  }

  // Illustrated placeholder — warm gradient with book icon
  return (
    <div
      className={cn(
        'flex flex-col items-center justify-center rounded bg-gradient-to-br from-amber-50 to-amber-100 border border-amber-200',
        className,
      )}
    >
      <BookOpen className="text-amber-400 mb-1" strokeWidth={1.5} size={28} />
      <span className="text-[10px] text-amber-500 text-center px-2 leading-tight line-clamp-2">
        {title}
      </span>
    </div>
  )
}
