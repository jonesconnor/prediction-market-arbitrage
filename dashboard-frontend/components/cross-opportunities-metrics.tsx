"use client"

import { Card, CardContent } from "@/components/ui/card"
import type { CrossMatchMetrics } from "@/lib/types"
import { formatSimilarity, normalizeCategory } from "@/lib/utils/opportunity"

type CrossOpportunitiesMetricsProps = {
  metrics: CrossMatchMetrics
  isLoading: boolean
}

export function CrossOpportunitiesMetrics({ metrics, isLoading }: CrossOpportunitiesMetricsProps) {
  const cards = [
    {
      label: "Base Markets",
      value: metrics.uniqueBases.toString(),
    },
    {
      label: "Total Pairs",
      value: metrics.totalPairs.toString(),
    },
    {
      label: "Top Similarity",
      value: formatSimilarity(metrics.topSimilarity),
    },
    {
      label: "Avg Similarity",
      value: formatSimilarity(metrics.avgSimilarity),
    },
  ]

  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      {cards.map((card) => (
        <Card key={card.label}>
          <CardContent className="p-6">
            <div className="text-sm font-medium text-muted-foreground">{card.label}</div>
            <div className="mt-2 text-3xl font-bold font-mono">
              {isLoading ? <span className="animate-pulse">--</span> : card.value}
            </div>
          </CardContent>
        </Card>
      ))}
      <Card className="lg:col-span-2">
        <CardContent className="p-6">
          <div className="text-sm font-medium text-muted-foreground">Most Common Category</div>
          <div className="mt-2 text-2xl font-semibold">
            {isLoading ? <span className="animate-pulse">--</span> : normalizeCategory(metrics.topCategory || undefined)}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
