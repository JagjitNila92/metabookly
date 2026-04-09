import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const days = searchParams.get('days') ?? '30'
  const res = await fetch(`${API}/api/v1/analytics/publisher/me?days=${days}`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: 'no-store',
  })
  const text = await res.text()
  try {
    return NextResponse.json(JSON.parse(text), { status: res.status })
  } catch {
    return NextResponse.json({ error: text || 'Empty response from API' }, { status: res.status || 500 })
  }
}
