'use client'

import Link from 'next/link'
import { Lock } from 'lucide-react'

export function SoftWallPanel() {
  return (
    <div className="mt-4 rounded-lg border border-amber-200 bg-amber-50 p-4 text-center">
      <div className="flex justify-center mb-3">
        <div className="w-9 h-9 rounded-full bg-amber-100 flex items-center justify-center">
          <Lock size={16} className="text-amber-600" />
        </div>
      </div>

      <p className="text-sm font-semibold text-slate-800 mb-1">
        See live trade prices
      </p>
      <p className="text-xs text-slate-500 mb-4 leading-relaxed">
        Sign up free to view trade pricing from Gardners, Bertrams and more — directly in the catalogue.
      </p>

      <Link
        href="/register"
        className="block w-full text-center text-sm font-medium bg-amber-500 hover:bg-amber-600 text-white py-2 px-4 rounded-md transition-colors mb-2"
      >
        Create retailer account
      </Link>
      <Link
        href="/login"
        className="block text-xs text-slate-500 hover:text-amber-600 transition-colors"
      >
        Already have an account? Sign in
      </Link>
    </div>
  )
}
