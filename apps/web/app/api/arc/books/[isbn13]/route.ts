import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function POST(req: NextRequest, { params }: { params: { isbn13: string } }) {
  const session = await getServerSession(authOptions)
  const body = await req.json()

  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (session?.accessToken) headers['Authorization'] = `Bearer ${session.accessToken}`

  const res = await fetch(`${API}/api/v1/arc/books/${params.isbn13}/request`, {
    method: 'POST',
    headers,
    body: JSON.stringify(body),
  })
  const data = res.status === 201 ? await res.json() : null
  return NextResponse.json(data ?? {}, { status: res.status })
}

export async function GET(req: NextRequest, { params }: { params: { isbn13: string } }) {
  const { searchParams } = new URL(req.url)
  const email = searchParams.get('email')
  if (!email) return NextResponse.json({ has_request: false, status: null, decline_reason: null, download_url: null })

  const res = await fetch(
    `${API}/api/v1/arc/books/${params.isbn13}/status?email=${encodeURIComponent(email)}`,
  )
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
