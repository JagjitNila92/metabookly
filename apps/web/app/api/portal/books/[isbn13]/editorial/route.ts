import { getServerSession } from 'next-auth'
import { NextRequest, NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET(
  _req: NextRequest,
  { params }: { params: { isbn13: string } },
) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const res = await fetch(`${API}/api/v1/portal/books/${params.isbn13}/editorial`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: 'no-store',
  })
  const text = await res.text()
  try {
    return NextResponse.json(JSON.parse(text), { status: res.status })
  } catch {
    return NextResponse.json({ error: text || 'Empty response' }, { status: res.status || 500 })
  }
}

export async function PUT(
  req: NextRequest,
  { params }: { params: { isbn13: string } },
) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const body = await req.json()
  const res = await fetch(`${API}/api/v1/portal/books/${params.isbn13}/editorial`, {
    method: 'PUT',
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
    cache: 'no-store',
  })
  const text = await res.text()
  try {
    return NextResponse.json(JSON.parse(text), { status: res.status })
  } catch {
    return NextResponse.json({ error: text || 'Empty response' }, { status: res.status || 500 })
  }
}
