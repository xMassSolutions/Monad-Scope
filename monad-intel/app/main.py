"""FastAPI app factory + lifespan wiring."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app import __version__
from app.api import get_api_router
from app.db import session_scope
from app.logging import configure_logging, get_logger
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
    yield
    log.info("app.shutdown")


def create_app() -> FastAPI:
    app = FastAPI(
        title="Monad Scope",
        version=__version__,
        description="Monad Scope — Monad smart-contract intelligence backend.",
        lifespan=lifespan,
    )

    # CORS — allow the frontend (Vercel) to call the API.
    # Comma-separated list of origins via env, plus localhost for dev.
    raw_origins = os.getenv("CORS_ALLOW_ORIGINS", "")
    origins = [o.strip() for o in raw_origins.split(",") if o.strip()]
    origins += [
        "http://localhost:5173",
        "http://localhost:3000",
        "http://127.0.0.1:5173",
    ]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_origin_regex=r"https://.*\.vercel\.app",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(get_api_router())
    return app


app = create_app()
