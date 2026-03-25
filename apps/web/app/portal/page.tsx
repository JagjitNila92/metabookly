import Link from 'next/link'
import { Upload, FileText, AlertTriangle, Sparkles, ArrowRight } from 'lucide-react'

export default function PortalDashboard() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-slate-900 mb-1">Supplier Portal</h1>
      <p className="text-slate-500 mb-8">
        Submit ONIX feeds, review metadata conflicts, and manage AI-enhanced descriptions.
      </p>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        <DashCard
          href="/portal/upload"
          icon={Upload}
          title="Upload ONIX Feed"
          description="Submit a new catalog file or delta update. Supports ONIX 2.1 and 3.0."
          accent="amber"
        />
        <DashCard
          href="/portal/feeds"
          icon={FileText}
          title="Feed History"
          description="View the status of all your submitted feeds, including records ingested and any errors."
          accent="blue"
        />
        <DashCard
          href="/portal/conflicts"
          icon={AlertTriangle}
          title="Metadata Conflicts"
          description="Review fields where your latest feed differs from editorially-modified values."
          accent="red"
        />
        <DashCard
          href="/portal/suggestions"
          icon={Sparkles}
          title="AI Suggestions"
          description="Accept or reject AI-generated metadata improvements for your titles."
          accent="purple"
        />
      </div>
    </div>
  )
}

function DashCard({
  href,
  icon: Icon,
  title,
  description,
  accent,
}: {
  href: string
  icon: React.ElementType
  title: string
  description: string
  accent: 'amber' | 'blue' | 'red' | 'purple'
}) {
  const colors = {
    amber: 'bg-amber-50 text-amber-600 border-amber-200',
    blue: 'bg-blue-50 text-blue-600 border-blue-200',
    red: 'bg-red-50 text-red-600 border-red-200',
    purple: 'bg-purple-50 text-purple-600 border-purple-200',
  }
  return (
    <Link
      href={href}
      className="bg-white border border-slate-200 rounded-xl p-5 hover:shadow-md hover:border-slate-300 transition-all group"
    >
      <div className={`inline-flex p-2 rounded-lg border ${colors[accent]} mb-3`}>
        <Icon size={18} />
      </div>
      <h2 className="font-semibold text-slate-900 mb-1">{title}</h2>
      <p className="text-sm text-slate-500 leading-relaxed mb-3">{description}</p>
      <span className="flex items-center gap-1 text-sm font-medium text-slate-700 group-hover:text-amber-600 transition-colors">
        Open <ArrowRight size={14} />
      </span>
    </Link>
  )
}
