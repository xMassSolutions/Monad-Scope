"""Health endpoint."""

from __future__ import annotations

from fastapi import APIRouter

from app import __version__
from app.config import get_settings

router = APIRouter()


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
