import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import Link from 'next/link'
import { BookOpen } from 'lucide-react'
import './globals.css'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: { default: 'Metabookly', template: '%s | Metabookly' },
  description: 'AI-powered book discovery and pricing for independent retailers.',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className={inter.className}>
      <body>
        {/* Nav */}
        <header className="sticky top-0 z-50 bg-white border-b border-slate-200 shadow-sm">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 flex items-center h-14 gap-6">
            <Link href="/" className="flex items-center gap-2 font-semibold text-slate-900 shrink-0">
              <BookOpen className="text-amber-500" size={22} />
              <span>Metabookly</span>
            </Link>
            <nav className="flex items-center gap-4 text-sm text-slate-600">
              <Link href="/catalog" className="hover:text-amber-600 transition-colors">
                Catalog
              </Link>
            </nav>
            <div className="ml-auto flex items-center gap-3">
              <span className="text-xs bg-amber-100 text-amber-700 px-2 py-0.5 rounded-full font-medium">
                MVP Demo
              </span>
            </div>
          </div>
        </header>

        <main className="min-h-[calc(100vh-3.5rem)]">{children}</main>

        <footer className="border-t border-slate-200 bg-white mt-16">
          <div className="max-w-7xl mx-auto px-4 sm:px-6 py-6 flex items-center justify-between text-xs text-slate-400">
            <span>© {new Date().getFullYear()} Metabookly</span>
            <span>Book data sourced from ONIX 3.0 feeds</span>
          </div>
        </footer>
      </body>
    </html>
  )
}
