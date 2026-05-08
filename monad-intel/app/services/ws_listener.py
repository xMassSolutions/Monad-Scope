"""WebSocket listener for new Monad blocks.

- Default subscription is `newHeads` (Voted, reorg-free).
- `monadNewHeads` is selectable via `MONAD_WS_SUBSCRIPTION` env (Proposed, speculative).
- Reconnects with exponential backoff + jitter.
- Deduplicates blocks already in the queue.
- Persists the high-water-mark block; on reconnect, gaps trigger a sync catch-up.
- Bounded queue applies backpressure to consumers.
"""

from __future__ import annotations

import asyncio
import json
import random
from typing import Any, Awaitable, Callable

import websockets
from websockets.client import WebSocketClientProtocol

from app.config import get_settings
from app.logging import get_logger
from app.services.rpc import JsonRpcClient
from app.utils.time import parse_hex_qty

log = get_logger(__name__)


BlockHandler = Callable[[int], Awaitable[None]]
"""A coroutine called with the block number each time a header arrives.
The handler is responsible for processing the block end-to-end."""


class WsListener:
    def __init__(
        self,
        on_block: BlockHandler,
        rpc: JsonRpcClient,
        ws_url: str | None = None,
        subscription: str | None = None,
        queue_size: int | None = None,
    ) -> None:
        s = get_settings()
        self._on_block = on_block
        self._rpc = rpc
        self._url = ws_url or s.monad_rpc_ws
        self._sub = subscription or s.monad_ws_subscription
        self._q: asyncio.Queue[int] = asyncio.Queue(maxsize=queue_size or s.block_queue_maxsize)
        self._seen: set[int] = set()
        self._last_processed: int | None = None
        self._running = False
        self._sub_id: str | None = None

    @property
    def last_processed(self) -> int | None:
        return self._last_processed

    def set_last_processed(self, n: int) -> None:
        self._last_processed = n

    async def _subscribe(self, ws: WebSocketClientProtocol) -> None:
        req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "eth_subscribe",
            "params": [self._sub],
        }
        await ws.send(json.dumps(req))
        # Discard responses until we see the subscription id.
        while True:
            raw = await ws.recv()
            msg = json.loads(raw)
            if msg.get("id") == 1 and "result" in msg:
                self._sub_id = msg["result"]
                log.info("ws.subscribed", sub=self._sub, id=self._sub_id)
                return
            # Unexpected pre-subscription messages: ignore.

    async def _handle_message(self, msg: dict[str, Any]) -> None:
        if msg.get("method") != "eth_subscription":
            return
        params = msg.get("params") or {}
        result = params.get("result") or {}
        number = parse_hex_qty(result.get("number"))
        if number is None:
            return
        if number in self._seen:
            return
        self._seen.add(number)
        # Trim memory.
        if len(self._seen) > 1024:
            keep = sorted(self._seen)[-512:]
            self._seen = set(keep)
        try:
            self._q.put_nowait(number)
        except asyncio.QueueFull:
            log.warning("ws.queue_full", number=number)
            # Backpressure: block until consumer drains.
            await self._q.put(number)

    async def _catch_up(self, head: int) -> None:
        """If we know our last_processed and there's a gap, enqueue the gap."""
        if self._last_processed is None:
            return
        first_missing = self._last_processed + 1
        if first_missing > head:
            return
        log.info("ws.catchup", from_block=first_missing, to_block=head)
        for n in range(first_missing, head + 1):
            if n in self._seen:
                continue
            self._seen.add(n)
            await self._q.put(n)

    async def _consumer(self) -> None:
        while self._running:
            n = await self._q.get()
            try:
                await self._on_block(n)
                self._last_processed = max(self._last_processed or 0, n)
            except Exception as e:  # noqa: BLE001
                log.exception("ws.consumer.error", number=n, err=str(e))
            finally:
                self._q.task_done()

    async def run(self) -> None:
        self._running = True
        consumer_task = asyncio.create_task(self._consumer())
        try:
            backoff = 0.5
            while self._running:
                try:
                    log.info("ws.connect", url=self._url)
                    async with websockets.connect(
                        self._url, ping_interval=20, ping_timeout=20, max_queue=1024
                    ) as ws:
                        await self._subscribe(ws)
                        backoff = 0.5  # reset on successful connect
                        # Try to catch up against current head before processing live.
                        try:
                            head = await self._rpc.block_number()
                            await self._catch_up(head)
                        except Exception as e:  # noqa: BLE001
                            log.warning("ws.catchup.failed", err=str(e))
                        async for raw in ws:
                            try:
                                msg = json.loads(raw)
                            except Exception:
                                continue
                            await self._handle_message(msg)
                except Exception as e:  # noqa: BLE001
                    log.warning("ws.disconnected", err=str(e))
                if not self._running:
                    break
                jitter = random.uniform(0.0, 0.3)
                wait = min(30.0, backoff + jitter)
                log.info("ws.reconnect_in", seconds=wait)
                await asyncio.sleep(wait)
                backoff = min(30.0, backoff * 2)
        finally:
            consumer_task.cancel()
            try:
                await consumer_task
            except asyncio.CancelledError:
                pass

    async def stop(self) -> None:
        self._running = False
