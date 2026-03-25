import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function POST(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const res = await fetch(`${API}/api/v1/basket/items`, {
    method: 'POST',
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(await req.json()),
    cache: 'no-store',
  })
  const body = await res.text()
  try {
    return NextResponse.json(JSON.parse(body), { status: res.status })
  } catch {
    return NextResponse.json({ error: body || 'Unexpected error' }, { status: res.status })
  }
}
