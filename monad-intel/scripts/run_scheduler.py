"""CLI: run the rescan scheduler + regroup loops."""

from __future__ import annotations

import asyncio

import typer

from app.logging import configure_logging
from app.services.rpc import JsonRpcClient
from app.services.verifier import Verifier
from app.workers import regroup as regroup_worker
from app.workers import rescans as rescans_worker

app = typer.Typer(help="Run rescan + regroup loops.")


async def _run(rescan_every: int, regroup_every: int) -> None:
    configure_logging()
    rpc = JsonRpcClient()
    verifier = Verifier()
    try:
        await asyncio.gather(
            rescans_worker.loop(rpc, verifier, every_seconds=rescan_every),
            regroup_worker.loop(every_seconds=regroup_every),
        )
    finally:
        await rpc.close()


@app.command()
def main(
    rescan_every: int = typer.Option(60, "--rescan-every"),
    regroup_every: int = typer.Option(600, "--regroup-every"),
) -> None:
    asyncio.run(_run(rescan_every, regroup_every))


if __name__ == "__main__":
    app()
