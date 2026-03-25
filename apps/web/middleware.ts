import { withAuth } from 'next-auth/middleware'
import { NextResponse } from 'next/server'

export default withAuth(
  function middleware(req) {
    const { pathname } = req.nextUrl
    const groups: string[] = (req.nextauth.token?.groups as string[]) ?? []

    const isAdmin = groups.includes('admins')
    const isRetailer = groups.includes('retailers') || isAdmin
    const isPublisher = groups.includes('publishers') || isAdmin

    // Retailer-only routes
    if (
      pathname.startsWith('/account') ||
      pathname.startsWith('/retailer/') ||
      pathname.startsWith('/basket') ||
      pathname.startsWith('/orders') ||
      pathname.startsWith('/settings')
    ) {
      if (!isRetailer) {
        return NextResponse.redirect(new URL('/', req.url))
      }
    }

    // Publisher/distributor portal routes
    if (pathname.startsWith('/portal')) {
      if (!isPublisher) {
        return NextResponse.redirect(new URL('/', req.url))
      }
    }

    // Distributor/admin-only routes
    if (pathname.startsWith('/distributor/')) {
      if (!isAdmin) {
        return NextResponse.redirect(new URL('/', req.url))
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
    '/account/:path*',
    '/retailer/:path*',
    '/basket/:path*',
    '/basket',
    '/orders/:path*',
    '/orders',
    '/settings/:path*',
    '/settings',
    '/portal/:path*',
    '/distributor/:path*',
  ],
}
