'use client'

import { useEffect, useState, Suspense } from 'react'
import { useSearchParams } from 'next/navigation'
import { Settings, User, MapPin, Bell, Plus, Pencil, Trash2, Check, AlertCircle, X } from 'lucide-react'
import {
  getRetailerProfile, updateRetailerProfile,
  getSettings, updateSettings,
  getAddresses, createAddress, updateAddress, deleteAddress,
} from '@/lib/api'
import type { RetailerProfile, RetailerSettings, Address } from '@/lib/types'
import { cn } from '@/lib/utils'

// ─── Tabs ─────────────────────────────────────────────────────────────────────

const TABS = [
  { id: 'profile',       label: 'Profile',       icon: User },
  { id: 'addresses',     label: 'Addresses',     icon: MapPin },
  { id: 'notifications', label: 'Notifications', icon: Bell },
]

// ─── Address form ─────────────────────────────────────────────────────────────

type AddrFormData = {
  address_type: 'billing' | 'delivery'
  label: string; contact_name: string; line1: string; line2: string | null
  city: string; county: string | null; postcode: string; country_code: string; is_default: boolean
}

const EMPTY_ADDR: AddrFormData = {
  address_type: 'delivery',
  label: '', contact_name: '', line1: '', line2: '',
  city: '', county: '', postcode: '', country_code: 'GB', is_default: false,
}

function AddressForm({
  initial,
  onSave,
  onCancel,
}: {
  initial?: Partial<AddrFormData & { id: string }>
  onSave: (data: AddrFormData) => Promise<void>
  onCancel: () => void
}) {
  const [form, setForm] = useState({ ...EMPTY_ADDR, ...initial })
  const [saving, setSaving] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  const set = (k: string, v: unknown) => setForm(f => ({ ...f, [k]: v }))

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    setErr(null)
    try {
      await onSave(form)
    } catch (e: unknown) {
      setErr(e instanceof Error ? e.message : 'Failed to save address')
    } finally {
      setSaving(false)
    }
  }

  const field = (label: string, key: string, required = false, half = false) => (
    <div className={half ? 'col-span-1' : 'col-span-2'}>
      <label className="block text-xs font-medium text-slate-600 mb-1">{label}{required && ' *'}</label>
      <input
        value={(form as Record<string, unknown>)[key] as string ?? ''}
        onChange={e => set(key, e.target.value)}
        required={required}
        className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
      />
    </div>
  )

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="col-span-2">
          <label className="block text-xs font-medium text-slate-600 mb-1">Address type *</label>
          <select
            value={form.address_type}
            onChange={e => set('address_type', e.target.value)}
            className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value="billing">Billing</option>
            <option value="delivery">Delivery</option>
          </select>
        </div>
        {field('Label (e.g. "Main Shop")', 'label', true)}
        {field('Contact name', 'contact_name', true)}
        {field('Address line 1', 'line1', true)}
        {field('Address line 2', 'line2')}
        {field('City', 'city', true, true)}
        {field('County', 'county', false, true)}
        {field('Postcode', 'postcode', true, true)}
        {field('Country code', 'country_code', true, true)}
        <div className="col-span-2 flex items-center gap-2">
          <input
            type="checkbox"
            id="is_default"
            checked={form.is_default}
            onChange={e => set('is_default', e.target.checked)}
            className="accent-amber-500"
          />
          <label htmlFor="is_default" className="text-sm text-slate-600">Set as default</label>
        </div>
      </div>

      {err && (
        <div className="flex items-center gap-2 text-sm text-red-600">
          <AlertCircle size={14} /> {err}
        </div>
      )}

      <div className="flex gap-2">
        <button
          type="button"
          onClick={onCancel}
          className="flex-1 px-4 py-2 border border-slate-200 rounded-lg text-sm text-slate-600 hover:bg-slate-50"
        >
          Cancel
        </button>
        <button
          type="submit"
          disabled={saving}
          className="flex-1 px-4 py-2 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium"
        >
          {saving ? 'Saving…' : 'Save address'}
        </button>
      </div>
    </form>
  )
}

// ─── Profile tab ──────────────────────────────────────────────────────────────

function ProfileTab() {
  const [profile, setProfile] = useState<RetailerProfile | null>(null)
  const [form, setForm] = useState({ company_name: '', country_code: 'GB', san: '' })
  const [saving, setSaving] = useState(false)
  const [saved, setSaved] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getRetailerProfile().then(p => {
      setProfile(p)
      setForm({ company_name: p.company_name, country_code: p.country_code, san: p.san ?? '' })
    }).finally(() => setLoading(false))
  }, [])

  async function handleSave(e: React.FormEvent) {
    e.preventDefault()
    setSaving(true)
    try {
      const updated = await updateRetailerProfile({
        company_name: form.company_name,
        country_code: form.country_code,
        san: form.san || undefined,
      })
      setProfile(updated)
      setSaved(true)
      setTimeout(() => setSaved(false), 2000)
    } catch { /* ignore */ } finally {
      setSaving(false)
    }
  }

  if (loading) return <div className="animate-pulse h-40 bg-slate-100 rounded-lg" />

  return (
    <form onSubmit={handleSave} className="space-y-5 max-w-md">
      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Email</label>
        <input
          value={profile?.email ?? ''}
          disabled
          className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm bg-slate-50 text-slate-400"
        />
        <p className="text-xs text-slate-400 mt-1">Email is managed via your sign-in account</p>
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Company name *</label>
        <input
          value={form.company_name}
          onChange={e => setForm(f => ({ ...f, company_name: e.target.value }))}
          className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">Country code</label>
        <input
          value={form.country_code}
          maxLength={2}
          onChange={e => setForm(f => ({ ...f, country_code: e.target.value.toUpperCase() }))}
          className="w-24 px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
        />
      </div>

      <div>
        <label className="block text-xs font-medium text-slate-600 mb-1">
          SAN (Standard Address Number)
          <span className="font-normal text-slate-400 ml-1">— optional</span>
        </label>
        <input
          value={form.san}
          placeholder="e.g. 1234567"
          onChange={e => setForm(f => ({ ...f, san: e.target.value }))}
          className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-amber-500"
        />
        <p className="text-xs text-slate-400 mt-1">
          Your BIC-registered SAN. Required for some distributor integrations.{' '}
          <a href="https://www.bic.org.uk/7/Standard-Address-Number-(SAN)/" target="_blank" rel="noreferrer" className="text-amber-600 hover:underline">
            Register with BIC →
          </a>
        </p>
      </div>

      <button
        type="submit"
        disabled={saving}
        className="flex items-center gap-2 px-5 py-2.5 bg-amber-500 hover:bg-amber-600 disabled:opacity-50 text-white rounded-lg text-sm font-medium transition-colors"
      >
        {saved ? <><Check size={14} /> Saved!</> : saving ? 'Saving…' : 'Save profile'}
      </button>
    </form>
  )
}

// ─── Addresses tab ────────────────────────────────────────────────────────────

function AddressesTab() {
  const [addresses, setAddresses] = useState<Address[]>([])
  const [loading, setLoading] = useState(true)
  const [showForm, setShowForm] = useState(false)
  const [editing, setEditing] = useState<Address | null>(null)

  function load() {
    getAddresses().then(setAddresses).finally(() => setLoading(false))
  }
  useEffect(() => { load() }, [])

  async function handleCreate(data: typeof EMPTY_ADDR) {
    await createAddress(data as Omit<Address, 'id' | 'created_at'>)
    setShowForm(false)
    load()
  }

  async function handleUpdate(id: string, data: typeof EMPTY_ADDR) {
    await updateAddress(id, data)
    setEditing(null)
    load()
  }

  async function handleDelete(id: string) {
    if (!confirm('Remove this address?')) return
    await deleteAddress(id)
    load()
  }

  const billing = addresses.filter(a => a.address_type === 'billing')
  const delivery = addresses.filter(a => a.address_type === 'delivery')

  if (loading) return <div className="animate-pulse h-40 bg-slate-100 rounded-lg" />

  const AddressGroup = ({ title, items }: { title: string; items: Address[] }) => (
    <div className="mb-6">
      <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wide mb-3">{title}</h3>
      {items.length === 0 && (
        <p className="text-sm text-slate-400 italic">No {title.toLowerCase()} addresses yet.</p>
      )}
      <div className="space-y-3">
        {items.map(addr => (
          editing?.id === addr.id ? (
            <div key={addr.id} className="bg-slate-50 border border-slate-200 rounded-xl p-4">
              <AddressForm
                initial={{ ...addr }}
                onSave={d => handleUpdate(addr.id, d)}
                onCancel={() => setEditing(null)}
              />
            </div>
          ) : (
            <div key={addr.id} className="flex items-start justify-between bg-white border border-slate-200 rounded-xl p-4">
              <div className="text-sm">
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="font-medium text-slate-900">{addr.label}</span>
                  {addr.is_default && (
                    <span className="text-xs bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full">Default</span>
                  )}
                </div>
                <p className="text-slate-500">{addr.contact_name}</p>
                <p className="text-slate-500">{addr.line1}{addr.line2 ? `, ${addr.line2}` : ''}</p>
                <p className="text-slate-500">{addr.city}{addr.county ? `, ${addr.county}` : ''}, {addr.postcode}</p>
              </div>
              <div className="flex items-center gap-2 ml-4 flex-none">
                <button
                  onClick={() => setEditing(addr)}
                  className="text-slate-400 hover:text-amber-600 transition-colors"
                >
                  <Pencil size={14} />
                </button>
                <button
                  onClick={() => handleDelete(addr.id)}
                  className="text-slate-400 hover:text-red-500 transition-colors"
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
          )
        ))}
      </div>
    </div>
  )

  return (
    <div>
      <AddressGroup title="Delivery addresses" items={delivery} />
      <AddressGroup title="Billing addresses" items={billing} />

      {showForm ? (
        <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 mt-4">
          <div className="flex justify-between items-center mb-4">
            <h3 className="text-sm font-semibold text-slate-800">Add new address</h3>
            <button onClick={() => setShowForm(false)} className="text-slate-400 hover:text-slate-600">
              <X size={16} />
            </button>
          </div>
          <AddressForm onSave={handleCreate} onCancel={() => setShowForm(false)} />
        </div>
      ) : (
        <button
          onClick={() => setShowForm(true)}
          className="flex items-center gap-2 mt-2 px-4 py-2 border border-dashed border-slate-300 rounded-lg text-sm text-slate-500 hover:border-amber-400 hover:text-amber-600 transition-colors"
        >
          <Plus size={14} /> Add address
        </button>
      )}
    </div>
  )
}

// ─── Notifications tab ────────────────────────────────────────────────────────

function NotificationsTab() {
  const [settings, setSettings] = useState<RetailerSettings | null>(null)
  const [saving, setSaving] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    getSettings().then(setSettings).finally(() => setLoading(false))
  }, [])

  async function toggle(key: keyof RetailerSettings) {
    if (!settings) return
    const updated = { ...settings, [key]: !settings[key] }
    setSettings(updated)
    setSaving(key)
    try {
      const saved = await updateSettings({ [key]: updated[key] })
      setSettings(saved)
    } catch { setSettings(settings) } finally {
      setSaving(null)
    }
  }

  if (loading) return <div className="animate-pulse h-40 bg-slate-100 rounded-lg" />
  if (!settings) return null

  const toggles: { key: keyof RetailerSettings; label: string; description: string }[] = [
    {
      key: 'notify_order_submitted',
      label: 'Order submitted',
      description: 'Email when your order has been successfully transmitted to the distributor.',
    },
    {
      key: 'notify_backorder_alert',
      label: 'Back-order alert',
      description: 'Email when titles in your order are placed on back-order.',
    },
    {
      key: 'notify_invoice_available',
      label: 'Invoice available',
      description: 'Email when a distributor invoice is ready to view.',
    },
  ]

  return (
    <div className="space-y-4 max-w-lg">
      {toggles.map(({ key, label, description }) => (
        <div
          key={key}
          className="flex items-start justify-between gap-4 p-4 bg-white border border-slate-200 rounded-xl"
        >
          <div>
            <p className="text-sm font-medium text-slate-900">{label}</p>
            <p className="text-xs text-slate-500 mt-0.5">{description}</p>
          </div>
          <button
            onClick={() => toggle(key)}
            disabled={saving === key}
            className={cn(
              'relative flex-none w-10 h-5 rounded-full transition-colors mt-0.5',
              settings[key] ? 'bg-amber-500' : 'bg-slate-200',
              saving === key && 'opacity-50',
            )}
          >
            <span
              className={cn(
                'absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform',
                settings[key] ? 'translate-x-5' : 'translate-x-0.5',
              )}
            />
          </button>
        </div>
      ))}
    </div>
  )
}

// ─── Main settings page ───────────────────────────────────────────────────────

function SettingsContent() {
  const searchParams = useSearchParams()
  const [activeTab, setActiveTab] = useState(searchParams.get('tab') ?? 'profile')

  return (
    <div className="max-w-3xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="text-2xl font-bold text-slate-900 flex items-center gap-2 mb-6">
        <Settings size={24} className="text-amber-500" />
        Account settings
      </h1>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-slate-200 mb-6">
        {TABS.map(tab => {
          const Icon = tab.icon
          return (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={cn(
                'flex items-center gap-1.5 px-4 py-2.5 text-sm font-medium border-b-2 -mb-px transition-colors',
                activeTab === tab.id
                  ? 'border-amber-500 text-amber-600'
                  : 'border-transparent text-slate-500 hover:text-slate-700',
              )}
            >
              <Icon size={14} />
              {tab.label}
            </button>
          )
        })}
      </div>

      {/* Tab content */}
      {activeTab === 'profile'       && <ProfileTab />}
      {activeTab === 'addresses'     && <AddressesTab />}
      {activeTab === 'notifications' && <NotificationsTab />}
    </div>
  )
}

export default function SettingsPage() {
  return (
    <Suspense>
      <SettingsContent />
    </Suspense>
  )
}
