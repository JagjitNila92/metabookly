'use client'

import { useState } from 'react'
import { useSession } from 'next-auth/react'
import { ShoppingCart, Check, AlertCircle } from 'lucide-react'
import Link from 'next/link'
import { addToBasket } from '@/lib/api'

interface AddToBasketProps {
  isbn13: string
}

export function AddToBasket({ isbn13 }: AddToBasketProps) {
  const { data: session, status } = useSession()
  const [loading, setLoading] = useState(false)
  const [added, setAdded] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const groups: string[] = (session as any)?.groups ?? []
  const isRetailer = groups.includes('retailers') || groups.includes('admins')

  if (status === 'loading') return null
  if (!session || !isRetailer) return null

  async function handleAdd() {
    setLoading(true)
    setError(null)
    try {
      await addToBasket(isbn13, 1)
      setAdded(true)
      window.dispatchEvent(new Event('basketUpdated'))
    } catch (e: any) {
      setError(e.message ?? 'Failed to add to basket')
    } finally {
      setLoading(false)
    }
  }

  if (added) {
    return (
      <div className="mt-4 flex flex-col gap-2">
        <div className="flex items-center gap-1.5 text-sm text-green-700 font-medium">
          <Check size={16} /> Added to basket
        </div>
        <div className="flex gap-2">
          <Link
            href="/basket"
            className="flex-1 text-center text-sm font-medium bg-amber-500 hover:bg-amber-600 text-white px-4 py-2 rounded-lg transition-colors"
          >
            View basket
          </Link>
          <button
            onClick={() => setAdded(false)}
            className="text-sm text-slate-500 hover:text-slate-700 px-3 py-2 rounded-lg border border-slate-200 transition-colors"
          >
            Add more
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="mt-4">
      <button
        onClick={handleAdd}
        disabled={loading}
        className="w-full flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white font-semibold text-sm px-4 py-2.5 rounded-lg transition-colors"
      >
        <ShoppingCart size={16} />
        {loading ? 'Adding…' : 'Add to basket'}
      </button>
      {error && (
        <p className="mt-1.5 flex items-center gap-1 text-xs text-red-500">
          <AlertCircle size={12} /> {error}
        </p>
      )}
    </div>
  )
}
