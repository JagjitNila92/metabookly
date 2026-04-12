import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function DELETE(
  _req: Request,
  { params }: { params: { keyPrefix: string } },
) {
  const session = await getServerSession(authOptions)
  if (!session?.accessToken) return NextResponse.json({ error: 'Unauthorized' }, { status: 401 })

  const res = await fetch(`${API}/api/v1/portal/api-keys/${params.keyPrefix}`, {
    method: 'DELETE',
    headers: { Authorization: `Bearer ${session.accessToken}` },
  })

  if (res.status === 204) return new NextResponse(null, { status: 204 })

  const text = await res.text()
  try {
    return NextResponse.json(JSON.parse(text), { status: res.status })
  } catch {
    return NextResponse.json({ error: text || 'Error' }, { status: res.status || 500 })
  }
}
