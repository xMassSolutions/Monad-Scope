"""Async JSON-RPC client for Monad.

- Round-robins across configured HTTP URLs.
- Bounded retry with exponential backoff + jitter.
- Supports JSON-RPC batch.
- Tolerant of `null`-receipt responses (Monad will return null briefly at the head).
"""

from __future__ import annotations

import asyncio
import itertools
import random
from typing import Any

import httpx

from app.config import get_settings
from app.logging import get_logger

log = get_logger(__name__)


class RpcError(Exception):
    def __init__(self, code: int, message: str, data: Any = None) -> None:
        super().__init__(f"[{code}] {message}")
        self.code = code
        self.message = message
        self.data = data


class JsonRpcClient:
    def __init__(
        self,
        urls: list[str] | None = None,
        timeout: float | None = None,
        max_retries: int | None = None,
    ) -> None:
        s = get_settings()
        self._urls = urls or s.rpc_http_urls
        if not self._urls:
            raise ValueError("no RPC HTTP urls configured")
        self._cycle = itertools.cycle(self._urls)
        self._timeout = timeout if timeout is not None else s.rpc_timeout_seconds
        self._max_retries = max_retries if max_retries is not None else s.rpc_max_retries
        self._client: httpx.AsyncClient | None = None
        self._req_id = 0
        self._lock = asyncio.Lock()

    async def __aenter__(self) -> "JsonRpcClient":
        await self.start()
        return self

    async def __aexit__(self, *exc_info) -> None:
        await self.close()

    async def start(self) -> None:
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self._timeout)

    async def close(self) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def _next_id(self) -> int:
        async with self._lock:
            self._req_id += 1
            return self._req_id

    async def call(self, method: str, params: list[Any] | None = None) -> Any:
        await self.start()
        rid = await self._next_id()
        payload = {"jsonrpc": "2.0", "id": rid, "method": method, "params": params or []}
        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            url = next(self._cycle)
            try:
                resp = await self._client.post(url, json=payload)
                resp.raise_for_status()
                body = resp.json()
                if "error" in body and body["error"] is not None:
                    err = body["error"]
                    raise RpcError(int(err.get("code", -1)), err.get("message", "rpc error"), err.get("data"))
                return body.get("result")
            except (httpx.HTTPError, RpcError) as e:
                last_err = e
                if attempt == self._max_retries:
                    break
                backoff = (2**attempt) * 0.15 + random.uniform(0.0, 0.1)
                log.warning("rpc.retry", method=method, url=url, attempt=attempt, err=str(e), backoff=backoff)
                await asyncio.sleep(backoff)
        assert last_err is not None
        log.error("rpc.failed", method=method, err=str(last_err))
        raise last_err

    async def batch(self, calls: list[tuple[str, list[Any] | None]]) -> list[Any]:
        """Send a JSON-RPC batch. Returns results in input order. Raises on first error."""
        await self.start()
        if not calls:
            return []
        ids = []
        payload = []
        for method, params in calls:
            rid = await self._next_id()
            ids.append(rid)
            payload.append({"jsonrpc": "2.0", "id": rid, "method": method, "params": params or []})
        last_err: Exception | None = None
        for attempt in range(self._max_retries + 1):
            url = next(self._cycle)
            try:
                resp = await self._client.post(url, json=payload)
                resp.raise_for_status()
                body = resp.json()
                if not isinstance(body, list):
                    raise RpcError(-32000, "expected batch response", body)
                by_id = {item["id"]: item for item in body}
                results: list[Any] = []
                for rid in ids:
                    item = by_id.get(rid)
                    if item is None:
                        raise RpcError(-32001, f"missing id {rid} in batch response")
                    if "error" in item and item["error"] is not None:
                        err = item["error"]
                        raise RpcError(int(err.get("code", -1)), err.get("message", "rpc error"))
                    results.append(item.get("result"))
                return results
            except (httpx.HTTPError, RpcError) as e:
                last_err = e
                if attempt == self._max_retries:
                    break
                backoff = (2**attempt) * 0.15 + random.uniform(0.0, 0.1)
                log.warning("rpc.batch.retry", attempt=attempt, err=str(e), backoff=backoff)
                await asyncio.sleep(backoff)
        assert last_err is not None
        raise last_err

    # ---------- convenience wrappers ----------

    async def chain_id(self) -> int:
        from app.utils.time import parse_hex_qty
        return parse_hex_qty(await self.call("eth_chainId"))

    async def block_number(self) -> int:
        from app.utils.time import parse_hex_qty
        return parse_hex_qty(await self.call("eth_blockNumber"))

    async def get_block_by_number(
        self, number: int | str, full_tx: bool = True
    ) -> dict[str, Any] | None:
        tag = number if isinstance(number, str) else hex(number)
        return await self.call("eth_getBlockByNumber", [tag, full_tx])

    async def get_transaction_receipt(self, tx_hash: str) -> dict[str, Any] | None:
        return await self.call("eth_getTransactionReceipt", [tx_hash])

    async def get_transaction_receipts_with_retry(
        self,
        tx_hashes: list[str],
        attempts: int | None = None,
        base_ms: int | None = None,
    ) -> dict[str, dict[str, Any] | None]:
        """Receipts at the head may briefly be null on Monad. Retry per-hash."""
        s = get_settings()
        attempts = attempts or s.receipt_retry_attempts
        base_ms = base_ms or s.receipt_retry_base_ms
        out: dict[str, dict[str, Any] | None] = {}
        for h in tx_hashes:
            r = None
            for i in range(attempts):
                r = await self.get_transaction_receipt(h)
                if r is not None:
                    break
                await asyncio.sleep((base_ms / 1000.0) * (2**i) * (0.7 + random.random() * 0.6))
            out[h] = r
        return out

    async def get_code(self, address: str, block: str = "latest") -> str:
        return await self.call("eth_getCode", [address, block])

    async def eth_call(self, to: str, data: str, block: str = "latest") -> str:
        return await self.call("eth_call", [{"to": to, "data": data}, block])

    async def get_storage_at(self, address: str, slot: str, block: str = "latest") -> str:
        return await self.call("eth_getStorageAt", [address, slot, block])
