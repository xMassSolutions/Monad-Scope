"""Ruleset management — list, propose, promote."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session
from app.repositories import rulesets as rulesets_repo
from app.services import recalibration as recal_svc

router = APIRouter()


@router.get("/rulesets")
async def list_rulesets(session: AsyncSession = Depends(get_session)) -> list[dict]:
    rows = await rulesets_repo.list_all(session)
    return [
        {
            "version": r.version,
            "status": r.status,
            "created_at": r.created_at.isoformat(),
            "weights": r.weights_json,
            "metrics": r.metrics_json,
        }
        for r in rows
    ]


@router.post("/rulesets/recalculate")
async def recalculate(
    promote_version: int | None = None,
    session: AsyncSession = Depends(get_session),
) -> dict:
    proposal = await recal_svc.propose_new_ruleset(session)
    promoted = None
    if promote_version is not None:
        await recal_svc.promote_ruleset(session, promote_version)
        promoted = promote_version
    return {"proposal": proposal, "promoted_version": promoted}
