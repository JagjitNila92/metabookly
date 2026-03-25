import { getServerSession } from 'next-auth'
import { redirect } from 'next/navigation'
import { authOptions } from '@/lib/auth'

/**
 * Smart post-login redirect. Reads the user's Cognito groups from the session
 * and sends them to the right dashboard.
 *
 *   retailers   → /dashboard
 *   publishers  → /publisher/dashboard
 *   admins      → /dashboard  (with switcher in nav)
 *   unknown     → /catalog
 */
export default async function AuthRedirectPage() {
  const session = await getServerSession(authOptions)

  if (!session) {
    redirect('/login')
  }

  const groups: string[] = (session as { groups?: string[] }).groups ?? []
  const isAdmin     = groups.includes('admins')
  const isRetailer  = groups.includes('retailers')
  const isPublisher = groups.includes('publishers')

  if (isAdmin || isRetailer) {
    redirect('/dashboard')
  }

  if (isPublisher) {
    redirect('/publisher/dashboard')
  }

  // Fallback — unknown group
  redirect('/catalog')
}
