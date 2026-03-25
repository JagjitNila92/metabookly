import { NextResponse } from 'next/server'

export const dynamic = 'force-dynamic'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET() {
  const res = await fetch(`${API}/api/v1/catalog/facets`, {
    next: { revalidate: 300 },
  })
  return NextResponse.json(await res.json(), { status: res.status })
}
