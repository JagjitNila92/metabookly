import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function getToken() {
  const session = await getServerSession(authOptions)
  return session?.accessToken ?? null
}

export async function GET(_req: NextRequest, { params }: { params: { isbn13: string } }) {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const res = await fetch(`${API}/api/v1/portal/books/${params.isbn13}/assets`, {
    headers: { Authorization: `Bearer ${token}` },
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}

export async function POST(req: NextRequest, { params }: { params: { isbn13: string } }) {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const body = await req.json()
  const res = await fetch(`${API}/api/v1/portal/books/${params.isbn13}/assets`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
