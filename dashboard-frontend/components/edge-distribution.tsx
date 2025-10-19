"use client"

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import type { OpportunityWithProfits } from "@/lib/types"
import { useMemo } from "react"

type EdgeDistributionProps = {
  opportunities: OpportunityWithProfits[]
}

export function EdgeDistribution({ opportunities }: EdgeDistributionProps) {
  const data = useMemo(() => {
    const buckets = [
      { name: "0-1%", min: 0, max: 0.01, count: 0 },
      { name: "1-2%", min: 0.01, max: 0.02, count: 0 },
      { name: "2-3%", min: 0.02, max: 0.03, count: 0 },
      { name: "3-5%", min: 0.03, max: 0.05, count: 0 },
      { name: "5%+", min: 0.05, max: Number.POSITIVE_INFINITY, count: 0 },
    ]

    opportunities.forEach((opp) => {
      const bucket = buckets.find((b) => opp.edge >= b.min && opp.edge < b.max)
      if (bucket) bucket.count++
    })

    return buckets
  }, [opportunities])

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg font-semibold">Edge Distribution</CardTitle>
      </CardHeader>
      <CardContent>
        <ChartContainer
          config={{
            count: {
              label: "Opportunities",
              color: "hsl(var(--chart-1))",
            },
          }}
          className="h-[200px]"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={data}>
              <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
              <XAxis dataKey="name" stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <YAxis stroke="hsl(var(--muted-foreground))" fontSize={12} />
              <ChartTooltip content={<ChartTooltipContent />} />
              <Bar dataKey="count" fill="hsl(var(--chart-1))" radius={[4, 4, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </ChartContainer>
      </CardContent>
    </Card>
  )
}
