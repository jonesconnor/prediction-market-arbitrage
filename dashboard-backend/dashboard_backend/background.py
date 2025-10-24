from __future__ import annotations

import asyncio
import logging
from typing import List

from .core.edge import compute_opportunities
from .core.models import Market
from .core.normalize import normalize_market
from .core.cache import MarketCache
from .ingress.clob import ClobMarketClient
from .ingress.gamma import GammaClient
from .store.redis_store import RedisStore

logger = logging.getLogger(__name__)


class GammaPoller:
    """Background task that polls the Gamma REST API and updates Redis."""

    def __init__(
        self,
        *,
        client: GammaClient,
        store: RedisStore,
        refresh_interval: int,
        market_limit: int,
        min_edge: float,
        min_liquidity: float,
        cache: MarketCache | None = None,
        subscription_queue: asyncio.Queue[str] | None = None,
        clob_client: ClobMarketClient | None = None,
    ) -> None:
        self._client = client
        self._store = store
        self._refresh_interval = max(refresh_interval, 1)
        self._market_limit = max(market_limit, 1)
        self._min_edge = min_edge
        self._min_liquidity = min_liquidity
        self._cache = cache
        self._subscription_queue = subscription_queue
        self._clob_client = clob_client
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="gamma-poller")

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop_event.set()
        await self._task
        self._task = None

    async def run_once(self) -> None:
        try:
            markets_payload = await self._client.fetch_markets(limit=self._market_limit)
            logger.info(
                "Fetched %s markets from Gamma (limit=%s)",
                len(markets_payload),
                self._market_limit,
            )
        except Exception:
            logger.exception("Failed to fetch markets from Gamma")
            return

        markets: List[Market] = []
        for raw_market in markets_payload:
            normalized = normalize_market(raw_market)
            if normalized is not None:
                markets.append(normalized)

        logger.info("Normalized %s markets", len(markets))

        if self._clob_client is not None:
            condition_ids = {market.condition_id for market in markets if market.condition_id}
            token_enrichments = 0
            try:
                token_map = await self._clob_client.fetch_tokens(condition_ids)
            except Exception:
                logger.exception("Failed to fetch tokens from CLOB")
                token_map = {}
            else:
                for market in markets:
                    if not market.condition_id:
                        continue
                    outcome_tokens = token_map.get(market.condition_id) or {}
                    if not outcome_tokens:
                        continue
                    for outcome in market.outcomes:
                        if outcome.token_id:
                            continue
                        token_id = outcome_tokens.get(outcome.name)
                        if token_id:
                            outcome.token_id = token_id
                            token_enrichments += 1
                if token_enrichments:
                    logger.debug("Enriched %s outcomes with CLOB token ids", token_enrichments)

        if self._cache is not None:
            try:
                sync_result = await self._cache.sync(markets)
            except Exception:
                logger.exception("Failed to sync markets into cache")
            else:
                logger.debug('Cache sync new assets=%s removed markets=%s',
                             len(sync_result.new_asset_ids),
                             len(sync_result.removed_market_ids))
                if self._subscription_queue and sync_result.new_asset_ids:
                    for asset_id in sync_result.new_asset_ids:
                        try:
                            self._subscription_queue.put_nowait(asset_id)
                        except asyncio.QueueFull:
                            logger.warning("Subscription queue full; awaiting enqueue")
                            await self._subscription_queue.put(asset_id)

        opportunities = compute_opportunities(
            markets,
            min_edge=self._min_edge,
            min_liquidity=self._min_liquidity,
        )

        logger.info(
            "Computed %s opportunities (min_edge=%s, min_liquidity=%s)",
            len(opportunities),
            self._min_edge,
            self._min_liquidity,
        )

        try:
            await self._store.sync_opportunities(opportunities)
        except Exception:
            logger.exception("Failed to sync opportunities to Redis")

    async def _run(self) -> None:
        logger.info(
            "Starting Gamma poller (interval=%ss, limit=%s)",
            self._refresh_interval,
            self._market_limit,
        )
        try:
            while not self._stop_event.is_set():
                await self.run_once()
                try:
                    await asyncio.wait_for(
                        self._stop_event.wait(),
                        timeout=self._refresh_interval,
                    )
                except asyncio.TimeoutError:
                    continue
        finally:
            logger.info("Gamma poller stopped")
