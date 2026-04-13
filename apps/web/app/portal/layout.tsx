import Link from 'next/link'
import { Upload, FileText, AlertTriangle, Sparkles, LayoutDashboard, Settings, BarChart2, BookOpen, FolderOpen } from 'lucide-react'

const NAV = [
  { href: '/portal', label: 'Dashboard', icon: LayoutDashboard, exact: true },
  { href: '/portal/upload', label: 'Upload Feed', icon: Upload },
  { href: '/portal/feeds', label: 'Feed History', icon: FileText },
  { href: '/portal/quality', label: 'Quality', icon: BarChart2 },
  { href: '/portal/arcs', label: 'ARC Requests', icon: BookOpen },
  { href: '/portal/assets', label: 'Marketing Assets', icon: FolderOpen },
  { href: '/portal/conflicts', label: 'Conflicts', icon: AlertTriangle },
  { href: '/portal/suggestions', label: 'AI Review', icon: Sparkles },
  { href: '/portal/settings', label: 'Settings', icon: Settings },
]

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="flex min-h-[calc(100vh-3.5rem)]">
      {/* Sidebar */}
      <aside className="w-56 shrink-0 bg-slate-900 text-slate-300 flex flex-col py-6 px-3 gap-1">
        <p className="text-xs font-semibold text-slate-500 uppercase tracking-wider px-3 mb-2">
          Supplier Portal
        </p>
        {NAV.map(({ href, label, icon: Icon }) => (
          <Link
            key={href}
            href={href}
            className="flex items-center gap-2.5 px-3 py-2 rounded-md text-sm hover:bg-slate-800 hover:text-white transition-colors"
          >
            <Icon size={15} />
            {label}
          </Link>
        ))}
      </aside>

      {/* Content */}
      <div className="flex-1 overflow-auto bg-slate-50">
        <div className="max-w-5xl mx-auto px-6 py-8">{children}</div>
      </div>
    </div>
  )
}
