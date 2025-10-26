from __future__ import annotations

import asyncio
import logging
from typing import Iterable

import os

import httpx

from ..config import settings

logger = logging.getLogger(__name__)


class OpenAIEmbeddingClient:
    """Thin wrapper around OpenAI's embedding endpoint with async batching."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        model: str | None = None,
        timeout: float = 30.0,
        max_retries: int = 3,
    ) -> None:
        resolved_key = api_key or getattr(settings, "openai_api_key", None)
        if not resolved_key:
            resolved_key = os.environ.get("OPENAI_API_KEY")
        if not resolved_key:
            raise RuntimeError("OPENAI_API_KEY is required for embedding generation")
        self._api_key = resolved_key
        self._model = model or settings.embedding_model
        self._timeout = timeout
        self._max_retries = max(max_retries, 0)
        self._client = httpx.AsyncClient(
            base_url="https://api.openai.com/v1",
            timeout=self._timeout,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    async def close(self) -> None:
        await self._client.aclose()

    async def embed_texts(self, texts: Iterable[str]) -> list[list[float]]:
        payload = {
            "model": self._model,
            "input": list(texts),
        }
        attempt = 0
        backoff = 1.0
        while True:
            try:
                response = await self._client.post("/embeddings", json=payload)
                response.raise_for_status()
                data = response.json()
                vectors = [item["embedding"] for item in data.get("data", [])]
                return vectors
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429:
                    retry_after = exc.response.headers.get("Retry-After")
                    if retry_after:
                        try:
                            backoff = max(backoff, float(retry_after))
                        except ValueError:
                            backoff = backoff
                    headers = exc.response.headers
                    logger.warning(
                        "Embedding 429: remaining_requests=%s, remaining_tokens=%s, reset_requests=%s, reset_tokens=%s",
                        headers.get("x-ratelimit-remaining-requests"),
                        headers.get("x-ratelimit-remaining-tokens"),
                        headers.get("x-ratelimit-reset-requests"),
                        headers.get("x-ratelimit-reset-tokens"),
                    )
                if status in {429, 500, 502, 503} and attempt < self._max_retries:
                    attempt += 1
                    logger.warning(
                        "Embedding request failed (status=%s); retrying in %.1fs",
                        status,
                        backoff,
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    continue
                logger.exception(
                    "Embedding request failed permanently (status=%s)", status
                )
                raise
            except Exception:
                if attempt < self._max_retries:
                    attempt += 1
                    logger.exception(
                        "Embedding request errored; retrying in %.1fs", backoff
                    )
                    await asyncio.sleep(backoff)
                    backoff = min(backoff * 2, 60)
                    continue
                raise


__all__ = ["OpenAIEmbeddingClient"]
