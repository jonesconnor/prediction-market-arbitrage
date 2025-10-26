from __future__ import annotations

import asyncio
import argparse
import hashlib
import logging
from collections.abc import Iterable
from datetime import datetime, timezone

import httpx
from redis.asyncio import Redis

from ..config import settings
from ..core.documents import MarketDocument, MarketEmbedding
from ..integrations.openai_client import OpenAIEmbeddingClient
from ..store.redis_store import RedisStore

logger = logging.getLogger(__name__)


def _market_to_text(market: MarketDocument) -> str:
    outcomes = ", ".join(market.outcomes)
    parts = [market.question]
    if market.category:
        parts.append(f"Category: {market.category}")
    if market.close_time:
        parts.append(f"Closes: {market.close_time.isoformat()}")
    parts.append(f"Outcomes: {outcomes}")
    return " | ".join(parts)


def _compute_signature(market: MarketDocument) -> str:
    text = _market_to_text(market)
    return hashlib.md5(text.encode("utf-8"), usedforsecurity=False).hexdigest()


async def _gather_markets(store: RedisStore) -> tuple[list[MarketDocument], dict[str, MarketEmbedding]]:
    catalog = await store.get_market_catalog()
    embeddings = await store.get_market_embeddings()
    return catalog, embeddings


def _select_pending(
    catalog: Iterable[MarketDocument],
    embeddings: dict[str, MarketEmbedding],
) -> list[MarketDocument]:
    pending: list[MarketDocument] = []
    for market in catalog:
        existing = embeddings.get(market.market_id)
        if existing is None:
            pending.append(market)
            continue
        # re-embed if market metadata changed (compare hash via metadata)
        existing_signature = existing.signature
        new_signature = _compute_signature(market)
        if existing_signature != new_signature:
            pending.append(market)
    return pending


async def run_embedding_worker() -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    store = RedisStore(redis, history_cap=settings.redis_history_cap)
    client = OpenAIEmbeddingClient()

    try:
        catalog, embeddings = await _gather_markets(store)
        pending = _select_pending(catalog, embeddings)
        batch_size = settings.embedding_batch_size
        if not pending:
            logger.info("Embedding worker found no pending markets")
            return

        logger.info("Embedding worker processing %s markets", len(pending))
        for i in range(0, len(pending), batch_size):
            chunk = pending[i : i + batch_size]
            texts = [_market_to_text(market) for market in chunk]
            try:
                vectors = await client.embed_texts(texts)
            except httpx.HTTPStatusError as exc:
                status = exc.response.status_code
                if status == 429:
                    logger.warning(
                        "Embedding worker skipping batch due to 429 (markets=%s)",
                        [market.market_id for market in chunk],
                    )
                    continue
                logger.exception("Embedding batch failed (status=%s); skipping", status)
                continue
            except Exception:
                logger.exception(
                    "Embedding batch errored; skipping markets %s",
                    [market.market_id for market in chunk],
                )
                continue

            if len(vectors) != len(chunk):
                logger.warning(
                    "Embedding worker mismatch (expected %s vectors, got %s)",
                    len(chunk),
                    len(vectors),
                )
                continue

            for market, vector in zip(chunk, vectors):
                embedding = MarketEmbedding(
                    marketId=market.market_id,
                    vector=vector,
                    model=settings.embedding_model,
                    updatedAt=datetime.now(timezone.utc),
                    signature=_compute_signature(market),
                )
                await store.store_market_embedding(embedding)

            if settings.embedding_batch_sleep_sec > 0:
                await asyncio.sleep(settings.embedding_batch_sleep_sec)
            logger.info("Embedding worker completed")
    finally:
        await client.close()
        await redis.aclose()


async def main() -> None:
    interval = settings.embedding_refresh_sec
    while True:
        try:
            await run_embedding_worker()
        except Exception:
            logger.exception("Embedding worker iteration failed")
        logger.info("Embedding worker sleeping for %ss", interval)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run market embedding worker")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously using EMBEDDING_REFRESH_SEC interval",
    )
    args = parser.parse_args()
    if args.loop:
        asyncio.run(main())
    else:
        asyncio.run(run_embedding_worker())
