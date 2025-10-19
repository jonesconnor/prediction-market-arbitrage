from __future__ import annotations

import json
from typing import AsyncGenerator

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import StreamingResponse

from ..config import settings
from ..core.models import Opportunity
from ..store.redis_store import RedisStore

router = APIRouter()


def get_store(request: Request) -> RedisStore:
    store = getattr(request.app.state, "store", None)
    if store is None:
        raise HTTPException(status_code=500, detail="Redis store is not available")
    return store


@router.get("/healthz")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/opportunities", response_model=list[Opportunity])
async def list_opportunities(
    request: Request,
    min_edge: float | None = None,
    min_liquidity: float | None = None,
    category: str | None = None,
    store: RedisStore = Depends(get_store),
) -> list[Opportunity]:
    snapshot = await store.get_snapshot()

    edge_threshold = min_edge if min_edge is not None else settings.min_edge
    liquidity_threshold = min_liquidity if min_liquidity is not None else settings.min_liquidity
    category_filter = category.lower() if category else None

    results: list[Opportunity] = []
    for item in snapshot:
        try:
            opportunity = Opportunity.model_validate(item)
        except Exception:
            continue

        if opportunity.edge < edge_threshold:
            continue
        liquidity_value = opportunity.liquidity or 0.0
        if liquidity_value < liquidity_threshold:
            continue
        if category_filter and (opportunity.category or "").lower() != category_filter:
            continue
        results.append(opportunity)

    return results


@router.get("/v1/history/{market_id}")
async def get_history(
    market_id: str,
    limit: int | None = Query(default=500, ge=1, le=5000),
    order: str = Query(default="asc"),
    store: RedisStore = Depends(get_store),
) -> list[dict[str, object]]:
    order_normalized = order.lower()
    if order_normalized not in {"asc", "desc"}:
        raise HTTPException(status_code=400, detail="order must be 'asc' or 'desc'")

    history = await store.get_history(
        market_id=market_id,
        limit=limit,
        order=order_normalized,
    )
    return history


@router.get("/v1/stream")
async def stream_updates(
    request: Request,
    store: RedisStore = Depends(get_store),
) -> StreamingResponse:
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        raise HTTPException(status_code=500, detail="Redis connection is not available")

    pubsub = redis.pubsub()
    await pubsub.subscribe(store.updates_channel)

    async def event_generator() -> AsyncGenerator[bytes, None]:
        try:
            # initial heartbeat so clients know stream is ready
            payload = json.dumps({"type": "ready", "status": "listening"})
            yield f"data: {payload}\n\n".encode("utf-8")

            async for message in pubsub.listen():
                if await request.is_disconnected():
                    break
                if message.get("type") != "message":
                    continue
                data = message.get("data")
                if data is None:
                    continue
                if isinstance(data, bytes):
                    data_str = data.decode("utf-8")
                else:
                    data_str = str(data)
                yield f"data: {data_str}\n\n".encode("utf-8")
        finally:
            await pubsub.unsubscribe(store.updates_channel)
            await pubsub.close()

    return StreamingResponse(event_generator(), media_type="text/event-stream")
