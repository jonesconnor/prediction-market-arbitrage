"use client"

import { CrossOpportunitiesMetrics } from "@/components/cross-opportunities-metrics"
import { CrossOpportunitiesTable } from "@/components/cross-opportunities-table"
import { Button } from "@/components/ui/button"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import type { CrossMatchMetrics, CrossMatchRow } from "@/lib/types"

type CrossOpportunitiesSectionProps = {
  rows: CrossMatchRow[]
  metrics: CrossMatchMetrics
  isLoading: boolean
  error: string | null
  onRefresh: () => void
}

export function CrossOpportunitiesSection({ rows, metrics, isLoading, error, onRefresh }: CrossOpportunitiesSectionProps) {
  return (
    <section className="space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold">Cross-Market Opportunities</h2>
          <p className="text-sm text-muted-foreground">
            Potentially related markets surfaced via text similarity and structural filters.
          </p>
        </div>
        <Button variant="outline" size="sm" onClick={onRefresh} disabled={isLoading}>
          Refresh
        </Button>
      </div>

      {error && (
        <div className="rounded-md border border-destructive/40 bg-destructive/10 px-3 py-2 text-sm text-destructive">
          {error}
        </div>
      )}

      <CrossOpportunitiesMetrics metrics={metrics} isLoading={isLoading} />

      <Card>
        <CardHeader>
          <CardTitle className="text-base">Top Matches</CardTitle>
        </CardHeader>
        <CardContent>
          <CrossOpportunitiesTable rows={rows} isLoading={isLoading} />
        </CardContent>
      </Card>
    </section>
  )
}
