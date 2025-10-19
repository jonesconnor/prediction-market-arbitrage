"use client"

import { Card } from "@/components/ui/card"
import { Label } from "@/components/ui/label"
import { Slider } from "@/components/ui/slider"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import type { FilterState } from "@/lib/types"
import { formatPercent, formatCurrency } from "@/lib/utils/opportunity"

type FiltersBarProps = {
  filters: FilterState
  onChange: (filters: FilterState) => void
}

export function FiltersBar({ filters, onChange }: FiltersBarProps) {
  return (
    <Card className="p-6">
      <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wide text-muted-foreground">
            Min Edge: {formatPercent(filters.minEdge)}
          </Label>
          <Slider
            value={[filters.minEdge * 100]}
            onValueChange={([value]) => onChange({ ...filters, minEdge: value / 100 })}
            max={10}
            step={0.1}
            className="mt-2"
          />
        </div>

        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wide text-muted-foreground">
            Min Liquidity: {formatCurrency(filters.minLiquidity)}
          </Label>
          <Slider
            value={[filters.minLiquidity]}
            onValueChange={([value]) => onChange({ ...filters, minLiquidity: value })}
            max={10000}
            step={100}
            className="mt-2"
          />
        </div>

        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wide text-muted-foreground">Category</Label>
          <Select value={filters.category} onValueChange={(value) => onChange({ ...filters, category: value })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Categories</SelectItem>
              <SelectItem value="politics">Politics</SelectItem>
              <SelectItem value="sports">Sports</SelectItem>
              <SelectItem value="crypto">Crypto</SelectItem>
              <SelectItem value="us-current-affairs">US Current Affairs</SelectItem>
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-2">
          <Label className="text-xs uppercase tracking-wide text-muted-foreground">Sort By</Label>
          <Select value={filters.sortBy} onValueChange={(value: any) => onChange({ ...filters, sortBy: value })}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="edge">Edge %</SelectItem>
              <SelectItem value="profitAt1000">Profit @ $1k</SelectItem>
              <SelectItem value="liquidity">Liquidity</SelectItem>
              <SelectItem value="closeTime">Time to Close</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>
    </Card>
  )
}
