"""TTL-driven rescan worker. Picks due contracts and re-runs the pipeline in 'refined' stage."""

from __future__ import annotations

import asyncio

from app.db import session_scope
from app.logging import get_logger
from app.repositories import contracts as contracts_repo
from app.services import enrichment as enrichment_svc
from app.services import scheduler as scheduler_svc
from app.services.rpc import JsonRpcClient
from app.services.verifier import Verifier

log = get_logger(__name__)


async def run_due(rpc: JsonRpcClient, verifier: Verifier, batch: int = 50) -> int:
    async with session_scope() as session:
        due = await scheduler_svc.list_due(session, limit=batch)
    log.info("rescans.due", count=len(due))
    processed = 0
    for item in due:
        try:
            async with session_scope() as session:
                contract = await contracts_repo.get_by_id(session, item.contract_id)
                if contract is None:
                    continue
                await enrichment_svc.enrich_contract(
                    session, rpc, verifier, contract, stage="refined"
                )
            processed += 1
        except Exception as e:  # noqa: BLE001
            log.exception("rescans.error", contract_id=item.contract_id, err=str(e))
    return processed


async def loop(rpc: JsonRpcClient, verifier: Verifier, every_seconds: int = 60) -> None:
    while True:
        try:
            await run_due(rpc, verifier)
        except Exception as e:  # noqa: BLE001
            log.exception("rescans.loop.error", err=str(e))
        await asyncio.sleep(every_seconds)
