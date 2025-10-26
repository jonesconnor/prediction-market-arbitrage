"use client"

import { useState } from "react"
import { useOpportunities } from "@/hooks/use-opportunities"
import { useCrossOpportunities } from "@/hooks/use-cross-opportunities"
import { useSSE } from "@/hooks/use-sse"
import { getSSEUrl } from "@/lib/api"
import type { Opportunity } from "@/lib/types"
import { ConnectionStatusIndicator } from "./connection-status"
import { LiveMetrics } from "./live-metrics"
import { FiltersBar } from "./filters-bar"
import { OpportunitiesTable } from "./opportunities-table"
import { EdgeDistribution } from "./edge-distribution"
import { MarketDetailDrawer } from "./market-detail-drawer"
import { CrossOpportunitiesSection } from "./cross-opportunities-section"

type DashboardClientProps = {
  initialData: Opportunity[]
}

export function DashboardClient({ initialData }: DashboardClientProps) {
  const { opportunities, filters, setFilters, stats, handleSSEMessage } = useOpportunities(initialData)
  const connectionStatus = useSSE(getSSEUrl(), handleSSEMessage)
  const [selectedMarketId, setSelectedMarketId] = useState<string | null>(null)
  const {
    rows: crossRows,
    metrics: crossMetrics,
    isLoading: crossLoading,
    error: crossError,
    refresh: refreshCross,
  } = useCrossOpportunities(20)

  const selectedOpportunity = opportunities.find((o) => o.marketId === selectedMarketId) || null

  return (
    <div className="min-h-screen bg-background">
      <header className="border-b border-border bg-card">
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-2xl font-bold">Polymarket Arbitrage</h1>
              <p className="text-sm text-muted-foreground mt-1">Real-time intra-market arbitrage opportunities</p>
            </div>
            <ConnectionStatusIndicator status={connectionStatus} />
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8 space-y-6">
        <LiveMetrics
          count={stats.count}
          avgEdge={stats.avgEdge}
          totalLiquidity={stats.totalLiquidity}
          bestEdge={stats.bestEdge}
        />

        <FiltersBar filters={filters} onChange={setFilters} />

        <div className="grid gap-6 lg:grid-cols-3">
          <div className="lg:col-span-2">
            <OpportunitiesTable opportunities={opportunities} onSelectOpportunity={setSelectedMarketId} />
          </div>
          <div>
            <EdgeDistribution opportunities={opportunities} />
          </div>
        </div>

        <CrossOpportunitiesSection
          rows={crossRows}
          metrics={crossMetrics}
          isLoading={crossLoading}
          error={crossError}
          onRefresh={refreshCross}
        />
      </main>

      <MarketDetailDrawer
        opportunity={selectedOpportunity}
        open={selectedMarketId !== null}
        onClose={() => setSelectedMarketId(null)}
      />
    </div>
  )
}
