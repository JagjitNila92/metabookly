'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { signIn } from 'next-auth/react'
import { BookOpen, Check, Loader2, X } from 'lucide-react'
import { Suspense } from 'react'

// ── Password rules ─────────────────────────────────────────────────────────────

const PASSWORD_RULES = [
  { label: 'At least 8 characters',        test: (p: string) => p.length >= 8 },
  { label: 'One uppercase letter',          test: (p: string) => /[A-Z]/.test(p) },
  { label: 'One lowercase letter',          test: (p: string) => /[a-z]/.test(p) },
  { label: 'One number',                    test: (p: string) => /[0-9]/.test(p) },
  { label: 'One special character (!@#$)',  test: (p: string) => /[^A-Za-z0-9]/.test(p) },
]

function PasswordRule({ label, met }: { label: string; met: boolean }) {
  return (
    <li className={`flex items-center gap-1.5 text-xs transition-colors ${met ? 'text-green-600' : 'text-slate-400'}`}>
      {met ? <Check size={11} /> : <X size={11} />}
      {label}
    </li>
  )
}

function Field({ label, required = true, children }: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  )
}

const INPUT  = 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent'
const SELECT = `${INPUT} bg-white`

// ── Free tier benefits list ────────────────────────────────────────────────────

const BENEFITS = [
  'Unlimited title listings — always free',
  'ONIX 3.0 and 2.1 upload support',
  'Metadata quality scoring per title',
  'AI-powered description enrichment',
  'Real-time feed history and error reports',
  'Visible to thousands of UK booksellers',
]

// ── Form ──────────────────────────────────────────────────────────────────────

function PublisherRegisterForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError]     = useState('')

  const [form, setForm] = useState({
    contact_name:     '',
    email:            '',
    password:         '',
    confirm_password: '',
    company_name:     '',
    publisher_type:   '',
    phone:            '',
    website:          '',
    title_count:      '',
    referral_source:  '',
  })

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const passwordMet        = PASSWORD_RULES.map(r => r.test(form.password))
  const allPasswordRulesMet = passwordMet.every(Boolean)
  const passwordsMatch      = form.password === form.confirm_password && form.confirm_password.length > 0

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!allPasswordRulesMet) { setError('Password does not meet the requirements.'); return }
    if (!passwordsMatch)      { setError('Passwords do not match.'); return }

    setLoading(true)
    try {
      const res = await fetch('/api/register/publisher', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email:            form.email,
          password:         form.password,
          contact_name:     form.contact_name,
          company_name:     form.company_name,
          publisher_type:   form.publisher_type || null,
          phone:            form.phone || null,
          website:          form.website || null,
          title_count:      form.title_count || null,
          referral_source:  form.referral_source || null,
        }),
      })

      const data = await res.json()
      if (!res.ok) { setError(data.error ?? 'Registration failed. Please try again.'); return }

      // Auto sign-in then redirect to publisher dashboard
      const result = await signIn('credentials', {
        email:    form.email,
        password: form.password,
        redirect: false,
      })

      if (result?.error) {
        router.push('/login?registered=1')
      } else {
        router.push('/publisher/dashboard?welcome=1')
      }
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="max-w-2xl mx-auto">

        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <BookOpen className="text-amber-500" size={28} />
          <span className="text-xl font-semibold text-slate-900">Metabookly</span>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-5 gap-6">

          {/* Left: free tier benefits */}
          <div className="lg:col-span-2">
            <div className="bg-amber-50 border border-amber-200 rounded-xl p-6">
              <p className="text-xs font-semibold text-amber-700 uppercase tracking-wide mb-1">Free forever</p>
              <h2 className="text-lg font-semibold text-slate-900 mb-4">
                List your entire catalogue at no cost
              </h2>
              <ul className="space-y-3">
                {BENEFITS.map(b => (
                  <li key={b} className="flex items-start gap-2 text-sm text-slate-700">
                    <Check size={15} className="text-amber-500 mt-0.5 shrink-0" />
                    {b}
                  </li>
                ))}
              </ul>
              <p className="mt-6 text-xs text-slate-500">
                No credit card required. No title fees. No lock-in.
              </p>
            </div>
          </div>

          {/* Right: form */}
          <div className="lg:col-span-3 bg-white rounded-xl border border-slate-200 shadow-sm p-8">
            <h1 className="text-lg font-semibold text-slate-900 mb-1">Create your publisher account</h1>
            <p className="text-sm text-slate-500 mb-6">
              Start uploading your catalogue today — it takes less than 2 minutes.
            </p>

            <form onSubmit={handleSubmit} className="space-y-4">

              {/* Row: Full name + Email */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Your name">
                  <input type="text" value={form.contact_name} onChange={set('contact_name')}
                    required placeholder="Jane Smith" className={INPUT} />
                </Field>
                <Field label="Email address">
                  <input type="email" value={form.email} onChange={set('email')}
                    required placeholder="jane@yourpress.com" className={INPUT} />
                </Field>
              </div>

              {/* Row: Company + Type */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Publisher / company name">
                  <input type="text" value={form.company_name} onChange={set('company_name')}
                    required placeholder="Harbour Books" className={INPUT} />
                </Field>
                <Field label="Publisher type" required={false}>
                  <select value={form.publisher_type} onChange={set('publisher_type')} className={SELECT}>
                    <option value="">Select (optional)</option>
                    <option value="indie">Independent press</option>
                    <option value="traditional">Traditional publisher</option>
                    <option value="university-press">University press</option>
                    <option value="self-pub">Self-publishing / hybrid</option>
                  </select>
                </Field>
              </div>

              {/* Row: Titles + Website */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Approx. number of titles" required={false}>
                  <select value={form.title_count} onChange={set('title_count')} className={SELECT}>
                    <option value="">Select (optional)</option>
                    <option value="1-10">1 – 10</option>
                    <option value="11-50">11 – 50</option>
                    <option value="51-200">51 – 200</option>
                    <option value="201-500">201 – 500</option>
                    <option value="500+">500+</option>
                  </select>
                </Field>
                <Field label="Publisher website" required={false}>
                  <input type="url" value={form.website} onChange={set('website')}
                    placeholder="https://yourpress.com" className={INPUT} />
                </Field>
              </div>

              {/* Row: Phone + How did you hear */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <Field label="Phone number" required={false}>
                  <input type="tel" value={form.phone} onChange={set('phone')}
                    placeholder="+44 7700 900000" className={INPUT} />
                </Field>
                <Field label="How did you hear about us?" required={false}>
                  <select value={form.referral_source} onChange={set('referral_source')} className={SELECT}>
                    <option value="">Select (optional)</option>
                    <option value="google">Google Search</option>
                    <option value="social_media">Social Media</option>
                    <option value="bookseller_recommendation">Bookseller recommendation</option>
                    <option value="distributor">Distributor / Gardners</option>
                    <option value="word_of_mouth">Word of mouth</option>
                    <option value="trade_press">Trade press (The Bookseller etc.)</option>
                    <option value="trade_event">Trade event / London Book Fair</option>
                    <option value="other">Other</option>
                  </select>
                </Field>
              </div>

              {/* Password */}
              <Field label="Password">
                <input type="password" value={form.password} onChange={set('password')}
                  required placeholder="••••••••" className={INPUT} />
                {form.password.length > 0 && (
                  <ul className="mt-2 space-y-1 pl-1">
                    {PASSWORD_RULES.map((r, i) => (
                      <PasswordRule key={r.label} label={r.label} met={passwordMet[i]} />
                    ))}
                  </ul>
                )}
              </Field>

              {/* Confirm password */}
              <Field label="Confirm password">
                <input type="password" value={form.confirm_password} onChange={set('confirm_password')}
                  required placeholder="••••••••" className={INPUT} />
                {form.confirm_password.length > 0 && (
                  <p className={`text-xs mt-1 flex items-center gap-1 ${passwordsMatch ? 'text-green-600' : 'text-red-500'}`}>
                    {passwordsMatch ? <Check size={11} /> : <X size={11} />}
                    {passwordsMatch ? 'Passwords match' : 'Passwords do not match'}
                  </p>
                )}
              </Field>

              {error && (
                <p className="text-sm text-red-500 bg-red-50 border border-red-200 rounded-md px-3 py-2">
                  {error}
                </p>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full flex items-center justify-center gap-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white font-medium py-2.5 px-4 rounded-md transition-colors mt-2"
              >
                {loading && <Loader2 size={15} className="animate-spin" />}
                {loading ? 'Creating account…' : 'Create free account'}
              </button>

              <p className="text-xs text-center text-slate-400">
                By signing up you agree to our Terms of Service and Privacy Policy.
              </p>
            </form>
          </div>
        </div>

        <p className="text-center text-sm text-slate-500 mt-6">
          Already have an account?{' '}
          <Link href="/login" className="text-amber-600 hover:text-amber-700 font-medium">Sign in</Link>
          {' · '}
          <Link href="/register" className="text-amber-600 hover:text-amber-700 font-medium">Register as a retailer</Link>
        </p>
      </div>
    </div>
  )
}

export default function PublisherRegisterPage() {
  return (
    <Suspense>
      <PublisherRegisterForm />
    </Suspense>
  )
}
