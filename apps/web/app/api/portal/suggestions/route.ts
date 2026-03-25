import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { searchParams } = new URL(req.url)
  const qs = new URLSearchParams()
  if (searchParams.get('confidence')) qs.set('confidence', searchParams.get('confidence')!)
  if (searchParams.get('limit')) qs.set('limit', searchParams.get('limit')!)
  if (searchParams.get('offset')) qs.set('offset', searchParams.get('offset')!)

  const res = await fetch(`${API}/api/v1/portal/suggestions?${qs}`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: 'no-store',
  })

  return NextResponse.json(await res.json(), { status: res.status })
}
