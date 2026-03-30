import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const url = new URL(`${API}/api/v1/distributor/orders`)
  for (const [k, v] of searchParams.entries()) url.searchParams.set(k, v)

  const res = await fetch(url.toString(), {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: 'no-store',
  })
  return NextResponse.json(await res.json(), { status: res.status })
}
