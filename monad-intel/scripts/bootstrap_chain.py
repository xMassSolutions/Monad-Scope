"""CLI: bootstrap a historical block range.

Usage:
    python scripts/bootstrap_chain.py --from-block 1000 --to-block 1200
"""

from __future__ import annotations

import asyncio

import typer

from app.db import create_all, session_scope
from app.logging import configure_logging, get_logger
from app.services import bootstrap as bootstrap_svc
from app.services import recalibration as recal_svc
from app.services.rpc import JsonRpcClient
from app.services.verifier import Verifier
from app.workers.blocks import BlockProcessor
from app.workers.enrichment import run_enrichment_workers

app = typer.Typer(help="Bootstrap a Monad block range.")


async def _run(from_block: int, to_block: int, init_db: bool) -> None:
    configure_logging()
    log = get_logger("bootstrap")
    if init_db:
        await create_all()
    async with session_scope() as s:
        await recal_svc.seed_default_ruleset_if_empty(s)

    rpc = JsonRpcClient()
    verifier = Verifier()
    workers = await run_enrichment_workers(rpc, verifier)
    processor = BlockProcessor(rpc)

    async def process(n: int) -> None:
        await processor.process(n)

    try:
        result = await bootstrap_svc.crawl_range(
            process, from_block=from_block, to_block=to_block
        )
        log.info("bootstrap.complete", **result)
    finally:
        for t in workers:
            t.cancel()
        await rpc.close()


@app.command()
def main(
    from_block: int = typer.Option(..., "--from-block"),
    to_block: int = typer.Option(..., "--to-block"),
    init_db: bool = typer.Option(False, "--init-db", help="Create tables before starting (dev only)."),
) -> None:
    asyncio.run(_run(from_block, to_block, init_db))


if __name__ == "__main__":
    app()
