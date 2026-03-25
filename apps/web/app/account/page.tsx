'use client'

import { useEffect, useState } from 'react'
import { Building2, Link2, Loader2, Trash2, CheckCircle2, AlertCircle, Clock, XCircle, Plus } from 'lucide-react'

type Account = {
  id: string
  distributor_code: string
  distributor_name: string
  account_number: string | null
  status: 'pending' | 'approved' | 'rejected' | 'withdrawn'
  rejection_reason: string | null
  created_at: string
}

type Profile = {
  id: string
  company_name: string
  email: string
  country_code: string
  accounts: Account[]
}

type Distributor = {
  distributor_code: string
  distributor_name: string
  requires_account_number: boolean
}

function StatusBadge({ status }: { status: Account['status'] }) {
  if (status === 'approved') {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-green-700 bg-green-50 border border-green-200 rounded-full px-2 py-0.5">
        <CheckCircle2 size={11} /> Approved
      </span>
    )
  }
  if (status === 'pending') {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-amber-700 bg-amber-50 border border-amber-200 rounded-full px-2 py-0.5">
        <Clock size={11} /> Pending approval
      </span>
    )
  }
  if (status === 'rejected') {
    return (
      <span className="flex items-center gap-1 text-xs font-medium text-red-700 bg-red-50 border border-red-200 rounded-full px-2 py-0.5">
        <XCircle size={11} /> Rejected
      </span>
    )
  }
  return null
}

export default function AccountPage() {
  const [profile, setProfile] = useState<Profile | null>(null)
  const [distributors, setDistributors] = useState<Distributor[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Link form state
  const [showForm, setShowForm] = useState(false)
  const [selectedCode, setSelectedCode] = useState('')
  const [accountNumber, setAccountNumber] = useState('')
  const [linking, setLinking] = useState(false)
  const [linkError, setLinkError] = useState<string | null>(null)

  // Company name edit state
  const [editingName, setEditingName] = useState(false)
  const [companyName, setCompanyName] = useState('')
  const [savingName, setSavingName] = useState(false)

  // Withdraw state
  const [withdrawingId, setWithdrawingId] = useState<string | null>(null)

  useEffect(() => {
    Promise.all([
      fetch('/api/retailer/me').then((r) => r.json()),
      fetch('/api/retailer/distributors').then((r) => r.json()),
    ])
      .then(([profileData, distData]) => {
        setProfile(profileData)
        setCompanyName(profileData.company_name ?? '')
        setDistributors(Array.isArray(distData) ? distData : [])
      })
      .catch(() => setError('Could not load account details'))
      .finally(() => setLoading(false))
  }, [])

  const saveCompanyName = async () => {
    if (!companyName.trim()) return
    setSavingName(true)
    try {
      const res = await fetch('/api/retailer/me', {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ company_name: companyName }),
      })
      if (!res.ok) throw new Error()
      const updated = await res.json()
      setProfile(updated)
      setEditingName(false)
    } catch {
      setError('Failed to update company name')
    } finally {
      setSavingName(false)
    }
  }

  const submitLinkRequest = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!selectedCode) return
    setLinking(true)
    setLinkError(null)
    try {
      const res = await fetch('/api/retailer/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          distributor_code: selectedCode,
          account_number: accountNumber || null,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail ?? 'Failed to submit request')
      setProfile((prev) =>
        prev ? { ...prev, accounts: [...prev.accounts, data] } : prev,
      )
      setShowForm(false)
      setSelectedCode('')
      setAccountNumber('')
    } catch (err: unknown) {
      setLinkError(err instanceof Error ? err.message : 'Failed to submit request')
    } finally {
      setLinking(false)
    }
  }

  const withdrawRequest = async (accountId: string) => {
    setWithdrawingId(accountId)
    try {
      const res = await fetch(`/api/retailer/accounts/${accountId}`, { method: 'DELETE' })
      if (!res.ok && res.status !== 204) throw new Error()
      setProfile((prev) =>
        prev
          ? { ...prev, accounts: prev.accounts.filter((a) => a.id !== accountId) }
          : prev,
      )
    } catch {
      setError('Failed to withdraw request')
    } finally {
      setWithdrawingId(null)
    }
  }

  const selectedDistributor = distributors.find((d) => d.distributor_code === selectedCode)

  // Distributors with an active pending/approved request are already "in flight"
  const unavailableCodes = new Set(
    profile?.accounts
      .filter((a) => a.status === 'pending' || a.status === 'approved')
      .map((a) => a.distributor_code),
  )
  const availableToLink = distributors.filter((d) => !unavailableCodes.has(d.distributor_code))

  if (loading) {
    return (
      <div className="flex justify-center py-24">
        <Loader2 className="animate-spin text-slate-400" size={24} />
      </div>
    )
  }

  if (error && !profile) {
    return (
      <div className="max-w-2xl mx-auto px-4 py-16">
        <div className="bg-red-50 border border-red-200 rounded-lg p-4 text-red-600 text-sm">{error}</div>
      </div>
    )
  }

  return (
    <div className="max-w-2xl mx-auto px-4 sm:px-6 py-10">
      <h1 className="text-2xl font-bold text-slate-900 mb-8">My Account</h1>

      {error && (
        <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-600 text-sm mb-6">
          {error}
        </div>
      )}

      {/* Profile card */}
      <div className="bg-white border border-slate-200 rounded-xl p-6 mb-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
            <Building2 size={18} className="text-amber-600" />
          </div>
          <div>
            <p className="text-xs text-slate-500 font-medium uppercase tracking-wider">Retailer Account</p>
            <p className="text-sm text-slate-500">{profile?.email}</p>
          </div>
        </div>

        <div>
          <label className="block text-sm font-medium text-slate-700 mb-1">Company name</label>
          {editingName ? (
            <div className="flex gap-2">
              <input
                value={companyName}
                onChange={(e) => setCompanyName(e.target.value)}
                className="flex-1 px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-400 focus:border-transparent"
                autoFocus
              />
              <button
                onClick={saveCompanyName}
                disabled={savingName}
                className="px-3 py-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white text-sm rounded-md"
              >
                {savingName ? <Loader2 size={14} className="animate-spin" /> : 'Save'}
              </button>
              <button
                onClick={() => { setEditingName(false); setCompanyName(profile?.company_name ?? '') }}
                className="px-3 py-2 border border-slate-300 text-slate-600 hover:bg-slate-50 text-sm rounded-md"
              >
                Cancel
              </button>
            </div>
          ) : (
            <div className="flex items-center gap-3">
              <span className="text-sm text-slate-900">{profile?.company_name}</span>
              <button
                onClick={() => setEditingName(true)}
                className="text-xs text-amber-600 hover:text-amber-700 font-medium"
              >
                Edit
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Distributor accounts */}
      <div className="bg-white border border-slate-200 rounded-xl p-6">
        <div className="flex items-center justify-between mb-5">
          <div>
            <h2 className="text-base font-semibold text-slate-900">Distributor accounts</h2>
            <p className="text-xs text-slate-500 mt-0.5">
              Request to link your trade accounts to see live prices in the catalogue.
            </p>
          </div>
          {availableToLink.length > 0 && !showForm && (
            <button
              onClick={() => setShowForm(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-amber-500 hover:bg-amber-600 text-white text-sm rounded-md"
            >
              <Plus size={14} />
              Request link
            </button>
          )}
        </div>

        {/* Accounts list */}
        {profile?.accounts && profile.accounts.length > 0 ? (
          <div className="space-y-3 mb-5">
            {profile.accounts.map((account) => (
              <div
                key={account.id}
                className="flex items-start justify-between py-3 px-4 bg-slate-50 border border-slate-200 rounded-lg"
              >
                <div className="flex items-start gap-3 min-w-0">
                  <div className="mt-0.5">
                    {account.status === 'approved' && <CheckCircle2 size={16} className="text-green-500 shrink-0" />}
                    {account.status === 'pending' && <Clock size={16} className="text-amber-500 shrink-0" />}
                    {account.status === 'rejected' && <XCircle size={16} className="text-red-500 shrink-0" />}
                  </div>
                  <div className="min-w-0">
                    <div className="flex items-center gap-2 flex-wrap">
                      <p className="text-sm font-medium text-slate-900">{account.distributor_name}</p>
                      <StatusBadge status={account.status} />
                    </div>
                    {account.account_number && (
                      <p className="text-xs text-slate-500 mt-0.5">Account: {account.account_number}</p>
                    )}
                    {account.status === 'rejected' && account.rejection_reason && (
                      <p className="text-xs text-red-600 mt-1">Reason: {account.rejection_reason}</p>
                    )}
                    {account.status === 'pending' && (
                      <p className="text-xs text-slate-400 mt-1">Awaiting distributor approval</p>
                    )}
                  </div>
                </div>
                <button
                  onClick={() => withdrawRequest(account.id)}
                  disabled={withdrawingId === account.id}
                  className="ml-3 p-1.5 text-slate-400 hover:text-red-500 disabled:opacity-40 transition-colors shrink-0"
                  title={account.status === 'approved' ? 'Unlink account' : 'Withdraw request'}
                >
                  {withdrawingId === account.id
                    ? <Loader2 size={14} className="animate-spin" />
                    : <Trash2 size={14} />
                  }
                </button>
              </div>
            ))}
          </div>
        ) : !showForm ? (
          <div className="text-center py-8 text-slate-400">
            <Link2 size={24} className="mx-auto mb-2" />
            <p className="text-sm">No distributor accounts linked yet</p>
          </div>
        ) : null}

        {/* Link request form */}
        {showForm && (
          <form onSubmit={submitLinkRequest} className="border border-slate-200 rounded-lg p-4 bg-slate-50">
            <h3 className="text-sm font-semibold text-slate-800 mb-1">Request a distributor account link</h3>
            <p className="text-xs text-slate-500 mb-4">
              Once submitted, the distributor will review your request and approve or reject it.
            </p>

            {linkError && (
              <div className="flex items-center gap-2 text-sm text-red-600 bg-red-50 border border-red-200 rounded-md p-2.5 mb-4">
                <AlertCircle size={14} />
                {linkError}
              </div>
            )}

            <div className="space-y-3">
              <div>
                <label className="block text-xs font-medium text-slate-700 mb-1">Distributor</label>
                <select
                  value={selectedCode}
                  onChange={(e) => { setSelectedCode(e.target.value); setAccountNumber('') }}
                  required
                  className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm bg-white focus:outline-none focus:ring-2 focus:ring-amber-400"
                >
                  <option value="">Select a distributor…</option>
                  {availableToLink.map((d) => (
                    <option key={d.distributor_code} value={d.distributor_code}>
                      {d.distributor_name}
                    </option>
                  ))}
                </select>
              </div>

              {selectedDistributor?.requires_account_number && (
                <div>
                  <label className="block text-xs font-medium text-slate-700 mb-1">
                    Account number
                  </label>
                  <input
                    value={accountNumber}
                    onChange={(e) => setAccountNumber(e.target.value)}
                    placeholder="e.g. GB123456"
                    className="w-full px-3 py-2 border border-slate-300 rounded-md text-sm focus:outline-none focus:ring-2 focus:ring-amber-400"
                  />
                  <p className="text-xs text-slate-400 mt-1">
                    Enter your account number as provided by the distributor.
                  </p>
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <button
                  type="submit"
                  disabled={linking || !selectedCode}
                  className="flex items-center gap-1.5 px-4 py-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-60 text-white text-sm rounded-md"
                >
                  {linking && <Loader2 size={12} className="animate-spin" />}
                  Submit request
                </button>
                <button
                  type="button"
                  onClick={() => { setShowForm(false); setLinkError(null); setSelectedCode(''); setAccountNumber('') }}
                  className="px-4 py-2 border border-slate-300 text-slate-600 hover:bg-white text-sm rounded-md"
                >
                  Cancel
                </button>
              </div>
            </div>
          </form>
        )}

        {availableToLink.length === 0 && !showForm && profile?.accounts.length === distributors.length && (
          <p className="text-xs text-slate-400 mt-3">All available distributors have been requested.</p>
        )}
      </div>
    </div>
  )
}
