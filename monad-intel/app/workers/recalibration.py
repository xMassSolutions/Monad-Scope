"""Periodic drift check + propose-new-ruleset run. Never auto-promotes."""

from __future__ import annotations

import asyncio

from app.db import session_scope
from app.logging import get_logger
from app.services import drift as drift_svc
from app.services import recalibration as recal_svc

log = get_logger(__name__)


async def run_once() -> dict:
    async with session_scope() as session:
        report = await drift_svc.compute_finding_drift(session)
        log.info("recalibration.drift", **{k: v for k, v in report.items() if k != "by_code"})
        proposal = await recal_svc.propose_new_ruleset(session)
    return {"drift": report, "proposal": proposal}


async def loop(every_seconds: int = 24 * 3600) -> None:
    while True:
        try:
            await run_once()
        except Exception as e:  # noqa: BLE001
            log.exception("recalibration.loop.error", err=str(e))
        await asyncio.sleep(every_seconds)
