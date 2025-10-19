"use client"

import { useEffect, useState } from "react"
import { Sheet, SheetContent, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Button } from "@/components/ui/button"
import { LineChart, Line, XAxis, YAxis, CartesianGrid, ResponsiveContainer } from "recharts"
import { ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { ExternalLink, Loader2 } from "lucide-react"
import type { OpportunityWithProfits, EdgeHistoryPoint } from "@/lib/types"
import { formatCurrency, formatPercent, normalizeCategory } from "@/lib/utils/opportunity"
import { getMarketHistory } from "@/lib/api"

type MarketDetailDrawerProps = {
  opportunity: OpportunityWithProfits | null
  open: boolean
  onClose: () => void
}

export function MarketDetailDrawer({ opportunity, open, onClose }: MarketDetailDrawerProps) {
  const [stake, setStake] = useState(1000)
  const [history, setHistory] = useState<EdgeHistoryPoint[]>([])
  const [loadingHistory, setLoadingHistory] = useState(false)

  useEffect(() => {
    if (opportunity && open) {
      setLoadingHistory(true)
      getMarketHistory(opportunity.marketId, 100)
        .then(setHistory)
        .catch((err) => {
          console.error("[v0] Failed to load history:", err)
          setHistory([])
        })
        .finally(() => setLoadingHistory(false))
    }
  }, [opportunity, open])

  if (!opportunity) return null

  const profit = opportunity.edge * stake
  const roi = opportunity.edge

  return (
    <Sheet open={open} onOpenChange={onClose}>
      <SheetContent className="w-full sm:max-w-xl overflow-y-auto">
        <SheetHeader>
          <SheetTitle className="text-balance leading-tight pr-8">{opportunity.question}</SheetTitle>
        </SheetHeader>

        <div className="mt-6 space-y-6">
          <div className="flex items-center gap-4 text-sm">
            <div>
              <span className="text-muted-foreground">Edge: </span>
              <span className="font-mono font-semibold text-success">{formatPercent(opportunity.edge)}</span>
            </div>
            <div className="h-4 w-px bg-border" />
            <div>
              <span className="text-muted-foreground">Liquidity: </span>
              <span className="font-mono font-semibold">
                {opportunity.liquidity ? formatCurrency(opportunity.liquidity) : "N/A"}
              </span>
            </div>
          </div>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Profit Calculator</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="stake">Stake Amount</Label>
                <Input
                  id="stake"
                  type="number"
                  value={stake}
                  onChange={(e) => setStake(Number(e.target.value))}
                  className="font-mono"
                />
              </div>
              <div className="rounded-lg bg-success/10 p-4 border border-success/20">
                <div className="text-sm text-muted-foreground">Expected Profit</div>
                <div className="mt-1 text-2xl font-bold font-mono text-success">{formatCurrency(profit)}</div>
                <div className="mt-1 text-sm text-muted-foreground">{formatPercent(roi)} ROI</div>
              </div>
            </CardContent>
          </Card>

          {opportunity.outcomes && opportunity.outcomes.length > 0 && (
            <Card>
              <CardHeader>
                <CardTitle className="text-base">Outcome Prices</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {opportunity.outcomes.map((outcome, idx) => (
                  <div key={idx} className="space-y-1">
                    <div className="flex justify-between text-sm">
                      <span className="font-medium">{outcome.name}</span>
                      <span className="font-mono text-muted-foreground">{formatCurrency(outcome.price)}</span>
                    </div>
                    <div className="h-2 w-full rounded-full bg-secondary overflow-hidden">
                      <div className="h-full bg-primary transition-all" style={{ width: `${outcome.price * 100}%` }} />
                    </div>
                  </div>
                ))}
                <div className="pt-2 border-t">
                  <div className="flex justify-between text-sm">
                    <span className="font-medium">Sum</span>
                    <span className="font-mono font-semibold">{formatCurrency(opportunity.sumPrices)}</span>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">
                    {formatPercent(1 - opportunity.sumPrices)} underround
                  </div>
                </div>
              </CardContent>
            </Card>
          )}

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Edge History (24h)</CardTitle>
            </CardHeader>
            <CardContent>
              {loadingHistory ? (
                <div className="flex items-center justify-center h-[150px]">
                  <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
                </div>
              ) : history.length > 0 ? (
                <ChartContainer
                  config={{
                    edge: {
                      label: "Edge",
                      color: "hsl(var(--chart-2))",
                    },
                  }}
                  className="h-[150px]"
                >
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={history}>
                      <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border))" />
                      <XAxis
                        dataKey="updatedAt"
                        stroke="hsl(var(--muted-foreground))"
                        fontSize={10}
                        tickFormatter={(value) =>
                          new Date(value).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                        }
                      />
                      <YAxis
                        stroke="hsl(var(--muted-foreground))"
                        fontSize={10}
                        tickFormatter={(value) => `${(value * 100).toFixed(1)}%`}
                      />
                      <ChartTooltip
                        content={<ChartTooltipContent />}
                        labelFormatter={(value) => new Date(value).toLocaleString()}
                      />
                      <Line type="monotone" dataKey="edge" stroke="hsl(var(--chart-2))" strokeWidth={2} dot={false} />
                    </LineChart>
                  </ResponsiveContainer>
                </ChartContainer>
              ) : (
                <div className="flex items-center justify-center h-[150px] text-sm text-muted-foreground">
                  No history data available
                </div>
              )}
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle className="text-base">Market Details</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 text-sm">
              <div className="flex justify-between">
                <span className="text-muted-foreground">Category</span>
                <span className="font-medium">{normalizeCategory(opportunity.category)}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-muted-foreground">Outcomes</span>
                <span className="font-medium">{opportunity.numOutcomes}</span>
              </div>
              {opportunity.closeTime && (
                <div className="flex justify-between">
                  <span className="text-muted-foreground">Closes</span>
                  <span className="font-medium">{new Date(opportunity.closeTime).toLocaleString()}</span>
                </div>
              )}
              <div className="pt-2">
                <Button asChild variant="outline" className="w-full bg-transparent">
                  <a href={opportunity.url} target="_blank" rel="noopener noreferrer">
                    View on Polymarket
                    <ExternalLink className="ml-2 h-4 w-4" />
                  </a>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </SheetContent>
    </Sheet>
  )
}
