'use client'

import { useEffect, useState } from 'react'

const STORAGE_KEY = 'mbk_view_count'
export const VIEW_THRESHOLD = 5

/**
 * Tracks how many book detail pages an anonymous user has visited.
 * Increments the counter on mount. Safe to call on every book detail page.
 */
export function useViewCount() {
  const [count, setCount] = useState(0)

  useEffect(() => {
    const stored = parseInt(localStorage.getItem(STORAGE_KEY) ?? '0', 10)
    const next = stored + 1
    localStorage.setItem(STORAGE_KEY, String(next))
    setCount(next)
  }, [])

  return { count, overThreshold: count > VIEW_THRESHOLD }
}
