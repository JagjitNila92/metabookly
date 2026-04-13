import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export async function GET(req: NextRequest, { params }: { params: { isbn13: string } }) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const { searchParams } = new URL(req.url)
  const qs = searchParams.toString()
  const res = await fetch(
    `${API}/api/v1/portal/books/${params.isbn13}/assets/upload-url?${qs}`,
    { headers: { Authorization: `Bearer ${session.accessToken}` } },
  )
  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
