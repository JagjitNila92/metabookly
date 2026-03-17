import Link from 'next/link'
import { ArrowRight, Search, Zap, Globe } from 'lucide-react'

export default function HomePage() {
  return (
    <div className="max-w-5xl mx-auto px-4 sm:px-6 py-20 text-center">
      {/* Hero */}
      <span className="inline-block text-xs font-semibold bg-amber-100 text-amber-700 px-3 py-1 rounded-full mb-6 uppercase tracking-wide">
        MVP Demo
      </span>
      <h1 className="text-4xl sm:text-5xl font-bold text-slate-900 mb-4 text-balance">
        The smarter book catalog for{' '}
        <span className="text-amber-600">independent retailers</span>
      </h1>
      <p className="text-lg text-slate-500 mb-10 max-w-2xl mx-auto text-balance">
        Search the full catalog, see your personal pricing from Gardners and Bertrams in
        real-time, and discover titles your customers will love — powered by AI.
      </p>

      <div className="flex flex-col sm:flex-row gap-3 justify-center mb-20">
        <Link
          href="/catalog"
          className="inline-flex items-center gap-2 bg-amber-500 hover:bg-amber-600 text-white font-semibold px-6 py-3 rounded-lg transition-colors"
        >
          Browse the catalog <ArrowRight size={18} />
        </Link>
        <Link
          href="/catalog?q=fiction"
          className="inline-flex items-center gap-2 border border-slate-300 hover:border-slate-400 text-slate-700 font-medium px-6 py-3 rounded-lg transition-colors"
        >
          Try a search
        </Link>
      </div>

      {/* Feature grid */}
      <div className="grid sm:grid-cols-3 gap-6 text-left">
        {[
          {
            icon: Search,
            title: 'Full-text catalog search',
            body: 'Search by title, author, description or subject code across the entire catalog.',
          },
          {
            icon: Zap,
            title: 'Live pricing per retailer',
            body: 'Your personal price from Gardners, Bertrams and Ingram — fetched live from each distributor.',
          },
          {
            icon: Globe,
            title: 'ONIX-native',
            body: 'Ingests standard ONIX 3.0 feeds from any publisher or distributor automatically.',
          },
        ].map(({ icon: Icon, title, body }) => (
          <div key={title} className="bg-white rounded-xl border border-slate-200 p-5">
            <div className="w-9 h-9 rounded-lg bg-amber-100 flex items-center justify-center mb-3">
              <Icon size={18} className="text-amber-600" />
            </div>
            <h3 className="font-semibold text-slate-900 mb-1">{title}</h3>
            <p className="text-sm text-slate-500">{body}</p>
          </div>
        ))}
      </div>
    </div>
  )
}
