"""CLI: run drift detection + propose a new ruleset (status='proposed').

Promotion requires a separate admin action via POST /rulesets/recalculate?promote=true.
"""

from __future__ import annotations

import asyncio
import json

import typer

from app.db import session_scope
from app.logging import configure_logging
from app.services import drift as drift_svc
from app.services import recalibration as recal_svc

app = typer.Typer(help="Run recalibration: drift + proposal (no promotion).")


async def _run(promote_version: int | None) -> None:
    configure_logging()
    async with session_scope() as session:
        drift = await drift_svc.compute_finding_drift(session)
        proposal = await recal_svc.propose_new_ruleset(session)
        if promote_version is not None:
            await recal_svc.promote_ruleset(session, promote_version)
    typer.echo(json.dumps({"drift": drift, "proposal": proposal}, default=str, indent=2))


@app.command()
def main(
    promote_version: int = typer.Option(
        None, "--promote-version", help="Promote a previously proposed ruleset version to active."
    ),
) -> None:
    asyncio.run(_run(promote_version))


if __name__ == "__main__":
    app()
