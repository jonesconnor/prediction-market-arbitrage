from __future__ import annotations

import asyncio
import json
import logging
import ssl
from collections.abc import Sequence
from contextlib import suppress
from typing import Any

import websockets
from websockets.exceptions import ConnectionClosed

from ..core.cache import MarketCache
from ..core.edge import compute_opportunity
from ..core.models import Market
from ..store.redis_store import RedisStore

logger = logging.getLogger(__name__)


def _chunked(items: Sequence[str], size: int) -> list[list[str]]:
    if size <= 0:
        size = 1
    return [list(items[i : i + size]) for i in range(0, len(items), size)]


class MarketStream:
    """Client for the Polymarket CLOB market websocket feed."""

    def __init__(
        self,
        *,
        url: str,
        cache: MarketCache,
        store: RedisStore,
        subscription_queue: asyncio.Queue[str],
        min_edge: float,
        min_liquidity: float,
        ping_interval: float = 10.0,
        subscribe_chunk_size: int = 100,
        reconnect_delay: float = 5.0,
        verify_ssl: bool = True,
    ) -> None:
        self._url = url
        self._cache = cache
        self._store = store
        self._queue = subscription_queue
        self._min_edge = min_edge
        self._min_liquidity = min_liquidity
        self._ping_interval = max(ping_interval, 1.0)
        self._subscribe_chunk_size = max(subscribe_chunk_size, 1)
        self._reconnect_delay = max(reconnect_delay, 1.0)
        self._verify_ssl = verify_ssl
        self._task: asyncio.Task[None] | None = None
        self._stop_event = asyncio.Event()
        self._subscribed_assets: set[str] = set()

    async def start(self) -> None:
        if self._task and not self._task.done():
            return
        self._stop_event = asyncio.Event()
        self._task = asyncio.create_task(self._run(), name="market-stream")

    async def stop(self) -> None:
        if not self._task:
            return
        self._stop_event.set()
        self._task.cancel()
        with suppress(asyncio.CancelledError):
            await self._task
        self._task = None

    async def _run(self) -> None:
        backoff = self._reconnect_delay
        while not self._stop_event.is_set():
            try:
                await self._connect_and_consume()
                backoff = self._reconnect_delay
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Market stream disconnected unexpectedly")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)

    async def _connect_and_consume(self) -> None:
        logger.info("Connecting to Polymarket market websocket %s", self._url)
        self._subscribed_assets.clear()

        ssl_context = None
        if not self._verify_ssl:
            ssl_context = ssl._create_unverified_context()
            logger.warning("Market stream SSL verification disabled; do not use in production.")

        async with websockets.connect(
            self._url,
            ping_interval=None,
            close_timeout=10,
            open_timeout=10,
            max_size=None,
            ssl=ssl_context,
        ) as ws:
            await self._perform_initial_subscribe(ws)

            receiver = asyncio.create_task(self._receiver_loop(ws), name="market-stream-recv")
            pinger = asyncio.create_task(self._ping_loop(ws), name="market-stream-ping")
            subscriber = asyncio.create_task(
                self._subscription_loop(ws),
                name="market-stream-subscribe",
            )

            done, pending = await asyncio.wait(
                {receiver, pinger, subscriber},
                return_when=asyncio.FIRST_EXCEPTION,
            )

            for task in pending:
                task.cancel()
            for task in pending:
                with suppress(asyncio.CancelledError):
                    await task

            for task in done:
                with suppress(asyncio.CancelledError):
                    await task

    async def _receiver_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        async for raw in ws:
            if self._stop_event.is_set():
                break
            try:
                if isinstance(raw, bytes):
                    message = json.loads(raw.decode("utf-8"))
                else:
                    message = json.loads(raw)
            except json.JSONDecodeError:
                logger.warning("Dropping malformed websocket payload: %r", raw)
                continue

            await self._handle_message(message)

    async def _subscription_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        while not self._stop_event.is_set():
            asset_id = await self._queue.get()
            pending: set[str] = {str(asset_id)}

            while True:
                try:
                    next_id = self._queue.get_nowait()
                except asyncio.QueueEmpty:
                    break
                pending.add(str(next_id))

            new_ids = [asset for asset in pending if asset not in self._subscribed_assets]
            if not new_ids:
                continue

            await self._send_subscribe(ws, new_ids)

    async def _ping_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        while not self._stop_event.is_set():
            try:
                await asyncio.sleep(self._ping_interval)
                await ws.send("PING")
            except (ConnectionClosed, asyncio.CancelledError):
                break
            except Exception:
                logger.exception("Failed to send websocket ping")
                break

    async def _perform_initial_subscribe(self, ws: websockets.WebSocketClientProtocol) -> None:
        asset_ids = await self._cache.asset_ids()
        if not asset_ids:
            logger.info("Market stream has no asset ids to subscribe yet")
            return
        await self._send_subscribe(ws, asset_ids)

    async def _send_subscribe(self, ws: websockets.WebSocketClientProtocol, asset_ids: Sequence[str]) -> None:
        chunks = _chunked(list(asset_ids), self._subscribe_chunk_size)
        for chunk in chunks:
            payload = json.dumps({"assets_ids": chunk, "type": "market"})
            await ws.send(payload)
            self._subscribed_assets.update(chunk)
        logger.debug("Subscribed to %s asset ids", len(asset_ids))

    async def _handle_message(self, message: Any) -> None:
        if isinstance(message, list):
            for item in message:
                if isinstance(item, dict):
                    await self._process_event(item)
                else:
                    logger.debug("Ignoring non-dict item in websocket payload list: %s", item)
            return

        if not isinstance(message, dict):
            if message in {"PING", "PONG"}:
                logger.debug("Received websocket control frame %s", message)
                return
            logger.debug("Ignoring unexpected websocket payload type: %s", type(message))
            return

        await self._process_event(message)

    async def _process_event(self, message: dict[str, Any]) -> None:
        event_type = message.get("event_type") or message.get("type")
        if event_type == "book":
            asset_id = message.get("asset_id") or message.get("assetId")
            if not asset_id:
                logger.debug("Book event missing asset id: %s", message)
                return
            bids = message.get("bids") or []
            asks = message.get("asks") or []
            updated_market = await self._cache.apply_book_snapshot(
                asset_id=str(asset_id),
                bids=bids,
                asks=asks,
            )
            if updated_market:
                await self._process_market(updated_market)
        elif event_type == "price_change":
            price_changes = message.get("price_changes") or message.get("priceChanges") or []
            if not price_changes:
                return
            markets = await self._cache.apply_price_changes(price_changes)
            for market in markets:
                await self._process_market(market)
        elif event_type == "last_trade_price":
            # Trade events are informational for now; no direct state mutation required.
            logger.debug(
                "Trade event received for market %s at price %s",
                message.get("market"),
                message.get("price"),
            )
        elif event_type == "tick_size_change":
            logger.debug("Tick size change event received: %s", message)
        else:
            logger.debug("Unhandled websocket event: %s", message)

    async def _process_market(self, market: Market) -> None:
        try:
            opportunity = compute_opportunity(
                market,
                min_edge=self._min_edge,
                min_liquidity=self._min_liquidity,
            )
        except Exception:
            logger.exception("Failed to compute opportunity for market %s", market.id)
            return

        if opportunity:
            try:
                await self._store.upsert_opportunity(opportunity)
            except Exception:
                logger.exception("Failed to upsert opportunity for market %s", market.id)
        else:
            try:
                await self._store.remove_opportunity(market.id)
            except Exception:
                logger.exception("Failed to remove opportunity for market %s", market.id)
