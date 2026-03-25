'use client'

import { useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { signIn } from 'next-auth/react'
import { BookOpen, Loader2, Check, X } from 'lucide-react'
import { Suspense } from 'react'

// ── Password rules ─────────────────────────────────────────────────────────────

const PASSWORD_RULES = [
  { label: 'At least 8 characters',       test: (p: string) => p.length >= 8 },
  { label: 'One uppercase letter',         test: (p: string) => /[A-Z]/.test(p) },
  { label: 'One lowercase letter',         test: (p: string) => /[a-z]/.test(p) },
  { label: 'One number',                   test: (p: string) => /[0-9]/.test(p) },
  { label: 'One special character (!@#$)', test: (p: string) => /[^A-Za-z0-9]/.test(p) },
]

function PasswordRule({ label, met }: { label: string; met: boolean }) {
  return (
    <li className={`flex items-center gap-1.5 text-xs transition-colors ${met ? 'text-green-600' : 'text-slate-400'}`}>
      {met ? <Check size={11} /> : <X size={11} />}
      {label}
    </li>
  )
}

// ── Field component ────────────────────────────────────────────────────────────

function Field({
  label, required = true, children,
}: { label: string; required?: boolean; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">
        {label}{required && <span className="text-red-400 ml-0.5">*</span>}
      </label>
      {children}
    </div>
  )
}

const INPUT = 'w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent'
const SELECT = `${INPUT} bg-white`

// ── Countries ─────────────────────────────────────────────────────────────────

const COUNTRIES = [
  { code: 'GB', name: 'United Kingdom' },
  { code: 'IE', name: 'Ireland' },
  { code: 'US', name: 'United States' },
  { code: 'AU', name: 'Australia' },
  { code: 'CA', name: 'Canada' },
  { code: 'NZ', name: 'New Zealand' },
  { code: 'ZA', name: 'South Africa' },
  { code: 'DE', name: 'Germany' },
  { code: 'FR', name: 'France' },
  { code: 'NL', name: 'Netherlands' },
  { code: 'BE', name: 'Belgium' },
  { code: 'SE', name: 'Sweden' },
  { code: 'NO', name: 'Norway' },
  { code: 'DK', name: 'Denmark' },
  { code: 'ES', name: 'Spain' },
  { code: 'IT', name: 'Italy' },
  { code: 'PT', name: 'Portugal' },
  { code: 'CH', name: 'Switzerland' },
  { code: 'AT', name: 'Austria' },
  { code: 'PL', name: 'Poland' },
  { code: 'IN', name: 'India' },
  { code: 'SG', name: 'Singapore' },
  { code: 'HK', name: 'Hong Kong' },
  { code: 'JP', name: 'Japan' },
]

// ── Form ──────────────────────────────────────────────────────────────────────

function RegisterForm() {
  const router = useRouter()
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const [form, setForm] = useState({
    contact_name: '',
    email: '',
    password: '',
    confirm_password: '',
    company_name: '',
    role: '',
    country_code: 'GB',
    phone: '',
    referral_source: '',
  })

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement | HTMLSelectElement>) =>
    setForm(f => ({ ...f, [k]: e.target.value }))

  const passwordMet = PASSWORD_RULES.map(r => r.test(form.password))
  const allPasswordRulesMet = passwordMet.every(Boolean)
  const passwordsMatch = form.password === form.confirm_password && form.confirm_password.length > 0

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')

    if (!allPasswordRulesMet) { setError('Password does not meet the requirements.'); return }
    if (!passwordsMatch) { setError('Passwords do not match.'); return }

    setLoading(true)
    try {
      const res = await fetch('/api/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: form.email,
          password: form.password,
          company_name: form.company_name,
          contact_name: form.contact_name,
          phone: form.phone,
          role: form.role,
          country_code: form.country_code,
          referral_source: form.referral_source,
        }),
      })

      const data = await res.json()
      if (!res.ok) { setError(data.error ?? 'Registration failed. Please try again.'); return }

      // Auto sign-in then redirect to dashboard
      const result = await signIn('credentials', {
        email: form.email,
        password: form.password,
        redirect: false,
      })

      if (result?.error) {
        // Account created but auto-sign-in failed — send to login
        router.push('/login?registered=1')
      } else {
        router.push('/dashboard?welcome=1')
      }
    } catch {
      setError('Something went wrong. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen bg-slate-50 py-12 px-4">
      <div className="max-w-lg mx-auto">

        {/* Logo */}
        <div className="flex items-center justify-center gap-2 mb-8">
          <BookOpen className="text-amber-500" size={28} />
          <span className="text-xl font-semibold text-slate-900">Metabookly</span>
        </div>

        <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-8">
          <h1 className="text-lg font-semibold text-slate-900 mb-1">Create your retailer account</h1>
          <p className="text-sm text-slate-500 mb-6">
            See live trade prices from Gardners, Bertrams and more — free to join.
          </p>

          <form onSubmit={handleSubmit} className="space-y-4">

            {/* Row: Full name + Email */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Full name">
                <input type="text" value={form.contact_name} onChange={set('contact_name')}
                  required placeholder="Jane Smith" className={INPUT} />
              </Field>
              <Field label="Email address">
                <input type="email" value={form.email} onChange={set('email')}
                  required placeholder="jane@yourbookshop.com" className={INPUT} />
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

            {/* Row: Company + Role */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Company / shop name">
                <input type="text" value={form.company_name} onChange={set('company_name')}
                  required placeholder="Pages & Binding Books" className={INPUT} />
              </Field>
              <Field label="Your role">
                <select value={form.role} onChange={set('role')} required className={SELECT}>
                  <option value="">Select role…</option>
                  <option>Owner</option>
                  <option>Director</option>
                  <option>Buyer</option>
                  <option>Manager</option>
                  <option>Other</option>
                </select>
              </Field>
            </div>

            {/* Row: Country + Phone */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <Field label="Country">
                <select value={form.country_code} onChange={set('country_code')} required className={SELECT}>
                  {COUNTRIES.map(c => (
                    <option key={c.code} value={c.code}>{c.name}</option>
                  ))}
                </select>
              </Field>
              <Field label="Mobile / contact number">
                <input type="tel" value={form.phone} onChange={set('phone')}
                  required placeholder="+44 7700 900000" className={INPUT} />
              </Field>
            </div>

            {/* How did you hear */}
            <Field label="How did you hear about Metabookly?">
              <select value={form.referral_source} onChange={set('referral_source')} required className={SELECT}>
                <option value="">Select an option…</option>
                <option>Google Search</option>
                <option>Social Media</option>
                <option>Publisher recommendation</option>
                <option>Word of mouth</option>
                <option>Trade event</option>
                <option>Gardners / Bertrams</option>
                <option>Other</option>
              </select>
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
              {loading ? 'Creating account…' : 'Create account'}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-slate-500 mt-4">
          Already have an account?{' '}
          <Link href="/login" className="text-amber-600 hover:text-amber-700 font-medium">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}

export default function RegisterPage() {
  return (
    <Suspense>
      <RegisterForm />
    </Suspense>
  )
}
