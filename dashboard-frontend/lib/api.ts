import type { Opportunity, EdgeHistoryPoint, CrossMatchGroup } from "./types"

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000"

export async function getOpportunities(): Promise<Opportunity[]> {
  const res = await fetch(`${API_URL}/v1/opportunities`, {
    cache: "no-store",
  })

  if (!res.ok) {
    throw new Error("Failed to fetch opportunities")
  }

  return res.json()
}

export async function getMarketHistory(marketId: string, limit = 100): Promise<EdgeHistoryPoint[]> {
  const res = await fetch(`${API_URL}/v1/history/${marketId}?limit=${limit}&order=asc`)

  if (!res.ok) {
    throw new Error("Failed to fetch market history")
  }

  return res.json()
}

export function getSSEUrl(): string {
  return `${API_URL}/v1/stream`
}

export async function getCrossOpportunities(limit = 10): Promise<CrossMatchGroup[]> {
  const res = await fetch(`${API_URL}/v1/cross-opportunities?limit=${limit}`, {
    cache: "no-store",
  })

  if (!res.ok) {
    throw new Error("Failed to fetch cross-market opportunities")
  }

  return res.json()
}
