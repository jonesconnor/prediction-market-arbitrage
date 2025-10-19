"use client"

import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from "@/components/ui/table"
import { Card } from "@/components/ui/card"
import type { OpportunityWithProfits } from "@/lib/types"
import { formatCurrency, formatPercent, formatTimeToClose, normalizeCategory } from "@/lib/utils/opportunity"
import { ChevronRight } from "lucide-react"

type OpportunitiesTableProps = {
  opportunities: OpportunityWithProfits[]
  onSelectOpportunity: (marketId: string) => void
}

export function OpportunitiesTable({ opportunities, onSelectOpportunity }: OpportunitiesTableProps) {
  if (opportunities.length === 0) {
    return (
      <Card className="p-12">
        <div className="text-center text-muted-foreground">
          <p className="text-lg font-medium">No opportunities found</p>
          <p className="mt-2 text-sm">Adjust your filters or wait for new opportunities to appear</p>
        </div>
      </Card>
    )
  }

  return (
    <Card>
      <Table>
        <TableHeader>
          <TableRow>
            <TableHead className="w-[40%]">Market</TableHead>
            <TableHead className="text-right">Edge</TableHead>
            <TableHead className="text-right">Profit @ $1k</TableHead>
            <TableHead className="text-right">Liquidity</TableHead>
            <TableHead className="text-right">Closes</TableHead>
            <TableHead className="w-[50px]"></TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {opportunities.map((opp) => (
            <TableRow
              key={opp.marketId}
              className="cursor-pointer transition-colors hover:bg-accent/50"
              onClick={() => onSelectOpportunity(opp.marketId)}
            >
              <TableCell>
                <div className="flex flex-col gap-1">
                  <div className="font-medium text-balance leading-tight">{opp.question}</div>
                  <div className="text-xs text-muted-foreground">{normalizeCategory(opp.category)}</div>
                </div>
              </TableCell>
              <TableCell className="text-right">
                <span className="font-mono text-sm font-semibold text-success">{formatPercent(opp.edge)}</span>
              </TableCell>
              <TableCell className="text-right">
                <span className="font-mono text-sm font-semibold">{formatCurrency(opp.profitAt1000)}</span>
              </TableCell>
              <TableCell className="text-right">
                <span className="font-mono text-sm text-muted-foreground">
                  {opp.liquidity ? formatCurrency(opp.liquidity) : "N/A"}
                </span>
              </TableCell>
              <TableCell className="text-right">
                <span className="text-sm text-muted-foreground">{formatTimeToClose(opp.closeTime)}</span>
              </TableCell>
              <TableCell>
                <ChevronRight className="h-4 w-4 text-muted-foreground" />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </Card>
  )
}
