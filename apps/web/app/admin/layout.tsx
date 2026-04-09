import Link from 'next/link'
import { LayoutDashboard, Users, ToggleLeft } from 'lucide-react'

const NAV = [
  { href: '/admin/dashboard', label: 'Overview',       icon: LayoutDashboard },
  { href: '/admin/retailers', label: 'Retailers',       icon: Users           },
  { href: '/admin/flags',     label: 'Feature Flags',   icon: ToggleLeft      },
]

export default function AdminLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[calc(100vh-3.5rem)]">
      <aside className="w-52 shrink-0 border-r border-slate-200 bg-slate-50 px-3 py-6 hidden md:block">
        <p className="text-[10px] font-semibold text-slate-400 uppercase tracking-widest px-3 mb-3">
          Admin
        </p>
        <nav className="space-y-0.5">
          {NAV.map(({ href, label, icon: Icon }) => (
            <Link
              key={href}
              href={href}
              className="flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm text-slate-600
                         hover:bg-white hover:text-slate-900 hover:shadow-sm transition-all"
            >
              <Icon size={14} className="shrink-0 text-slate-400" />
              {label}
            </Link>
          ))}
        </nav>
      </aside>
      <div className="flex-1 min-w-0">{children}</div>
    </div>
  )
}
