import { formatDistanceStrict } from "date-fns"

import type { Opportunity, OpportunityWithProfits } from "../types"

export function calculateProfits(opp: Opportunity): OpportunityWithProfits {
  const edge = opp.edge

  return {
    ...opp,
    profitAt10: edge * 10,
    profitAt100: edge * 100,
    profitAt1000: edge * 1000,
    profitAt10000: edge * 10000,
  }
}

export function formatCurrency(value: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: 0,
    maximumFractionDigits: 0,
  }).format(value)
}

export function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)}%`
}

export function formatSimilarity(value: number | undefined | null): string {
  if (value === null || value === undefined) return "--"
  return `${(value * 100).toFixed(1)}%`
}

export function formatTimeToClose(closeTime: string | null | undefined): string {
  if (!closeTime) return "No close date"

  const now = new Date()
  const close = new Date(closeTime)
  const diff = close.getTime() - now.getTime()

  if (diff < 0) return "Closed"

  const hours = Math.floor(diff / (1000 * 60 * 60))
  const days = Math.floor(hours / 24)

  if (days > 0) return `${days}d`
  if (hours > 0) return `${hours}h`
  return "<1h"
}

export function normalizeCategory(category: string | undefined): string {
  if (!category) return "Other"
  return category
    .toLowerCase()
    .replace(/-/g, " ")
    .replace(/\b\w/g, (l) => l.toUpperCase())
}

export function formatCloseDifference(
  baseCloseTime?: string | null,
  candidateCloseTime?: string | null,
): string {
  if (!baseCloseTime || !candidateCloseTime) {
    return "--"
  }

  try {
    const base = new Date(baseCloseTime)
    const candidate = new Date(candidateCloseTime)
    return formatDistanceStrict(base, candidate, { addSuffix: false })
  } catch {
    return "--"
  }
}
