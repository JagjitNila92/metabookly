import { getServerSession } from 'next-auth'
import { NextRequest, NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function POST(
  req: NextRequest,
  { params }: { params: { isbn13: string } },
) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  // Forward the multipart form data as-is to the FastAPI backend
  const formData = await req.formData()
  const res = await fetch(`${API}/api/v1/portal/books/${params.isbn13}/cover`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${session.accessToken}` },
    body: formData,
  })
  const text = await res.text()
  try {
    return NextResponse.json(JSON.parse(text), { status: res.status })
  } catch {
    return NextResponse.json({ error: text || 'Empty response' }, { status: res.status || 500 })
  }
}

export async function DELETE(
  _req: NextRequest,
  { params }: { params: { isbn13: string } },
) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const res = await fetch(`${API}/api/v1/portal/books/${params.isbn13}/cover`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${session.accessToken}` },
  })
  if (res.status === 204) return new NextResponse(null, { status: 204 })
  const text = await res.text()
  try {
    return NextResponse.json(JSON.parse(text), { status: res.status })
  } catch {
    return NextResponse.json({ error: text || 'Empty response' }, { status: res.status || 500 })
  }
}
