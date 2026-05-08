"""FastAPI app factory + lifespan wiring."""

from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api import get_api_router
from app.db import session_scope
from app.logging import configure_logging, get_logger
from app.repositories import exploits as exploits_repo
from app.services import exploit_feed as exploit_feed_svc
from app.services import recalibration as recal_svc

log = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    log.info("app.startup", version=__version__)
    # Bootstrap ruleset v1 if absent. Idempotent.
    try:
        async with session_scope() as session:
            await recal_svc.seed_default_ruleset_if_empty(session)
    except Exception as e:  # noqa: BLE001
        log.warning("app.seed_failed", err=str(e))
    # Seed the exploit registry on first boot if it's empty. Best-effort —
    # network failures must not block app startup.
    try:
        async with session_scope() as session:
            existing = await exploits_repo.count(session)
            if existing == 0:
                result = await exploit_feed_svc.sync_defillama(session)
                log.info("app.exploit_seed", **result)
    except Exception as e:  # noqa: BLE001
        log.warning("app.exploit_seed_failed", err=str(e))
    yield
    log.info("app.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Monad Scope",
        version=__version__,
        description="Monad Scope — Monad smart-contract intelligence backend.",
        lifespan=lifespan,
    )
    app.include_router(get_api_router())
    return app


app = create_app()
