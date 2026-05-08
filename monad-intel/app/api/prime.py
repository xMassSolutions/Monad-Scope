"""Prime purchase endpoint — the billing-critical route."""

from __future__ import annotations

import asyncio

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.db import get_session
from app.repositories import contracts as contracts_repo
from app.schemas.prime import PrimePurchaseRequest, PrimeStatusBlock
from app.services import prime_state
from app.services.cache import get_redis
from app.services.privy import PrivyUser
from app.workers import prime as prime_worker

router = APIRouter()


def _normalize(address: str) -> str:
    address = address.lower()
    if not address.startswith("0x") or len(address) != 42:
        raise HTTPException(400, detail="invalid address")
    return address


@router.post("/contracts/{address}/prime", response_model=PrimeStatusBlock)
async def buy_prime(
    address: str,
    body: PrimePurchaseRequest,
    bg: BackgroundTasks,
    session: AsyncSession = Depends(get_session),
    user: PrivyUser = Depends(get_current_user),
) -> PrimeStatusBlock:
    address = _normalize(address)
    c = await contracts_repo.get_by_address(session, address)
    if c is None:
        raise HTTPException(404, detail="contract not found")
    redis = get_redis()
    # Stamp the requesting user onto the receipt so the audit trail records who paid.
    receipt = body.payment_receipt or f"privy:{user.user_id}"
    try:
        block = await prime_state.purchase(session, redis, c, receipt)
    except RuntimeError as e:
        raise HTTPException(402, detail=str(e))

    # If a fresh job was created, kick off the worker in the background.
    if block.job_id and block.state.value == "in_progress":
        bg.add_task(prime_worker.run_job, block.job_id)
    return block
