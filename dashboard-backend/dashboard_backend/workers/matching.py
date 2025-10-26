from __future__ import annotations

import argparse
import asyncio
import logging
from collections import defaultdict
from datetime import UTC, datetime

import numpy as np
from redis.asyncio import Redis

from ..config import settings
from ..core.documents import MarketDocument, MarketEmbedding
from ..store.redis_store import RedisStore

logger = logging.getLogger(__name__)


def _build_vector_matrix(embeddings: dict[str, MarketEmbedding]) -> tuple[list[str], np.ndarray]:
    market_ids = []
    vectors = []
    for market_id, embedding in embeddings.items():
        market_ids.append(market_id)
        vectors.append(np.array(embedding.vector, dtype=np.float32))
    if not vectors:
        return [], np.empty((0,))
    matrix = np.stack(vectors, axis=0)
    norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    norms = np.where(norms == 0, 1, norms)
    matrix = matrix / norms
    return market_ids, matrix


def _filter_candidates(
    catalog: dict[str, MarketDocument],
    base_market: MarketDocument,
    candidate_market: MarketDocument,
) -> bool:
    if base_market.market_id == candidate_market.market_id:
        return False
    if base_market.condition_id and candidate_market.condition_id:
        if base_market.condition_id == candidate_market.condition_id:
            return False
    if len(base_market.outcomes) != len(candidate_market.outcomes):
        return False
    if base_market.category and candidate_market.category:
        if base_market.category.lower() != candidate_market.category.lower():
            return False
    if base_market.close_time and candidate_market.close_time:
        delta = abs((base_market.close_time - candidate_market.close_time).total_seconds())
        if delta > 7 * 24 * 3600:
            return False
    return True


def _prepare_catalog_map(markets: list[MarketDocument]) -> dict[str, MarketDocument]:
    return {market.market_id: market for market in markets}


def _top_matches(
    market_ids: list[str],
    similarity_matrix: np.ndarray,
    catalog_map: dict[str, MarketDocument],
) -> dict[str, list[dict]]:
    threshold = settings.similarity_threshold
    max_matches = settings.max_matches_per_market
    results: dict[str, list[dict]] = defaultdict(list)

    for idx, market_id in enumerate(market_ids):
        similarities = similarity_matrix[idx]
        sorted_idx = np.argsort(-similarities)
        base_market = catalog_map.get(market_id)
        if base_market is None:
            continue
        for candidate_idx in sorted_idx:
            if candidate_idx == idx:
                continue
            score = float(similarities[candidate_idx])
            if score < threshold:
                break
            candidate_id = market_ids[candidate_idx]
            candidate_market = catalog_map.get(candidate_id)
            if candidate_market is None:
                continue
            if not _filter_candidates(catalog_map, base_market, candidate_market):
                continue
            results[market_id].append(
                {
                    "marketId": candidate_id,
                    "similarity": score,
                    "question": candidate_market.question,
                    "category": candidate_market.category,
                    "closeTime": candidate_market.close_time.isoformat() if candidate_market.close_time else None,
                    "timestamp": datetime.now(UTC).isoformat(),
                }
            )
            if len(results[market_id]) >= max_matches:
                break
    return results


def _compute_similarity(matrix: np.ndarray) -> np.ndarray:
    if matrix.size == 0:
        return np.empty((0, 0))
    return np.matmul(matrix, matrix.T)


async def run_matching_worker() -> None:
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    store = RedisStore(redis, history_cap=settings.redis_history_cap)

    try:
        catalog = await store.get_market_catalog()
        embeddings = await store.get_market_embeddings()
        if not catalog or not embeddings:
            logger.info("Matching worker found empty catalog or embeddings")
            return

        catalog_map = _prepare_catalog_map(catalog)
        market_ids, matrix = _build_vector_matrix(embeddings)
        if not market_ids:
            logger.info("Matching worker found no embeddings to process")
            return

        similarity = _compute_similarity(matrix)
        matches = _top_matches(market_ids, similarity, catalog_map)
        if matches:
            await store.set_cross_matches(matches)
            logger.info("Matching worker stored matches for %s markets", len(matches))
        else:
            logger.info("Matching worker produced no matches above threshold")

    finally:
        await redis.aclose()


async def main() -> None:
    interval = settings.embedding_refresh_sec
    while True:
        try:
            await run_matching_worker()
        except Exception:
            logger.exception("Matching worker iteration failed")
        logger.info("Matching worker sleeping for %ss", interval)
        await asyncio.sleep(interval)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run cross-market matching worker")
    parser.add_argument(
        "--loop",
        action="store_true",
        help="Run continuously using EMBEDDING_REFRESH_SEC interval",
    )
    args = parser.parse_args()
    if args.loop:
        asyncio.run(main())
    else:
        asyncio.run(run_matching_worker())
