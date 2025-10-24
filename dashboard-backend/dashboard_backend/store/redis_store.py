from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Iterable, Sequence

from redis.asyncio import Redis

from ..core.models import Opportunity, OpportunityUpdate

logger = logging.getLogger(__name__)


def _history_key(market_id: str) -> str:
    return f"ops:history:{market_id}"


class RedisStore:
    """Helper around Redis persistence for opportunities and history."""

    snapshot_key = "ops:snapshot"
    updates_channel = "ops:updates"

    def __init__(self, client: Redis, *, history_cap: int) -> None:
        self._redis = client
        self._history_cap = max(history_cap, 0)
        self._lock = asyncio.Lock()
        self._snapshot_cache: Dict[str, dict] | None = None

    async def _load_snapshot_locked(self) -> Dict[str, dict]:
        if self._snapshot_cache is not None:
            return self._snapshot_cache

        data = await self._redis.get(self.snapshot_key)
        if not data:
            self._snapshot_cache = {}
            return self._snapshot_cache

        try:
            payload = json.loads(data)
        except json.JSONDecodeError:
            logger.warning("Failed to decode snapshot JSON; clearing cache.")
            self._snapshot_cache = {}
            return self._snapshot_cache

        cache: Dict[str, dict] = {}
        if isinstance(payload, list):
            for item in payload:
                if not isinstance(item, dict):
                    continue
                market_id = item.get("marketId")
                if market_id:
                    cache[str(market_id)] = item

        self._snapshot_cache = cache
        return self._snapshot_cache

    async def get_snapshot(self) -> list[dict]:
        async with self._lock:
            cache = await self._load_snapshot_locked()
            return list(cache.values())

    async def get_snapshot_models(self) -> list[Opportunity]:
        snapshot = await self.get_snapshot()
        results: list[Opportunity] = []
        for item in snapshot:
            try:
                results.append(Opportunity.model_validate(item))
            except Exception:
                logger.exception("Failed to parse snapshot item", extra={"item": item})
        return results

    async def sync_opportunities(self, opportunities: Sequence[Opportunity]) -> None:
        """Persist the latest opportunity set and publish deltas."""
        updates_to_publish: list[OpportunityUpdate] = []
        removed_count = 0
        payload: list[dict] = []

        async with self._lock:
            cache = await self._load_snapshot_locked()
            existing_keys = set(cache.keys())
            new_by_id = {opp.market_id: opp for opp in opportunities}

            for market_id, opportunity in new_by_id.items():
                serialized = opportunity.serialize()
                previous = cache.get(market_id)
                if previous != serialized:
                    updates_to_publish.append(
                        OpportunityUpdate(
                            type="upsert",
                            market_id=market_id,
                            opportunity=opportunity,
                        )
                    )
                cache[market_id] = serialized

            removed_ids = existing_keys.difference(new_by_id)
            removed_count = len(removed_ids)
            for market_id in removed_ids:
                cache.pop(market_id, None)
                updates_to_publish.append(
                    OpportunityUpdate(
                        type="remove",
                        market_id=market_id,
                        opportunity=None,
                    )
                )

            payload = list(cache.values())
            await self._redis.set(self.snapshot_key, json.dumps(payload))

        if updates_to_publish:
            await self.publish_updates(updates_to_publish)

        logger.info(
            "Snapshot synchronized with %s opportunities (%s updates, %s removals)",
            len(opportunities),
            len(updates_to_publish),
            removed_count,
        )

        await self._append_histories(opportunities)

    async def upsert_opportunity(self, opportunity: Opportunity) -> None:
        payload: list[dict] | None = None
        async with self._lock:
            cache = await self._load_snapshot_locked()
            serialized = opportunity.serialize()
            previous = cache.get(opportunity.market_id)
            if previous == serialized:
                return
            cache[opportunity.market_id] = serialized
            payload = list(cache.values())

        if payload is None:
            return

        await self._redis.set(self.snapshot_key, json.dumps(payload))
        await self.publish_updates(
            [
                OpportunityUpdate(
                    type="upsert",
                    market_id=opportunity.market_id,
                    opportunity=opportunity,
                )
            ]
        )
        await self.append_history(
            market_id=opportunity.market_id,
            timestamp=opportunity.updated_at,
            edge=opportunity.edge,
        )

    async def remove_opportunity(self, market_id: str) -> None:
        payload: list[dict] | None = None
        async with self._lock:
            cache = await self._load_snapshot_locked()
            if market_id not in cache:
                return
            cache.pop(market_id, None)
            payload = list(cache.values())

        if payload is None:
            return

        await self._redis.set(self.snapshot_key, json.dumps(payload))
        await self.publish_updates(
            [
                OpportunityUpdate(
                    type="remove",
                    market_id=market_id,
                    opportunity=None,
                )
            ]
        )

    async def publish_updates(self, updates: Iterable[OpportunityUpdate]) -> None:
        for update in updates:
            message = json.dumps(update.serialize())
            await self._redis.publish(self.updates_channel, message)

    async def _append_histories(self, opportunities: Iterable[Opportunity]) -> None:
        for opportunity in opportunities:
            await self.append_history(
                market_id=opportunity.market_id,
                timestamp=opportunity.updated_at,
                edge=opportunity.edge,
            )

    async def append_history(self, *, market_id: str, timestamp: datetime, edge: float) -> None:
        key = _history_key(market_id)
        score = timestamp.timestamp()
        member = json.dumps({"edge": edge, "updatedAt": timestamp.isoformat()})
        await self._redis.zadd(key, {member: score})

        if self._history_cap <= 0:
            return

        current_size = await self._redis.zcard(key)
        overflow = current_size - self._history_cap
        if overflow > 0:
            await self._redis.zremrangebyrank(key, 0, overflow - 1)

    async def get_history(
        self,
        *,
        market_id: str,
        limit: int | None = None,
        order: str = "asc",
    ) -> list[dict]:
        key = _history_key(market_id)
        if limit is not None and limit <= 0:
            return []

        if order == "desc":
            end = limit - 1 if limit is not None else -1
            entries = await self._redis.zrevrange(
                key,
                0,
                end,
                withscores=False,
            )
        else:
            end = limit - 1 if limit is not None else -1
            entries = await self._redis.zrange(
                key,
                0,
                end,
                withscores=False,
            )

        history: list[dict] = []
        for entry in entries:
            try:
                payload = json.loads(entry)
            except (TypeError, json.JSONDecodeError):
                logger.warning("Malformed history entry", extra={"market_id": market_id})
                continue
            if isinstance(payload, dict):
                history.append(payload)
        return history
