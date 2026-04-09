import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

/** GET /api/admin/flags/global — list all global flags */
export async function GET() {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const res = await fetch(`${API}/api/v1/admin/flags/global`, {
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: 'no-store',
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}

/** PATCH /api/admin/flags/global  body: { flag_name, enabled } */
export async function PATCH(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { flag_name, enabled } = await req.json()
  if (!flag_name || typeof enabled !== 'boolean') {
    return NextResponse.json({ error: 'flag_name and enabled required' }, { status: 400 })
  }

  const res = await fetch(`${API}/api/v1/admin/flags/global/${flag_name}`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ enabled }),
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
