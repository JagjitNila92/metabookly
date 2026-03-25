import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function DELETE(
  _req: Request,
  { params }: { params: { id: string; lineId: string } },
) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const res = await fetch(`${API}/api/v1/orders/${params.id}/lines/${params.lineId}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${session.accessToken}` },
    cache: 'no-store',
  })
  return new NextResponse(null, { status: res.status })
}
