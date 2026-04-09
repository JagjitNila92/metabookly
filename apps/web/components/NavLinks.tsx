'use client'

import Link from 'next/link'
import { useSession } from 'next-auth/react'
import { useEffect, useState, useCallback } from 'react'
import { usePathname } from 'next/navigation'
import { ShoppingCart, ArrowLeftRight } from 'lucide-react'
import { getBasket } from '@/lib/api'
import FeatureGate from '@/components/FeatureGate'

// ── Basket badge ──────────────────────────────────────────────────────────────

function BasketBadge() {
  const [count, setCount] = useState<number | null>(null)

  const refresh = useCallback(() => {
    getBasket()
      .then(b => setCount(b.items.length))
      .catch(() => setCount(null))
  }, [])

  useEffect(() => {
    refresh()
    window.addEventListener('basketUpdated', refresh)
    return () => window.removeEventListener('basketUpdated', refresh)
  }, [refresh])

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

// ── Nav link helper ───────────────────────────────────────────────────────────

function NavLink({ href, children }: { href: string; children: React.ReactNode }) {
  const path = usePathname()
  const active = path === href || (href !== '/' && path.startsWith(href))
  return (
    <Link
      href={href}
      className={`transition-colors ${active ? 'text-amber-600 font-medium' : 'hover:text-amber-600'}`}
    >
      {children}
    </Link>
  )
}

// ── Admin switcher ────────────────────────────────────────────────────────────

type PortalView = 'retailer' | 'publisher' | 'distributor' | 'admin'

function AdminSwitcher({ view, onChange }: { view: PortalView; onChange: (v: PortalView) => void }) {
  const tabs: { value: PortalView; label: string }[] = [
    { value: 'retailer',    label: 'Retailer' },
    { value: 'publisher',   label: 'Publisher' },
    { value: 'distributor', label: 'Distributor' },
    { value: 'admin',       label: 'Admin' },
  ]
  return (
    <div className="flex items-center gap-1 bg-slate-100 rounded-full px-1 py-0.5 text-xs">
      <ArrowLeftRight size={11} className="text-slate-400 mx-1" />
      {tabs.map(t => (
        <button
          key={t.value}
          onClick={() => onChange(t.value)}
          className={`px-2.5 py-0.5 rounded-full transition-colors ${
            view === t.value ? 'bg-white shadow-sm text-slate-800 font-medium' : 'text-slate-500 hover:text-slate-700'
          }`}
        >
          {t.label}
        </button>
      ))}
    </div>
  )
}

// ── Main nav ──────────────────────────────────────────────────────────────────

export function NavLinks() {
  const { data: session } = useSession()
  const pathname = usePathname()

  const groups: string[] = (session as { groups?: string[] } | null)?.groups ?? []
  const isAdmin     = groups.includes('admins')
  const isRetailer  = groups.includes('retailers') || isAdmin
  const isPublisher = groups.includes('publishers') || isAdmin

  // Admin starts on whichever portal their current path suggests
  const inferView = (): PortalView => {
    if (pathname.startsWith('/admin')) return 'admin'
    if (pathname.startsWith('/publisher') || pathname.startsWith('/portal')) return 'publisher'
    if (pathname.startsWith('/distributor')) return 'distributor'
    return 'retailer'
  }
  const [adminView, setAdminView] = useState<PortalView>(inferView)

  // When admin switches view, navigate to the right dashboard
  const handleSwitch = (v: PortalView) => {
    setAdminView(v)
    if (v === 'retailer') window.location.href = '/dashboard'
    else if (v === 'publisher') window.location.href = '/publisher/dashboard'
    else if (v === 'distributor') window.location.href = '/distributor/orders'
    else window.location.href = '/admin/dashboard'
  }

  // Determine which nav to show
  const showRetailerNav    = isRetailer && (!isAdmin || adminView === 'retailer')
  const showPublisherNav   = isPublisher && (!isAdmin || adminView === 'publisher')
  const showDistributorNav = isAdmin && adminView === 'distributor'
  const showAdminNav       = isAdmin && adminView === 'admin'

  return (
    <nav className="flex items-center gap-4 text-sm text-slate-600">
      {/* Catalog is always visible */}
      <NavLink href="/catalog">Catalogue</NavLink>

      {/* Retailer nav */}
      {showRetailerNav && (
        <>
          <NavLink href="/dashboard">Dashboard</NavLink>
          {/* Ordering links hidden until ordering_enabled flag is true */}
          <FeatureGate flag="ordering_enabled">
            <NavLink href="/orders">Orders</NavLink>
            <NavLink href="/order/bulk">Quick order</NavLink>
            <NavLink href="/order/lists">Lists</NavLink>
            <BasketBadge />
          </FeatureGate>
          <NavLink href="/settings">Settings</NavLink>
          <NavLink href="/account">My Account</NavLink>
        </>
      )}

      {/* Publisher nav */}
      {showPublisherNav && (
        <>
          <NavLink href="/publisher/dashboard">Dashboard</NavLink>
          <NavLink href="/portal/feeds">Feed History</NavLink>
          <NavLink href="/portal/conflicts">Conflicts</NavLink>
          <NavLink href="/portal/suggestions">AI Review</NavLink>
        </>
      )}

      {/* Distributor nav (admin only, distributor view) */}
      {showDistributorNav && (
        <>
          <NavLink href="/distributor/dashboard">Dashboard</NavLink>
          <NavLink href="/distributor/orders">Orders</NavLink>
          <NavLink href="/distributor/requests">Requests</NavLink>
        </>
      )}

      {/* Admin nav */}
      {showAdminNav && (
        <>
          <NavLink href="/admin/dashboard">Overview</NavLink>
          <NavLink href="/admin/retailers">Retailers</NavLink>
          <NavLink href="/admin/publishers">Publishers</NavLink>
          <NavLink href="/admin/flags">Flags</NavLink>
        </>
      )}

      {/* Admin switcher */}
      {isAdmin && (
        <AdminSwitcher view={adminView} onChange={handleSwitch} />
      )}
    </nav>
  )
}
