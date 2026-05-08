"""Periodic regroup pass — recomputes project status from current contract state."""

from __future__ import annotations

import asyncio

from sqlalchemy import select

from app.db import session_scope
from app.logging import get_logger
from app.models.project import Project
from app.services import grouping as grouping_svc

log = get_logger(__name__)


async def run_once() -> int:
    async with session_scope() as session:
        res = await session.execute(select(Project.id))
        ids = list(res.scalars().all())
    log.info("regroup.start", project_count=len(ids))
    touched = 0
    for pid in ids:
        try:
            async with session_scope() as session:
                await grouping_svc.regroup_status(session, pid)
            touched += 1
        except Exception as e:  # noqa: BLE001
            log.exception("regroup.error", project_id=pid, err=str(e))
    log.info("regroup.done", touched=touched)
    return touched


async def loop(every_seconds: int = 600) -> None:
    while True:
        try:
            await run_once()
        except Exception as e:  # noqa: BLE001
            log.exception("regroup.loop.error", err=str(e))
        await asyncio.sleep(every_seconds)
