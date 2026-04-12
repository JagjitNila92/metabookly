import { NextRequest, NextResponse } from 'next/server'

const API            = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'
const HUBSPOT_TOKEN  = process.env.HUBSPOT_TOKEN

export async function POST(req: NextRequest) {
  const body = await req.json()

  // 1. Create publisher via FastAPI (Cognito + DB + welcome email)
  const apiRes = await fetch(`${API}/api/v1/publisher/register`, {
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

  // 2. Create HubSpot contact (fire-and-forget)
  if (HUBSPOT_TOKEN) {
    fetch('https://api.hubapi.com/crm/v3/objects/contacts', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${HUBSPOT_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        properties: {
          email:                        body.email,
          firstname:                    body.contact_name?.split(' ')[0] ?? '',
          lastname:                     body.contact_name?.split(' ').slice(1).join(' ') ?? '',
          company:                      body.company_name,
          phone:                        body.phone ?? '',
          website:                      body.website ?? '',
          // Custom properties — ensure these exist in your HubSpot portal
          account_type:                 'publisher',
          publisher_type:               body.publisher_type ?? '',
          approximate_title_count:      body.title_count ?? '',
          how_did_you_hear_about_us:    body.referral_source ?? '',
        },
      }),
    }).catch((e) => console.warn('HubSpot publisher contact creation failed:', e))
  }

  return NextResponse.json({ success: true })
}
