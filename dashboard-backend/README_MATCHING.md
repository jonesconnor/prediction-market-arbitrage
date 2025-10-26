# Cross-Market Discovery Pipeline

This document explains the new cross-market opportunity discovery flow: how data moves through the system, how to operate the workers, and what to expect in the API/front-end.

---

## 1. Architectural Overview

```
Gamma + CLOB Poller  --->  MarketCatalog (Redis)  --->  Embedding Worker  --->  embeddings hash
                           |                                             \
                           |                                              ->  Matching Worker  --->  matches hash
                           v
                        Opportunity Snapshot  --->  /v1/opportunities & /v1/stream
```

1. **Gamma/CLOB Poller** (`GammaPoller`)
   - Fetches `PM_GAMMA_LIMIT` markets, enriches them with CLOB token IDs, computes intra-market opportunities, and writes:
     - `ops:snapshot` (opportunity list) + `ops:updates` pub/sub (existing behavior).
     - `markets:catalog` Redis hash (new) with normalized `MarketDocument` entries.

2. **Embedding Worker** (`dashboard_backend/workers/embedding.py`)
   - Reads the market catalog, diff-ing based on question/outcome metadata hash (`signature`).
   - Uses OpenAI `text-embedding-3-small` to embed new/changed markets in batches of `EMBEDDING_BATCH_SIZE` (default 32).
   - Stores vectors + model metadata in `markets:embeddings` Redis hash.

3. **Matching Worker** (`dashboard_backend/workers/matching.py`)
   - Loads catalog + embeddings, normalizes vectors with NumPy, computes cosine similarities.
   - Applies structural filters (matching outcome count, avoid same condition, category equality, close-time within ~7 days).
   - Writes top `MAX_MATCHES_PER_MARKET` candidates per market that exceed `SIMILARITY_THRESHOLD` into `markets:cross_matches` hash.

4. **API Surface**
   - `/v1/cross-opportunities`: returns stored match lists (optionally filtered via `market_id` and limited per market).
   - Existing endpoints (`/v1/opportunities`, `/v1/history`, `/v1/stream`) continue unchanged; the new matches are additive.

---

## 2. Runtime Controls & Environment Variables

| Setting | Default | Purpose |
|---------|---------|---------|
| `PM_GAMMA_LIMIT` | 200 | Markets fetched per poll (scope of catalog + opportunities). |
| `EMBEDDING_MODEL` | `text-embedding-3-small` | OpenAI model for embeddings. |
| `EMBEDDING_BATCH_SIZE` | 32 | Markets embedded per request. |
| `EMBEDDING_REFRESH_SEC` | 900 (15 min) | Sleep interval for embedding & matching `--loop` workers. |
| `EMBEDDING_BATCH_SLEEP_SEC` | 0 | Optional pause between embedding batches to ease API throttling. |
| `SIMILARITY_THRESHOLD` | 0.75 | Minimum cosine similarity to consider a match. |
| `MAX_MATCHES_PER_MARKET` | 10 | Cap on matches stored per market. |
| `OPENAI_API_KEY` | *(required)* | API key for embedding worker. |
| `ENABLE_WS_INGEST` | True | Controls websocket ingest (leave on for live book updates). |

*Tip:* Remove the placeholder `OPENAI_API_KEY=""` from `.env.local` if you want the shell-exported key to be picked up automatically.

---

## 3. Operating the Workers

### Embedding Worker

Run once:
```bash
OPENAI_API_KEY=... PYTHONPATH=dashboard-backend \
  ./dashboard-backend/.venv/bin/python -m dashboard_backend.workers.embedding
```
Loop (continuous refresh):
```bash
OPENAI_API_KEY=... PYTHONPATH=dashboard-backend \
  ./dashboard-backend/.venv/bin/python -m dashboard_backend.workers.embedding --loop
```

Add `EMBEDDING_BATCH_SIZE` and optional `EMBEDDING_BATCH_SLEEP_SEC` overrides inline if you hit rate limits, e.g. `EMBEDDING_BATCH_SIZE=16 EMBEDDING_BATCH_SLEEP_SEC=1 ...`.

### Matching Worker

Run once:
```bash
PYTHONPATH=dashboard-backend \
  ./dashboard-backend/.venv/bin/python -m dashboard_backend.workers.matching
```

Loop:
```bash
PYTHONPATH=dashboard-backend \
  ./dashboard-backend/.venv/bin/python -m dashboard_backend.workers.matching --loop
```

The matching worker should follow the embedding worker (embed first, then match). Continuous mode keeps them in sync every `EMBEDDING_REFRESH_SEC` seconds.

### Observability

- **Redis Keys:**
  - `markets:catalog` – hash of `marketId -> MarketDocument` JSON.
  - `markets:embeddings` – hash of `marketId -> MarketEmbedding` JSON (vector + signature).
  - `markets:cross_matches` – hash of `marketId -> [match, ...]` arrays.
- **Logs:** Both workers log counts (pending markets, matches stored) and warn on API failures.
- **API Check:** `curl 'http://localhost:8000/v1/cross-opportunities?limit=5'`

---

## 4. Choosing Market Coverage

- `PM_GAMMA_LIMIT` controls how many markets the system maintains. Keeping it at 500 means you’re embedding exactly those 500 markets repeatedly; it will not automatically discover new ones once the set is stable.
- Possible strategies:
  1. **Global Scan (default):** Keep `PM_GAMMA_LIMIT` moderately high (e.g., 500–1000) to sample the most active markets platform-wide.
  2. **Topic-Specific:** Add filtering in `GammaClient` (e.g., by category) or post-filter the catalog before embedding to focus on sports/politics/etc. This reduces embedding cost and surfaces more relevant cross-market pairs.
  3. **Rolling windows:** Periodically rotate the set by fetching different offsets/categories, caching embeddings so repeated markets are inexpensive.

Embedding cost is proportional to new/changed markets. At 500 markets every 15 min the daily cost is ~$0.24. If that’s too high, lower the refresh frequency (e.g. every hour) or reduce the catalog size.

---

## 5. Frontend Integration Plan

The new API adds cross-market data alongside the existing intra-market opportunities; it doesn’t replace `/v1/opportunities`. Suggested UI changes:
1. **Discovery View:** Pull `/v1/cross-opportunities` to list candidate pairs. Each item already contains `marketId`, `question`, similarity, category, close time, and timestamp. Use the catalog (`markets:catalog`) if you need additional context (URL, liquidity) – add a backend helper if you plan to display more fields.
2. **Detail Drawer:** When users click a candidate pair, fetch each market’s standard opportunity data (existing `/v1/opportunities` entry, or a new `/v1/market/{id}` route if needed).
3. **Filtering:** Consider exposing query params via the new endpoint (`market_id` filter already exists). You can add more (e.g. `category`) or post-filter client-side.
4. **State Management:** Matches are not streamed yet; refresh periodically (5–10 min) or add SSE in Phase 5 if needed.

The existing frontend calls remain valid. You’re simply adding a new fetch for cross-market suggestions and a new view to surface them.

---

## 6. Testing Checklist

1. `PM_GAMMA_LIMIT=50` for quick smoke-tests.
2. Run embedding + matching workers once (use stub or live key).
3. `redis-cli HLEN markets:embeddings` and `HLEN markets:cross_matches` should be >0.
4. `curl 'http://localhost:8000/v1/cross-opportunities?limit=5'` -> JSON array of base markets and their matches.
5. Frontend: add an API call to display the pairs; ensure fallback when matches are empty.

---

## 7. Future Enhancements

- Stream matches via Redis pub/sub to avoid polling.
- Add more structured metadata (price deltas, liquidity comparisons) to match entries.
- Persist embeddings in a vector store with approximate nearest-neighbor search for scale.
- Explore topic-specific workers or integrate an LLM reranker cautiously (as a secondary validator).
