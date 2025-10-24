from __future__ import annotations

import asyncio
import logging
from typing import Iterable

from py_clob_client.client import ClobClient
from py_clob_client.exceptions import PolyApiException

logger = logging.getLogger(__name__)


class ClobMarketClient:
    """Thin async wrapper over py-clob-client for fetching outcome token metadata."""

    def __init__(self, host: str, *, chain_id: int | None = None) -> None:
        self._client = ClobClient(host, chain_id=chain_id)
        self._cache: dict[str, dict[str, str]] = {}

    async def fetch_tokens(
        self,
        condition_ids: Iterable[str],
    ) -> dict[str, dict[str, str]]:
        """Return mapping of condition id -> outcome name -> token id."""

        remaining = {cid for cid in condition_ids if cid}
        if not remaining:
            return {}

        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._fetch_tokens_sync, remaining)

    def _fetch_tokens_sync(self, condition_ids: set[str]) -> dict[str, dict[str, str]]:
        token_map: dict[str, dict[str, str]] = {}

        remaining = {cid for cid in condition_ids if cid not in self._cache}
        for cid in condition_ids - remaining:
            cached = self._cache.get(cid)
            if cached:
                token_map[cid] = cached

        cursor: str | None = "MA=="
        seen_cursors: set[str] = set()

        while cursor and remaining:
            try:
                response = self._client.get_markets(next_cursor=cursor)
            except PolyApiException as exc:
                logger.warning(
                    "Failed to fetch CLOB markets page (cursor=%s, status=%s)",
                    cursor,
                    exc.status_code,
                )
                break
            except Exception:
                logger.exception("Unexpected error fetching CLOB markets (cursor=%s)", cursor)
                break

            markets = response.get("data") or []
            for market in markets:
                condition_id = str(market.get("condition_id") or "")
                if not condition_id or condition_id not in remaining:
                    continue

                tokens = market.get("tokens") or []
                mapping: dict[str, str] = {}
                for token in tokens:
                    outcome_name = token.get("outcome")
                    token_id = token.get("token_id")
                    if not outcome_name or not token_id:
                        continue
                    mapping[str(outcome_name)] = str(token_id)

                if mapping:
                    self._cache[condition_id] = mapping
                    token_map[condition_id] = mapping
                    remaining.discard(condition_id)

            next_cursor = response.get("next_cursor")
            if not next_cursor or next_cursor in seen_cursors or next_cursor == "LTE=":
                break
            seen_cursors.add(next_cursor)
            cursor = next_cursor

        if remaining:
            logger.debug(
                "CLOB token fetch completed with %s condition ids still missing",
                len(remaining),
            )

        return token_map


__all__ = ["ClobMarketClient"]
