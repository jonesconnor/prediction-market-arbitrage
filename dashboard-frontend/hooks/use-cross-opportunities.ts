"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { getCrossOpportunities } from "@/lib/api"
import type { CrossMatchGroup, CrossMatchMetrics, CrossMatchRow } from "@/lib/types"

export function useCrossOpportunities(limit = 10) {
  const [groups, setGroups] = useState<CrossMatchGroup[]>([])
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchMatches = useCallback(async () => {
    setIsLoading(true)
    setError(null)
    try {
      const data = await getCrossOpportunities(limit)
      setGroups(data)
    } catch (err) {
      console.error("Failed to load cross-market opportunities", err)
      setError(err instanceof Error ? err.message : "Unknown error")
    } finally {
      setIsLoading(false)
    }
  }, [limit])

  useEffect(() => {
    fetchMatches()
  }, [fetchMatches])

  const rows: CrossMatchRow[] = useMemo(() => {
    return groups
      .flatMap((group) =>
        group.matches.map((candidate) => ({
          baseMarketId: group.baseMarketId,
          baseQuestion: group.baseQuestion,
          baseCategory: group.baseCategory ?? null,
          baseCloseTime: group.baseCloseTime ?? null,
          baseUrl: group.baseUrl ?? null,
          candidate,
        })),
      )
      .sort((a, b) => (b.candidate.similarity ?? 0) - (a.candidate.similarity ?? 0))
  }, [groups])

  const metrics: CrossMatchMetrics = useMemo(() => {
    if (rows.length === 0) {
      return {
        totalPairs: 0,
        uniqueBases: groups.length,
        avgSimilarity: 0,
        topSimilarity: 0,
        topCategory: null,
      }
    }

    const similarities = rows.map((row) => row.candidate.similarity ?? 0)
    const avgSimilarity = similarities.reduce((sum, value) => sum + value, 0) / similarities.length
    const topSimilarity = Math.max(...similarities)

    const categoryCounts = new Map<string, number>()
    for (const row of rows) {
      const cat = (row.baseCategory || row.candidate.category || "other").toLowerCase()
      categoryCounts.set(cat, (categoryCounts.get(cat) || 0) + 1)
    }
    const topCategoryEntry = Array.from(categoryCounts.entries()).sort((a, b) => b[1] - a[1])[0]

    return {
      totalPairs: rows.length,
      uniqueBases: groups.length,
      avgSimilarity,
      topSimilarity,
      topCategory: topCategoryEntry ? topCategoryEntry[0] : null,
    }
  }, [rows, groups.length])

  return {
    groups,
    rows,
    metrics,
    isLoading,
    error,
    refresh: fetchMatches,
  }
}
