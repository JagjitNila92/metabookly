'use client'

import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { useEffect, useState } from 'react'
import { ShoppingCart } from 'lucide-react'
import { getBasket } from '@/lib/api'

function BasketBadge() {
  const [count, setCount] = useState<number | null>(null)

  useEffect(() => {
    function refresh() {
      getBasket()
        .then(b => setCount(b.items.length))
        .catch(() => setCount(null))
    }
    refresh()
    window.addEventListener('basketUpdated', refresh)
    return () => window.removeEventListener('basketUpdated', refresh)
  }, [])

  return (
    <Link href="/basket" className="relative inline-flex items-center gap-1 hover:text-amber-600 transition-colors">
      <ShoppingCart size={16} />
      <span>Basket</span>
      {count != null && count > 0 && (
        <span className="absolute -top-1.5 -right-2.5 bg-amber-500 text-white text-[10px] font-bold rounded-full w-4 h-4 flex items-center justify-center leading-none">
          {count > 9 ? '9+' : count}
        </span>
      )}
    </Link>
  )
}

export function NavLinks() {
  const { data: session } = useSession()

  const groups: string[] = (session as any)?.groups ?? []
  const isAdmin = groups.includes('admins')
  const isRetailer = groups.includes('retailers') || isAdmin
  const isPublisher = groups.includes('publishers') || isAdmin

  return (
    <nav className="flex items-center gap-4 text-sm text-slate-600">
      <Link href="/catalog" className="hover:text-amber-600 transition-colors">
        Catalog
      </Link>

      {isPublisher && (
        <Link href="/portal" className="hover:text-amber-600 transition-colors">
          Supplier Portal
        </Link>
      )}

      {isRetailer && (
        <>
          <Link href="/orders" className="hover:text-amber-600 transition-colors">
            Orders
          </Link>
          <BasketBadge />
          <Link href="/settings" className="hover:text-amber-600 transition-colors">
            Settings
          </Link>
          <Link href="/account" className="hover:text-amber-600 transition-colors">
            My Account
          </Link>
          <Link href="/retailer/dashboard" className="hover:text-amber-600 transition-colors">
            My Activity
          </Link>
        </>
      )}

      {isAdmin && (
        <>
          <Link href="/distributor/dashboard" className="hover:text-amber-600 transition-colors">
            Distributor
          </Link>
          <Link href="/distributor/requests" className="hover:text-amber-600 transition-colors">
            Requests
          </Link>
        </>
      )}
    </nav>
  )
}
