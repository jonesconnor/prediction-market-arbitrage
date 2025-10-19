from __future__ import annotations

import asyncio
import logging
from typing import List

from .core.edge import compute_opportunities
from .core.models import Market, Opportunity
from .core.normalize import normalize_market
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
    ) -> None:
        self._client = client
        self._store = store
        self._refresh_interval = max(refresh_interval, 1)
        self._market_limit = max(market_limit, 1)
        self._min_edge = min_edge
        self._min_liquidity = min_liquidity
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
