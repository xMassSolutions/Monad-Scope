"""Enrichment worker — bounded-concurrency processor for newly created contracts.

Scaffold uses an in-process asyncio.Queue + semaphore. Production can replace
`enqueue_enrichment` and `run_enrichment_workers` with a real broker (Redis
streams, NATS, RabbitMQ) without changing call sites.
"""

from __future__ import annotations

import asyncio

from app.config import get_settings
from app.db import session_scope
from app.logging import get_logger
from app.repositories import contracts as contracts_repo
from app.services import enrichment as enrichment_svc
from app.services.rpc import JsonRpcClient
from app.services.verifier import Verifier

log = get_logger(__name__)

_queue: asyncio.Queue[str] = asyncio.Queue(maxsize=4096)


async def enqueue_enrichment(address: str) -> None:
    try:
        _queue.put_nowait(address)
    except asyncio.QueueFull:
        await _queue.put(address)


async def _worker(rpc: JsonRpcClient, verifier: Verifier, sem: asyncio.Semaphore) -> None:
    while True:
        address = await _queue.get()
        try:
            async with sem:
                async with session_scope() as session:
                    contract = await contracts_repo.get_by_address(session, address)
                    if contract is None:
                        log.warning("enrichment.contract_missing", address=address)
                        continue
                    await enrichment_svc.enrich_contract(
                        session, rpc, verifier, contract, stage="initial"
                    )
        except Exception as e:  # noqa: BLE001
            log.exception("enrichment.error", address=address, err=str(e))
        finally:
            _queue.task_done()


async def run_enrichment_workers(rpc: JsonRpcClient, verifier: Verifier) -> list[asyncio.Task]:
    s = get_settings()
    sem = asyncio.Semaphore(s.enrichment_concurrency)
    tasks = [
        asyncio.create_task(_worker(rpc, verifier, sem), name=f"enrich-{i}")
        for i in range(s.enrichment_concurrency)
    ]
    return tasks
