"""CLI: run the live WebSocket listener until Ctrl+C."""

from __future__ import annotations

import asyncio
import signal

import typer

from app.db import create_all, session_scope
from app.logging import configure_logging, get_logger
from app.repositories import blocks as blocks_repo
from app.services import recalibration as recal_svc
from app.services.rpc import JsonRpcClient
from app.services.verifier import Verifier
from app.services.ws_listener import WsListener
from app.workers.blocks import BlockProcessor
from app.workers.enrichment import run_enrichment_workers

app = typer.Typer(help="Run the live Monad block listener.")


async def _run(init_db: bool) -> None:
    configure_logging()
    log = get_logger("listener")
    if init_db:
        await create_all()
    async with session_scope() as s:
        await recal_svc.seed_default_ruleset_if_empty(s)
        last = await blocks_repo.get_max_processed_block(s)

    rpc = JsonRpcClient()
    verifier = Verifier()
    enrichment_tasks = await run_enrichment_workers(rpc, verifier)
    processor = BlockProcessor(rpc)
    listener = WsListener(processor.process, rpc=rpc)
    if last is not None:
        listener.set_last_processed(last)

    stop = asyncio.Event()
    loop = asyncio.get_event_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, stop.set)
        except NotImplementedError:
            # Windows or restricted env.
            pass

    listener_task = asyncio.create_task(listener.run())
    log.info("listener.started", last_processed=last)
    await stop.wait()
    log.info("listener.stopping")
    await listener.stop()
    listener_task.cancel()
    for t in enrichment_tasks:
        t.cancel()
    await rpc.close()


@app.command()
def main(
    init_db: bool = typer.Option(False, "--init-db"),
) -> None:
    asyncio.run(_run(init_db))


if __name__ == "__main__":
    app()
