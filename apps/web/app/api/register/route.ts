import { NextRequest, NextResponse } from 'next/server'

const API = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const HUBSPOT_TOKEN = process.env.HUBSPOT_TOKEN

export async function POST(req: NextRequest) {
  const body = await req.json()

  // 1. Create user via FastAPI (Cognito + DB + welcome email)
  const apiRes = await fetch(`${API}/api/v1/retailer/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  })

  if (!apiRes.ok) {
    const err = await apiRes.json().catch(() => ({ detail: 'Registration failed' }))
    return NextResponse.json(
      { error: err.detail ?? 'Registration failed' },
      { status: apiRes.status },
    )
  }

  // 2. Create HubSpot contact (fire-and-forget — don't block registration on this)
  if (HUBSPOT_TOKEN) {
    fetch('https://api.hubapi.com/crm/v3/objects/contacts', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${HUBSPOT_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        properties: {
          email: body.email,
          firstname: body.contact_name?.split(' ')[0] ?? '',
          lastname: body.contact_name?.split(' ').slice(1).join(' ') ?? '',
          company: body.company_name,
          phone: body.phone,
          country: body.country_code,
          jobtitle: body.role,
          // referral_source stored in our DB; HubSpot custom property needed for this field
        },
      }),
    }).catch((e) => console.warn('HubSpot contact creation failed:', e))
  }

  return NextResponse.json({ success: true })
}
