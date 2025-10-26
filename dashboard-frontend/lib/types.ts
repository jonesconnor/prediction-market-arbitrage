export type Opportunity = {
  marketId: string
  question: string
  sumPrices: number
  edge: number
  numOutcomes: number
  liquidity?: number
  url: string
  updatedAt: string
  outcomes?: Array<{
    name: string
    price: number
  }>
  category?: string
  closeTime?: string | null
}

export type OpportunityWithProfits = Opportunity & {
  profitAt10: number
  profitAt100: number
  profitAt1000: number
  profitAt10000: number
}

export type SSEMessage = {
  type: "upsert" | "remove"
  marketId: string
  opportunity: Opportunity | null
}

export type EdgeHistoryPoint = {
  edge: number
  updatedAt: string
}

export type CrossMatchCandidate = {
  marketId: string
  question: string
  similarity: number
  category?: string | null
  closeTime?: string | null
  url?: string | null
  timestamp: string
}

export type CrossMatchGroup = {
  baseMarketId: string
  baseQuestion: string
  baseCategory?: string | null
  baseCloseTime?: string | null
  baseUrl?: string | null
  matches: CrossMatchCandidate[]
}

export type CrossMatchRow = {
  baseMarketId: string
  baseQuestion: string
  baseCategory?: string | null
  baseCloseTime?: string | null
  baseUrl?: string | null
  candidate: CrossMatchCandidate
}

export type CrossMatchMetrics = {
  totalPairs: number
  uniqueBases: number
  avgSimilarity: number
  topSimilarity: number
  topCategory: string | null
}

export type FilterState = {
  minEdge: number
  maxEdge: number
  minLiquidity: number
  category: string
  sortBy: "edge" | "profitAt1000" | "liquidity" | "closeTime"
  sortOrder: "asc" | "desc"
}

export type ConnectionStatus = "connected" | "disconnected" | "reconnecting"
