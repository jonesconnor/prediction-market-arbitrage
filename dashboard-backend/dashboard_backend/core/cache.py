from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from typing import Dict, Sequence

from .models import Market, Outcome

logger = logging.getLogger(__name__)


def _safe_float(value: object) -> float | None:
    try:
        if value in (None, ""):
            return None
        result = float(value)
        return result
    except (TypeError, ValueError):
        return None


def _best_from_book(levels: Sequence[dict]) -> tuple[float | None, float | None]:
    if not levels:
        return None, None
    top = levels[0]
    price = _safe_float(top.get("price"))
    size = _safe_float(top.get("size"))
    return price, size


@dataclass
class MarketSyncResult:
    new_asset_ids: set[str]
    removed_market_ids: set[str]


class MarketCache:
    """In-memory cache of markets keyed by market id and outcome asset id."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._markets: Dict[str, Market] = {}
        self._asset_index: Dict[str, tuple[str, int]] = {}

    async def sync(self, markets: Sequence[Market]) -> MarketSyncResult:
        async with self._lock:
            seen_market_ids: set[str] = set()
            new_asset_ids: set[str] = set()

            for market in markets:
                seen_market_ids.add(market.id)

                existing_market = self._markets.get(market.id)
                existing_asset_ids = {
                    outcome.token_id
                    for outcome in (existing_market.outcomes if existing_market else [])
                    if outcome.token_id
                }

                market_copy = market.model_copy(deep=True)
                self._markets[market.id] = market_copy

                current_asset_ids: set[str] = set()
                for index, outcome in enumerate(market_copy.outcomes):
                    token_id = outcome.token_id
                    if not token_id:
                        continue
                    current_asset_ids.add(token_id)
                    if token_id not in self._asset_index:
                        new_asset_ids.add(token_id)
                    self._asset_index[token_id] = (market.id, index)

                if existing_asset_ids:
                    stale_assets = existing_asset_ids.difference(current_asset_ids)
                    for asset_id in stale_assets:
                        if asset_id:
                            self._asset_index.pop(asset_id, None)

            removed_market_ids = set(self._markets).difference(seen_market_ids)
            for market_id in removed_market_ids:
                removed = self._markets.pop(market_id, None)
                if removed:
                    for outcome in removed.outcomes:
                        if outcome.token_id:
                            self._asset_index.pop(outcome.token_id, None)

            logger.debug("Market cache sync processed %s markets (%s new assets, %s removed markets)",
                         len(markets),
                         len(new_asset_ids),
                         len(removed_market_ids))

            return MarketSyncResult(
                new_asset_ids=new_asset_ids,
                removed_market_ids=removed_market_ids,
            )

    async def asset_ids(self) -> list[str]:
        async with self._lock:
            return list(self._asset_index.keys())

    async def markets(self) -> list[Market]:
        async with self._lock:
            return [market.model_copy(deep=True) for market in self._markets.values()]

    async def get_market(self, market_id: str) -> Market | None:
        async with self._lock:
            market = self._markets.get(market_id)
            return market.model_copy(deep=True) if market else None

    async def apply_book_snapshot(
        self,
        *,
        asset_id: str,
        bids: Sequence[dict],
        asks: Sequence[dict],
    ) -> Market | None:
        async with self._lock:
            asset_key = str(asset_id)
            reference = self._asset_index.get(asset_key)
            if not reference:
                return None

            market_id, index = reference
            market = self._markets.get(market_id)
            if not market:
                return None

            outcome = market.outcomes[index]
            best_bid, best_bid_size = _best_from_book(bids)
            best_ask, best_ask_size = _best_from_book(asks)

            if best_bid is not None and best_bid > 0:
                outcome.best_bid = best_bid
                outcome.best_bid_size = best_bid_size

            if best_ask is not None and best_ask > 0:
                outcome.best_ask = best_ask
                outcome.best_ask_size = best_ask_size
                outcome.price = best_ask

            market.outcomes[index] = outcome
            self._markets[market_id] = market
            return market.model_copy(deep=True)

    async def apply_price_changes(self, price_changes: Sequence[dict]) -> list[Market]:
        async with self._lock:
            updated: Dict[str, Market] = {}

            for change in price_changes:
                asset_id = change.get("asset_id") or change.get("assetId")
                if not asset_id:
                    continue

                asset_key = str(asset_id)
                reference = self._asset_index.get(asset_key)
                if not reference:
                    continue

                market_id, index = reference
                market = self._markets.get(market_id)
                if not market:
                    continue

                outcome = market.outcomes[index]

                best_bid = _safe_float(change.get("best_bid") or change.get("bestBid"))
                best_ask = _safe_float(change.get("best_ask") or change.get("bestAsk"))
                size = _safe_float(change.get("size"))

                if best_bid is not None and best_bid > 0:
                    outcome.best_bid = best_bid
                    if (change.get("side") or "").upper() == "BUY":
                        outcome.best_bid_size = size

                if best_ask is not None:
                    if best_ask > 0:
                        outcome.best_ask = best_ask
                        if (change.get("side") or "").upper() == "SELL":
                            outcome.best_ask_size = size
                        outcome.price = best_ask
                    else:
                        # No asks remaining at the top of book; keep prior price but clear metadata.
                        outcome.best_ask = None
                        outcome.best_ask_size = None

                market.outcomes[index] = outcome
                self._markets[market_id] = market
                updated[market_id] = market

            return [market.model_copy(deep=True) for market in updated.values()]
