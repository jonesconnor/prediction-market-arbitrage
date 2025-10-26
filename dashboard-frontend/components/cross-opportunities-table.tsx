"use client"

import Link from "next/link"

import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import type { CrossMatchRow } from "@/lib/types"
import { formatCloseDifference, formatSimilarity, normalizeCategory } from "@/lib/utils/opportunity"

import { Button } from "@/components/ui/button"

function formatTimestamp(value: string | undefined | null) {
  if (!value) return "--"
  try {
    return new Date(value).toLocaleString()
  } catch {
    return "--"
  }
}

type CrossOpportunitiesTableProps = {
  rows: CrossMatchRow[]
  isLoading: boolean
}

export function CrossOpportunitiesTable({ rows, isLoading }: CrossOpportunitiesTableProps) {
  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        Fetching cross-market opportunities...
      </div>
    )
  }

  if (rows.length === 0) {
    return (
      <div className="flex items-center justify-center py-12 text-sm text-muted-foreground">
        No cross-market pairs available in the latest run.
      </div>
    )
  }

  return (
    <Table>
      <TableHeader>
        <TableRow>
          <TableHead>Base Market</TableHead>
          <TableHead>Candidate Market</TableHead>
          <TableHead>Similarity</TableHead>
          <TableHead>Close Gap</TableHead>
          <TableHead>Updated</TableHead>
          <TableHead className="text-right">Links</TableHead>
        </TableRow>
      </TableHeader>
      <TableBody>
        {rows.map((row) => (
          <TableRow key={`${row.baseMarketId}-${row.candidate.marketId}`}>
            <TableCell className="max-w-xs align-top">
              <div className="font-medium line-clamp-2">{row.baseQuestion}</div>
              <div className="text-xs text-muted-foreground mt-1">
                {normalizeCategory(row.baseCategory || undefined)}
              </div>
            </TableCell>
            <TableCell className="max-w-xs align-top">
              <div className="font-medium line-clamp-2">{row.candidate.question}</div>
              <div className="text-xs text-muted-foreground mt-1">
                {normalizeCategory(row.candidate.category || undefined)}
              </div>
            </TableCell>
            <TableCell className="font-mono align-top">
              {formatSimilarity(row.candidate.similarity)}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground align-top">
              {formatCloseDifference(row.baseCloseTime, row.candidate.closeTime)}
            </TableCell>
            <TableCell className="text-sm text-muted-foreground align-top">
              {formatTimestamp(row.candidate.timestamp)}
            </TableCell>
            <TableCell className="text-right space-x-2 align-top">
              {row.baseUrl && (
                <Button asChild variant="ghost" size="sm">
                  <Link href={row.baseUrl} target="_blank" rel="noopener noreferrer">
                    Base
                  </Link>
                </Button>
              )}
              {row.candidate.url && (
                <Button asChild variant="ghost" size="sm">
                  <Link href={row.candidate.url} target="_blank" rel="noopener noreferrer">
                    Candidate
                  </Link>
                </Button>
              )}
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}
