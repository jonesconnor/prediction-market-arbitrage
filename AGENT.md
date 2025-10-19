# Polymarket Arbitrage Dashboard — AGENT.md

**Stack**: Python (FastAPI) backend + Next.js (App Router) frontend. Redis for caching & pub/sub. Deploy: Backend on Railway; Frontend on Vercel.

---

## 0) Goals & Non‑Goals
**Goals**
- Surface *intra‑market* underround opportunities (sum of outcome prices < 1) on Polymarket in near‑real‑time.
- Show edge %, basic liquidity, and links to market rules & order book.
- Provide tracking of opportunities within the dashboard itself for manual review and analysis throughout the day.
- Keep infra lightweight and cheap; easy to iterate.

**Non‑Goals (MVP)**
- Automated trading/placing orders.
- Cross‑platform arbitrage (Kalshi/Manifold, etc.).
- Alerts or notifications.

---

## Backend (FastAPI)

### 1) High-Level Architecture
```
+--------------------+         WS/HTTP          +------------------------+
|  Polymarket APIs   |  <-------------------->  |  Arb Backend (FastAPI) |
|  - Gamma (REST)    |                         |  - WS client to CLOB    |
|  - CLOB (WS/REST)  |                         |  - Poll fallback (REST) |
+--------------------+                         |  - Edge calc            |
                                               |  - Redis cache/pubsub  |
                                               +-----------+------------+
                                                           |
                                             SSE/WebSocket |
                                                           v
                                               +-----------+------------+
                                               |  Next.js Frontend      |
                                               +------------------------+
```

- **Data ingress**: Start with **Gamma REST** polling; add **CLOB WebSocket** later.
- **Processing**: Normalize markets → compute `sum_prices` and `edge=1-sum` → filter → write to Redis.
- **Egress**:
  - Backend emits updates to Redis pub/sub channel `ops:updates` and materializes current snapshot in a Redis key `ops:snapshot`.
  - Frontend connects to backend SSE which streams from Redis pub/sub.

---

### 2) Data Model (normalized)
```ts
Market = {
  id: string,
  question: string,
  url: string,
  rulesUrl?: string,
  category?: string,
  closeTime?: string,
  outcomes: { name: string, price: number }[],
  liquidity?: number,
}

Opportunity = {
  marketId: string,
  question: string,
  sumPrices: number,
  edge: number,
  numOutcomes: number,
  liquidity?: number,
  url: string,
  updatedAt: string,
}
```

**Redis keys/channels**
- `ops:snapshot` → JSON array of current `Opportunity` objects (trimmed by filters server-side).
- `ops:history:{marketId}` → time-series (zset) of `{timestamp -> edge}` for sparkline/history.
- `ops:updates` → pub/sub channel; each message is an `Opportunity` delta (upsert/remove).

---

### 3) Backend Design
**Key modules**
- `ingress/rest_client.py`: Periodic pull from **Gamma Markets** REST with `limit=N`.
- `core/normalize.py`: Normalize payloads → `Market`.
- `core/edge.py`: Compute `sumPrices`, `edge`, apply filters.
- `store/redis_store.py`: 
  - `set_snapshot(opportunities)` → writes `ops:snapshot`.
  - `append_history(marketId, ts, edge)` → writes to `ops:history:{marketId}` with capped length.
  - `publish_update(opportunity)` → pub/sub to `ops:updates`.
- `api/routes.py`:
  - `GET /healthz`
  - `GET /v1/opportunities` → returns `ops:snapshot` (optionally filtered by query params)
  - `GET /v1/stream` → SSE that bridges Redis pub/sub (`ops:updates`) to clients

**Config (env)**
```
PM_GAMMA_URL=https://gamma-api.polymarket.com/markets
PM_CLOB_WS=wss://clob.polymarket.com/ws
MIN_EDGE=0.01
MIN_LIQUIDITY=100
REST_REFRESH_SEC=30
REDIS_URL=redis://redis:6379/0
REDIS_HISTORY_CAP=2880   # e.g., 24h at 30s intervals
```

**Update loop**
1. On boot, fetch active markets → seed Redis snapshot & histories.
2. Every `REST_REFRESH_SEC`, refresh, recompute edges, upsert snapshot, publish deltas, and append to per-market history (capped).
3. (Later) WS deltas update the same flow with lower latency.

**Error handling**
- Retry with exponential backoff on REST and Redis connection.
- Circuit breaker to temporarily reduce refresh rate on repeated failures.

**Why Redis**
- Shared state for multiple backend instances on Railway.
- Durable-ish rolling history for sparklines and session summaries without a full SQL DB.
- Low-latency pub/sub for pushing updates to the SSE bridge.

---

## Frontend (Next.js)


### 1) UI Layout
- **Header filters:**  
  - Min edge (e.g. ≥ 1%)  
  - Min liquidity (e.g. ≥ $100)  
  - Category selector  
  - Active/closing-soon toggles
- **Opportunities table (sortable):**  
  - Market/question (link)  
  - Σ outcome prices  
  - Edge %  
  - Num outcomes  
  - Liquidity  
  - Time to close  
- **Details drawer:**  
  - Outcome prices and small bar visualization  
  - Recent tick history (tracked locally)  
  - Resolution rules snippet

### 2) Data Flow
- SSR loads initial snapshot from `GET /v1/opportunities`.
- Client opens `EventSource('/v1/stream')` to receive updates.
- UI updates table state with new opportunities.

### 3) Components
- `FiltersBar`: sliders/inputs for thresholds.
- `OpportunitiesTable`: sortable, filterable list.
- `MarketRowDrawer`: detail view with history graph.
- `LocalTracker`: keeps record of past opportunities to visualize what profit could have been captured.

### 4) Styling & UX
- Tailwind + shadcn/ui for a finance-dashboard look.
- Dark mode by default.
- Keep typography fixed-width for numeric alignment.
- Add toggle for “Show historical edges” to replay past data.

---

## Opportunity Logic
- `sumPrices = Σ outcomes[i].price`
- `edge = 1 - sumPrices`
- Display if `edge >= MIN_EDGE` and `liquidity >= MIN_LIQUIDITY`.
- `MIN_EDGE`: filter for meaningful gaps. Start at **0.01 (1%)**.
- `MIN_LIQUIDITY`: filter tiny markets. Start at **100**.

---

## Deployment Plan
- **Backend**: Deploy FastAPI container on Railway. Enable SSE endpoints. Add health checks.
- **Frontend**: Deploy Next.js on Vercel. Configure backend URL via env. Enable 10s cache on snapshot route.
- **Domains**: `arb.yourdomain.com` → Vercel; `api.arb.yourdomain.com` → backend.

---

## Testing & Validation
- Unit: normalization and edge calculations.
- Integration: SSE streaming and periodic refresh.
- Manual: Compare displayed edges vs. actual Polymarket order book.

---

## Roadmap
**Status**
- MVP shipped: REST ingest + edge calc + dashboard table + manual filters + SSE stream.
- Next focus shifts because intra-market underrounds are sparse; we need deeper data coverage and cross-market discovery to surface more opportunities.

**V1 — Data Depth & Reliability**
- Add WebSocket ingest (CLOB) to reduce latency and catch short-lived gaps.
- Increase market refresh breadth (dynamic limit/backfill) and add robustness tooling (retries, monitoring, logging).
- Instrument near-miss edges and raw snapshots to guide matcher development.

**V2 — Cross-Market Opportunity Discovery**
- Build candidate-matching pipeline (text/embedding similarity + deterministic outcome checks).
- Surface reviewable cross-market pairs before promoting to automated filtering.
- Extend dashboard filters to inspect clustered events and matcher confidence.

**V3 — Simulation & Analytics**
- Introduce tracking of past opportunities and simple paper-trading / theoretical PnL tooling.
- Enhance history visualizations (sparklines, trend overlays) using richer stored telemetry.

**V4 — Multi-Platform & Execution (Stretch)**
- Add additional venues (Manifold, Kalshi, etc.) behind feature flags.
- Explore order placement integration once Polymarket trading APIs allow safe execution paths.

---

**MVP success criteria:** The dashboard visually surfaces underrounds (≥ chosen threshold), updates within ~1–3s, and retains opportunity data for later review.
