import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

async function getToken() {
  const session = await getServerSession(authOptions)
  return session?.accessToken ?? null
}

export async function PATCH(req: NextRequest, { params }: { params: { isbn13: string; assetId: string } }) {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const body = await req.json()
  const res = await fetch(`${API}/api/v1/portal/books/${params.isbn13}/assets/${params.assetId}`, {
    method: 'PATCH',
    headers: { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })
  return new NextResponse(null, { status: res.status })
}

export async function DELETE(_req: NextRequest, { params }: { params: { isbn13: string; assetId: string } }) {
  const token = await getToken()
  if (!token) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  const res = await fetch(`${API}/api/v1/portal/books/${params.isbn13}/assets/${params.assetId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${token}` },
  })
  return new NextResponse(null, { status: res.status })
}
