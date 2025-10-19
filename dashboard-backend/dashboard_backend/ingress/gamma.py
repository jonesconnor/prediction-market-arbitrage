from __future__ import annotations

from typing import Any, Dict, List

import httpx


class GammaClient:
    """Async HTTP client for interacting with the Polymarket Gamma REST API."""

    def __init__(self, base_url: str, *, timeout: float = 10.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._client = httpx.AsyncClient(timeout=timeout)

    async def fetch_markets(self, *, limit: int) -> List[Dict[str, Any]]:
        """Fetch active markets with a configurable limit."""

        params = {
            "limit": limit,
            "active": "true",
            "closed": "false",
            "archived": "false",
        }
        response = await self._client.get(self._base_url, params=params)
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, list):
            return payload

        if isinstance(payload, dict):
            if isinstance(payload.get("data"), list):
                return payload["data"]  # type: ignore[index]
            if isinstance(payload.get("markets"), list):
                return payload["markets"]  # type: ignore[index]

        return []

    async def close(self) -> None:
        await self._client.aclose()

    async def __aenter__(self) -> "GammaClient":
        return self

    async def __aexit__(self, *exc_info: Any) -> None:
        await self.close()
