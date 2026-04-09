/**
 * PATCH /api/admin/retailers/plan
 * Body: { retailer_id, plan, extra_seats? }
 * Proxies to FastAPI PATCH /admin/retailers/{id}/plan
 */
import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function PATCH(req: Request) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) {
    return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })
  }

  const { retailer_id, plan, extra_seats = 0 } = await req.json()
  if (!retailer_id || !plan) {
    return NextResponse.json({ error: 'retailer_id and plan required' }, { status: 400 })
  }

  const res = await fetch(`${API}/api/v1/admin/retailers/${retailer_id}/plan`, {
    method: 'PATCH',
    headers: {
      Authorization: `Bearer ${session.accessToken}`,
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({ plan, extra_seats }),
  })

  const data = await res.json()
  return NextResponse.json(data, { status: res.status })
}
