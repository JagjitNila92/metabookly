import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function POST(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { searchParams } = new URL(req.url)
  const filename = searchParams.get('filename') ?? 'feed.xml'
  const sequenceNumber = searchParams.get('sequence_number')

  const qs = new URLSearchParams({ filename })
  if (sequenceNumber) qs.set('sequence_number', sequenceNumber)

  const res = await fetch(`${API}/api/v1/portal/upload-url?${qs}`, {
    method: 'POST',
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: 'no-store',
  })

  const body = await res.json()
  return NextResponse.json(body, { status: res.status })
}
