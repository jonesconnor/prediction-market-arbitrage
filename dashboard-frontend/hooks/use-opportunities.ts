"use client"

import { useState, useMemo, useCallback } from "react"
import type { Opportunity, FilterState, SSEMessage } from "@/lib/types"
import { calculateProfits } from "@/lib/utils/opportunity"

const DEFAULT_FILTERS: FilterState = {
  minEdge: 0,
  maxEdge: 1,
  minLiquidity: 0,
  category: "all",
  sortBy: "edge",
  sortOrder: "desc",
}

export function useOpportunities(initialData: Opportunity[]) {
  const [opportunities, setOpportunities] = useState<Map<string, Opportunity>>(
    new Map(initialData.map((opp) => [opp.marketId, opp])),
  )
  const [filters, setFilters] = useState<FilterState>(DEFAULT_FILTERS)

  const handleSSEMessage = useCallback((message: SSEMessage) => {
    if (message.type === "upsert" && message.opportunity) {
      setOpportunities((prev) => {
        const next = new Map(prev)
        next.set(message.marketId, message.opportunity!)
        return next
      })
    } else if (message.type === "remove") {
      setOpportunities((prev) => {
        const next = new Map(prev)
        next.delete(message.marketId)
        return next
      })
    }
  }, [])

  const filteredAndSorted = useMemo(() => {
    const result = Array.from(opportunities.values())
      .map(calculateProfits)
      .filter((opp) => {
        if (opp.edge < filters.minEdge || opp.edge > filters.maxEdge) return false
        if (filters.minLiquidity > 0 && (opp.liquidity || 0) < filters.minLiquidity) return false
        if (filters.category !== "all" && opp.category?.toLowerCase() !== filters.category.toLowerCase()) return false
        return true
      })

    result.sort((a, b) => {
      let aVal: number, bVal: number

      switch (filters.sortBy) {
        case "edge":
          aVal = a.edge
          bVal = b.edge
          break
        case "profitAt1000":
          aVal = a.profitAt1000
          bVal = b.profitAt1000
          break
        case "liquidity":
          aVal = a.liquidity || 0
          bVal = b.liquidity || 0
          break
        case "closeTime":
          aVal = a.closeTime ? new Date(a.closeTime).getTime() : Number.POSITIVE_INFINITY
          bVal = b.closeTime ? new Date(b.closeTime).getTime() : Number.POSITIVE_INFINITY
          break
        default:
          aVal = a.edge
          bVal = b.edge
      }

      return filters.sortOrder === "desc" ? bVal - aVal : aVal - bVal
    })

    return result
  }, [opportunities, filters])

  const stats = useMemo(() => {
    const opps = Array.from(opportunities.values())
    return {
      count: opps.length,
      avgEdge: opps.length > 0 ? opps.reduce((sum, o) => sum + o.edge, 0) / opps.length : 0,
      totalLiquidity: opps.reduce((sum, o) => sum + (o.liquidity || 0), 0),
      bestEdge: opps.length > 0 ? Math.max(...opps.map((o) => o.edge)) : 0,
    }
  }, [opportunities])

  return {
    opportunities: filteredAndSorted,
    filters,
    setFilters,
    stats,
    handleSSEMessage,
  }
}
