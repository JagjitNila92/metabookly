'use client'

/**
 * FeatureGate — conditionally renders children based on a feature flag or plan tier.
 *
 * Usage (feature flag):
 *   <FeatureGate flag="ordering_enabled" fallback={<ComingSoonBanner />}>
 *     <BasketButton />
 *   </FeatureGate>
 *
 * Usage (plan gate):
 *   <FeatureGate plan="starter_api" currentPlan={retailer.plan} fallback={<UpgradePrompt />}>
 *     <ApiKeyPanel />
 *   </FeatureGate>
 *
 * When `flag` is provided the component fetches /api/flags?flags={flag} on mount.
 * When `plan` is provided it resolves synchronously from currentPlan + PLAN_ORDER.
 */

import { useEffect, useState } from 'react'
import { Lock, ArrowUpRight, Loader2 } from 'lucide-react'

// Must match PLAN_ORDER in auth/models.py
const PLAN_ORDER: Record<string, number> = {
  free: 0,
  starter_api: 1,
  intelligence: 2,
  enterprise: 3,
}

const PLAN_LABELS: Record<string, string> = {
  free: 'Free',
  starter_api: 'Starter API',
  intelligence: 'Intelligence',
  enterprise: 'Enterprise',
}

// ── Default upgrade prompt ────────────────────────────────────────────────────

function DefaultUpgradePrompt({ requiredPlan }: { requiredPlan: string }) {
  return (
    <div className="rounded-xl border border-dashed border-slate-300 bg-slate-50 p-6 flex flex-col items-center text-center gap-3">
      <div className="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center">
        <Lock size={16} className="text-amber-600" />
      </div>
      <div>
        <p className="text-sm font-semibold text-slate-800">
          {PLAN_LABELS[requiredPlan] ?? requiredPlan} plan required
        </p>
        <p className="text-xs text-slate-500 mt-1">
          Upgrade to unlock this feature
        </p>
      </div>
      <a
        href="/settings/plan"
        className="inline-flex items-center gap-1.5 text-xs font-medium text-amber-600 hover:text-amber-700"
      >
        View plans <ArrowUpRight size={12} />
      </a>
    </div>
  )
}

// ── Coming soon banner (used for ordering_enabled = false) ────────────────────

export function ComingSoonBanner({ message }: { message?: string }) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-700 flex items-center gap-2">
      <span className="font-semibold">Coming soon.</span>
      <span>{message ?? 'This feature is not yet available.'}</span>
    </div>
  )
}

// ── FeatureGate ───────────────────────────────────────────────────────────────

interface FeatureGateProps {
  /** Feature flag name to check via /api/flags */
  flag?: string
  /** Minimum plan tier required (requires currentPlan) */
  plan?: string
  /** The current account's plan tier */
  currentPlan?: string
  /** Rendered when the gate is closed. Defaults to UpgradePrompt for plan gates. */
  fallback?: React.ReactNode
  /** Rendered while flag is resolving */
  loading?: React.ReactNode
  children: React.ReactNode
}

export default function FeatureGate({
  flag,
  plan,
  currentPlan,
  fallback,
  loading,
  children,
}: FeatureGateProps) {
  const [flagEnabled, setFlagEnabled] = useState<boolean | null>(null)

  useEffect(() => {
    if (!flag) return
    fetch(`/api/flags?flags=${flag}`)
      .then(r => r.json())
      .then(data => setFlagEnabled(data[flag] ?? false))
      .catch(() => setFlagEnabled(false))
  }, [flag])

  // ── Plan-based gate (synchronous) ─────────────────────────────────────────
  if (plan) {
    const required = PLAN_ORDER[plan] ?? 0
    const current = PLAN_ORDER[currentPlan ?? 'free'] ?? 0
    if (current < required) {
      return <>{fallback ?? <DefaultUpgradePrompt requiredPlan={plan} />}</>
    }
    return <>{children}</>
  }

  // ── Flag-based gate (async) ────────────────────────────────────────────────
  if (flag) {
    if (flagEnabled === null) {
      return (
        <>
          {loading ?? (
            <div className="flex justify-center py-6">
              <Loader2 size={18} className="animate-spin text-slate-300" />
            </div>
          )}
        </>
      )
    }
    if (!flagEnabled) {
      return <>{fallback}</>
    }
    return <>{children}</>
  }

  // No gate specified — just render
  return <>{children}</>
}
