from __future__ import annotations

import logging
import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from redis.asyncio import Redis

from .api.routes import router
from .background import GammaPoller
from .config import settings
from .core.cache import MarketCache
from .ingress.clob import ClobMarketClient
from .ingress.gamma import GammaClient
from .ingress.market_stream import MarketStream
from .store.redis_store import RedisStore

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    redis = Redis.from_url(settings.redis_url, decode_responses=True)
    store = RedisStore(redis, history_cap=settings.redis_history_cap)
    client = GammaClient(settings.gamma_url, timeout=settings.request_timeout)
    market_cache = MarketCache()
    clob_client = ClobMarketClient(settings.clob_host)
    subscription_queue: asyncio.Queue[str] = asyncio.Queue()
    poller = GammaPoller(
        client=client,
        store=store,
        refresh_interval=settings.rest_refresh_sec,
        market_limit=settings.gamma_limit,
        min_edge=settings.min_edge,
        min_liquidity=settings.min_liquidity,
        cache=market_cache,
        subscription_queue=subscription_queue,
        clob_client=clob_client,
    )

    market_stream = MarketStream(
        url=settings.clob_ws,
        cache=market_cache,
        store=store,
        subscription_queue=subscription_queue,
        min_edge=settings.min_edge,
        min_liquidity=settings.min_liquidity,
        ping_interval=settings.ws_ping_interval,
        subscribe_chunk_size=settings.ws_subscribe_chunk_size,
        reconnect_delay=settings.ws_reconnect_backoff,
        verify_ssl=settings.ws_verify_ssl,
    ) if settings.enable_ws_ingest else None

    app.state.settings = settings
    app.state.redis = redis
    app.state.store = store
    app.state.poller = poller
    app.state.market_cache = market_cache
    app.state.clob_client = clob_client
    app.state.market_stream = market_stream

    try:
        await redis.ping()
    except Exception:
        logger.exception("Failed to connect to Redis")
        raise

    logger.info(
        "Backend configuration loaded (gamma_url=%s, min_edge=%s, min_liquidity=%s, refresh_sec=%s, history_cap=%s)",
        settings.gamma_url,
        settings.min_edge,
        settings.min_liquidity,
        settings.rest_refresh_sec,
        settings.redis_history_cap,
    )

    await poller.run_once()

    if market_stream is not None:
        await market_stream.start()

    await poller.start()

    try:
        yield
    finally:
        await poller.stop()
        if market_stream is not None:
            await market_stream.stop()
        await client.close()
        await redis.close()


def create_app() -> FastAPI:
    app = FastAPI(title="Polymarket Arbitrage Backend", lifespan=lifespan)
    origins = [origin.strip() for origin in settings.cors_allow_origins.split(",") if origin.strip()]
    if not origins:
        origins = ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)
    return app


app = create_app()
