import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function POST(
  _req: Request,
  { params }: { params: { suggestionId: string; action: string } },
) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  if (!['accept', 'reject'].includes(params.action)) {
    return NextResponse.json({ error: 'Invalid action' }, { status: 400 })
  }

  const res = await fetch(
    `${API}/api/v1/portal/suggestions/${params.suggestionId}/${params.action}`,
    {
      method: 'POST',
      headers: { Authorization: `Bearer ${session.accessToken}` },
      cache: 'no-store',
    },
  )

  return NextResponse.json(await res.json(), { status: res.status })
}
