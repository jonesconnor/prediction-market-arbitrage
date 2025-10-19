"use client"

import { Card, CardContent } from "@/components/ui/card"
import { formatCurrency, formatPercent } from "@/lib/utils/opportunity"

type LiveMetricsProps = {
  count: number
  avgEdge: number
  totalLiquidity: number
  bestEdge: number
}

export function LiveMetrics({ count, avgEdge, totalLiquidity, bestEdge }: LiveMetricsProps) {
  return (
    <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
      <Card>
        <CardContent className="p-6">
          <div className="text-sm font-medium text-muted-foreground">Active Opportunities</div>
          <div className="mt-2 text-3xl font-bold font-mono">{count}</div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="text-sm font-medium text-muted-foreground">Average Edge</div>
          <div className="mt-2 text-3xl font-bold font-mono text-primary">{formatPercent(avgEdge)}</div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="text-sm font-medium text-muted-foreground">Total Liquidity</div>
          <div className="mt-2 text-3xl font-bold font-mono">{formatCurrency(totalLiquidity)}</div>
        </CardContent>
      </Card>

      <Card>
        <CardContent className="p-6">
          <div className="text-sm font-medium text-muted-foreground">Best Edge</div>
          <div className="mt-2 text-3xl font-bold font-mono text-success">{formatPercent(bestEdge)}</div>
        </CardContent>
      </Card>
    </div>
  )
}
