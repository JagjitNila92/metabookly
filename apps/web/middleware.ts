import { withAuth } from 'next-auth/middleware'
import { NextResponse } from 'next/server'

export default withAuth(
  function middleware(req) {
    const { pathname } = req.nextUrl
    const groups: string[] = (req.nextauth.token?.groups as string[]) ?? []

    const isAdmin = groups.includes('admins')
    const isRetailer = groups.includes('retailers') || isAdmin
    const isPublisher = groups.includes('publishers') || isAdmin

    // Retailer dashboard + retailer-only routes
    if (
      pathname.startsWith('/dashboard') ||
      pathname.startsWith('/account') ||
      pathname.startsWith('/retailer/') ||
      pathname.startsWith('/basket') ||
      pathname.startsWith('/orders') ||
      pathname.startsWith('/settings')
    ) {
      if (!isRetailer) {
        return NextResponse.redirect(new URL('/login', req.url))
      }
    }

    // Publisher portal routes
    if (pathname.startsWith('/publisher') || pathname.startsWith('/portal')) {
      if (!isPublisher) {
        return NextResponse.redirect(new URL('/login', req.url))
      }
    }

    // Distributor/admin-only routes
    if (pathname.startsWith('/distributor/')) {
      if (!isAdmin) {
        return NextResponse.redirect(new URL('/login', req.url))
      }
    }

    return NextResponse.next()
  },
  {
    callbacks: {
      // Run the middleware function for all matched routes
      // (withAuth itself handles the unauthenticated → /login redirect)
      authorized: ({ token }) => !!token,
    },
  },
)

export const config = {
  matcher: [
    '/dashboard/:path*',
    '/dashboard',
    '/account/:path*',
    '/retailer/:path*',
    '/basket/:path*',
    '/basket',
    '/orders/:path*',
    '/orders',
    '/settings/:path*',
    '/settings',
    '/publisher/:path*',
    '/portal/:path*',
    '/distributor/:path*',
    '/auth/redirect',
  ],
}
