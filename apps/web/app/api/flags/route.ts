/**
 * GET /api/flags?flags=ordering_enabled,publisher_analytics
 *
 * Batch-resolve feature flags for the current session.
 * Returns { flag_name: boolean } — unauthenticated callers get global-only resolution.
 *
 * The frontend uses this to conditionally show/hide UI at the session level.
 * Per-account overrides are resolved server-side (FastAPI) via the same FeatureFlagService.
 */
import { getServerSession } from 'next-auth'
import { NextResponse } from 'next/server'
import { authOptions } from '@/lib/auth'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

export async function GET(req: Request) {
  const { searchParams } = new URL(req.url)
  const flagsParam = searchParams.get('flags')
  if (!flagsParam) {
    return NextResponse.json({ error: 'flags query param required' }, { status: 400 })
  }

  const session = await getServerSession(authOptions)
  const headers: HeadersInit = { 'Content-Type': 'application/json' }
  if (session?.accessToken) {
    headers['Authorization'] = `Bearer ${session.accessToken}`
  }

  const flagNames = flagsParam.split(',').map(f => f.trim()).filter(Boolean)

  // Resolve each flag in parallel via the FastAPI admin/global endpoint
  // (public read endpoint — auth optional, returns global value for anonymous callers)
  const res = await fetch(`${API}/api/v1/admin/flags/public`, {
    headers,
    cache: 'no-store',
  })

  if (!res.ok) {
    // On error, default everything to false (safe)
    return NextResponse.json(Object.fromEntries(flagNames.map(f => [f, false])))
  }

  const all: Array<{ flag_name: string; enabled: boolean }> = await res.json()
  const map = Object.fromEntries(all.map(f => [f.flag_name, f.enabled]))

  // Return only the requested flags; missing flags default to false
  const result = Object.fromEntries(flagNames.map(f => [f, map[f] ?? false]))
  return NextResponse.json(result)
}
