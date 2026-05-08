"""Admin / ops endpoints — bootstrap, listener control, manual block ingest, scheduler."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks
from pydantic import BaseModel, Field

from app.logging import get_logger
from app.services import bootstrap as bootstrap_svc
from app.services import ws_listener as ws
from app.services.rpc import JsonRpcClient
from app.services.verifier import Verifier
from app.workers import blocks as blocks_worker
from app.workers import rescans as rescans_worker

router = APIRouter()
log = get_logger(__name__)

# Process-local handles for the admin-controlled long-running tasks. In a real
# multi-process deployment, replace these with a control plane (Redis, k8s job).
_listener_task: asyncio.Task | None = None
_listener: ws.WsListener | None = None


class BootstrapRangeRequest(BaseModel):
    from_block: int = Field(..., ge=0)
    to_block: int = Field(..., ge=0)


class BootstrapStartRequest(BaseModel):
    """`from_block` defaults to 0; `to_block` defaults to current head."""
    from_block: int | None = None
    to_block: int | None = None


@router.post("/bootstrap/range")
async def bootstrap_range(req: BootstrapRangeRequest, bg: BackgroundTasks) -> dict:
    rpc = JsonRpcClient()
    verifier = Verifier()
    processor = blocks_worker.BlockProcessor(rpc)

    async def _run() -> None:
        try:
            await bootstrap_svc.crawl_range(
                processor.process, from_block=req.from_block, to_block=req.to_block
            )
        finally:
            await rpc.close()

    bg.add_task(_run)
    return {
        "status": "scheduled",
        "from_block": req.from_block,
        "to_block": req.to_block,
    }


@router.post("/bootstrap/start")
async def bootstrap_start(req: BootstrapStartRequest, bg: BackgroundTasks) -> dict:
    rpc = JsonRpcClient()
    head = req.to_block if req.to_block is not None else await rpc.block_number()
    start = req.from_block if req.from_block is not None else max(0, head - 1000)
    processor = blocks_worker.BlockProcessor(rpc)

    async def _run() -> None:
        try:
            await bootstrap_svc.crawl_range(processor.process, from_block=start, to_block=head)
        finally:
            await rpc.close()

    bg.add_task(_run)
    return {"status": "scheduled", "from_block": start, "to_block": head}


@router.post("/sync/listener/start")
async def listener_start() -> dict:
    """Start the live WS listener as a background task in this process."""
    global _listener_task, _listener
    if _listener_task and not _listener_task.done():
        return {"status": "already_running"}
    rpc = JsonRpcClient()
    processor = blocks_worker.BlockProcessor(rpc)
    _listener = ws.WsListener(processor.process, rpc=rpc)
    _listener_task = asyncio.create_task(_listener.run(), name="ws-listener")
    return {"status": "started"}


@router.post("/sync/process-block/{block_number}")
async def process_block(block_number: int) -> dict:
    rpc = JsonRpcClient()
    processor = blocks_worker.BlockProcessor(rpc)
    try:
        await processor.process(block_number)
    finally:
        await rpc.close()
    return {"status": "processed", "block": block_number}


@router.post("/scheduler/run-due")
async def scheduler_run_due(batch: int = 50) -> dict:
    rpc = JsonRpcClient()
    verifier = Verifier()
    try:
        n = await rescans_worker.run_due(rpc, verifier, batch=batch)
    finally:
        await rpc.close()
    return {"status": "ok", "processed": n}
