"""Cron endpoints for serverless ingestion.

These are designed to be hit by Vercel Cron Jobs — they take the place of the
always-on WSS listener and the long-running bootstrap script that the laptop
ran in dev. Each tick processes a small batch of blocks within Vercel's
function-execution budget, then returns. Idempotent and safe to retry.

Authentication: the `Authorization: Bearer $CRON_SECRET` header is required.
Vercel auto-injects this when running cron jobs (matching the project env var).
"""

from __future__ import annotations

import os

from fastapi import APIRouter, Header, HTTPException, Query
from sqlalchemy import select

from app.db import session_scope
from app.logging import get_logger
from app.models.block import Block
from app.services.rpc import JsonRpcClient
from app.workers import blocks as blocks_worker

router = APIRouter()
log = get_logger(__name__)


def _check(authorization: str | None) -> None:
    secret = os.getenv("CRON_SECRET")
    if not secret:
        # In dev (no secret), allow.
        return
    if not authorization or authorization != f"Bearer {secret}":
        raise HTTPException(status_code=401, detail="unauthorized")


@router.get("/cron/poll")
async def cron_poll(
    authorization: str | None = Header(default=None),
    batch: int = Query(default=10, ge=1, le=50),
) -> dict:
    """Poll the latest N blocks from chain head and ingest any we have not seen.

    Replaces the WSS listener for serverless deployments. Run on a 1-minute
    Vercel Cron schedule.
    """
    _check(authorization)
    rpc = JsonRpcClient()
    processor = blocks_worker.BlockProcessor(rpc)
    try:
        head = await rpc.block_number()
        target_from = head - batch + 1

        # Find which blocks in [target_from, head] are not yet in our DB.
        async with session_scope() as session:
            res = await session.execute(
                select(Block.number).where(
                    Block.number >= target_from, Block.number <= head
                )
            )
            already = {row[0] for row in res.all()}

        to_process = [n for n in range(target_from, head + 1) if n not in already]
        processed = 0
        for n in to_process:
            try:
                await processor.process(n)
                processed += 1
            except Exception as e:  # noqa: BLE001
                log.warning("cron.poll.block_failed", number=n, err=str(e))

        log.info(
            "cron.poll.done",
            head=head,
            batch=batch,
            already=len(already),
            processed=processed,
        )
        return {
            "status": "ok",
            "head": head,
            "considered": batch,
            "skipped_already_seen": len(already),
            "processed": processed,
        }
    finally:
        await rpc.close()


@router.get("/cron/backfill")
async def cron_backfill(
    authorization: str | None = Header(default=None),
    batch: int = Query(default=20, ge=1, le=100),
) -> dict:
    """Walk backward from the lowest known block, processing `batch` more.

    Replaces the long-running bootstrap script. Idempotent — processed blocks
    are stored in the `blocks` table so re-runs are no-ops on overlap.
    """
    _check(authorization)
    rpc = JsonRpcClient()
    processor = blocks_worker.BlockProcessor(rpc)
    try:
        # Find the lowest block we have already processed.
        async with session_scope() as session:
            res = await session.execute(select(Block.number).order_by(Block.number.asc()).limit(1))
            row = res.first()
            lowest = int(row[0]) if row else None

        if lowest is None:
            # Nothing yet — start from current head.
            head = await rpc.block_number()
            target_to = head
            target_from = max(0, head - batch + 1)
        else:
            target_to = lowest - 1
            target_from = max(0, target_to - batch + 1)

        if target_to < target_from:
            return {"status": "ok", "note": "no work", "lowest": lowest}

        processed = 0
        for n in range(target_to, target_from - 1, -1):
            try:
                await processor.process(n)
                processed += 1
            except Exception as e:  # noqa: BLE001
                log.warning("cron.backfill.block_failed", number=n, err=str(e))

        log.info(
            "cron.backfill.done",
            from_block=target_from,
            to_block=target_to,
            processed=processed,
        )
        return {
            "status": "ok",
            "from_block": target_from,
            "to_block": target_to,
            "processed": processed,
        }
    finally:
        await rpc.close()
