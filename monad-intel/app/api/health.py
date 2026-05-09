"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import desc, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app import __version__
from app.config import get_settings
from app.db import get_session
from app.logging import get_logger
from app.models.block import Block
from app.services.rpc import JsonRpcClient
from app.utils.time import utc_now

router = APIRouter()
log = get_logger(__name__)


@router.get("/health")
async def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "service": "Monad Scope",
        "version": __version__,
        "env": s.app_env,
        "chain": s.monad_chain,
        "chain_id": s.monad_chain_id,
    }


@router.get("/live/status")
async def live_status(session: AsyncSession = Depends(get_session)) -> dict:
    """Live ingestion status for the dashboard bottom bar.

    - `head`: current chain head (best-effort RPC; null on failure).
    - `last_processed`: highest block number we have stored.
    - `lag_blocks`: head - last_processed (null if either is null).
    - `lag_seconds`: now - last block timestamp (in seconds).
    - `tx_count_recent`: txs across the last 50 stored blocks.
    - `contracts_created_recent`: contracts across the last 50 stored blocks.
    """
    s = get_settings()

    # Latest stored block (timestamp + number).
    last_row = (
        await session.execute(select(Block).order_by(Block.number.desc()).limit(1))
    ).scalar_one_or_none()
    last_processed = last_row.number if last_row else None
    last_ts = last_row.timestamp if last_row else None

    lag_seconds: float | None = None
    if last_ts is not None:
        try:
            lag_seconds = max(0.0, (utc_now() - last_ts).total_seconds())
        except Exception:  # noqa: BLE001
            lag_seconds = None

    # Aggregate over the last 50 stored blocks for the bottom-bar pulse.
    recent_subq = (
        select(Block.tx_count, Block.contracts_created)
        .order_by(desc(Block.number))
        .limit(50)
        .subquery()
    )
    agg = (
        await session.execute(
            select(
                func.coalesce(func.sum(recent_subq.c.tx_count), 0),
                func.coalesce(func.sum(recent_subq.c.contracts_created), 0),
            )
        )
    ).first()
    tx_recent = int(agg[0]) if agg else 0
    contracts_recent = int(agg[1]) if agg else 0

    # Best-effort live head from RPC. Failures must not break the dashboard.
    head: int | None = None
    rpc = JsonRpcClient()
    try:
        head = await rpc.block_number()
    except Exception as e:  # noqa: BLE001
        log.warning("live.status.rpc_head_failed", err=str(e))
    finally:
        try:
            await rpc.close()
        except Exception:  # noqa: BLE001
            pass

    lag_blocks: int | None = None
    if head is not None and last_processed is not None:
        lag_blocks = max(0, head - last_processed)

    return {
        "chain": s.monad_chain,
        "chain_id": s.monad_chain_id,
        "head": head,
        "last_processed": last_processed,
        "lag_blocks": lag_blocks,
        "lag_seconds": lag_seconds,
        "tx_count_recent": tx_recent,
        "contracts_created_recent": contracts_recent,
    }
