"""Outcome ingestion endpoint."""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_session
from app.schemas.common import OutcomeLabel
from app.services import outcomes as outcomes_svc
from app.services.privy import PrivyUser

router = APIRouter()


class OutcomeIn(BaseModel):
    contract_id: str | None = None
    project_id: str | None = None
    outcome_label: OutcomeLabel
    notes: str | None = None


@router.post("/outcomes")
async def post_outcome(
    body: OutcomeIn,
    session: AsyncSession = Depends(get_session),
    user: PrivyUser = Depends(get_current_user),
) -> dict:
    if body.contract_id is None and body.project_id is None:
        raise HTTPException(400, detail="contract_id or project_id is required")
    # Prefix the notes with the reporter id so the supervised-evolution layer
    # can attribute labels.
    notes = body.notes
    if user.user_id and user.user_id != "anonymous":
        prefix = f"reporter={user.user_id}"
        notes = f"{prefix} | {notes}" if notes else prefix
    row = await outcomes_svc.record(
        session,
        contract_id=body.contract_id,
        project_id=body.project_id,
        outcome_label=body.outcome_label.value,
        notes=notes,
    )
    return {"id": row.id, "outcome_label": row.outcome_label, "reporter": user.user_id}
