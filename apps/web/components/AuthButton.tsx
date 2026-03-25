'use client'

import { useSession, signIn, signOut } from 'next-auth/react'
import { LogIn, LogOut, User } from 'lucide-react'
import Link from 'next/link'

export function AuthButton() {
  const { data: session, status } = useSession()

  if (status === 'loading') return null

  if (session) {
    return (
      <div className="flex items-center gap-3">
        <span className="hidden sm:flex items-center gap-1.5 text-xs text-slate-500">
          <User size={13} />
          {session.user?.email}
        </span>
        <button
          onClick={() => signOut({ callbackUrl: '/' })}
          className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-red-500 transition-colors"
        >
          <LogOut size={14} /> Sign out
        </button>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2">
      <Link
        href="/register"
        className="text-sm font-medium text-amber-600 border border-amber-300 hover:border-amber-500 hover:bg-amber-50 px-3 py-1.5 rounded-md transition-colors"
      >
        Register
      </Link>
      <button
        onClick={() => signIn()}
        className="flex items-center gap-1.5 text-sm font-medium text-white bg-amber-500 hover:bg-amber-600 px-3 py-1.5 rounded-md transition-colors"
      >
        <LogIn size={14} /> Sign in
      </button>
    </div>
  )
}
