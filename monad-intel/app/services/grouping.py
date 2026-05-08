"""Project grouping engine.

First-pass: assign during enrichment using strong signals (creator + impl-hash).
Regroup: a periodic pass that merges/splits based on accumulated metadata.

Status defaults to `watchlist`; promotion to `live_project` requires liquidity
+ holders, which is computed by the regroup pass.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models.contract import Contract
from app.repositories import contracts as contracts_repo
from app.repositories import projects as projects_repo

log = get_logger(__name__)


@dataclass(frozen=True)
class GroupingDecision:
    project_id: str
    role: str | None
    confidence: float
    created_new: bool


def _proposed_name(contract: Contract) -> str:
    if contract.contract_name:
        return contract.contract_name
    if contract.symbol:
        return contract.symbol
    return f"unnamed-{(contract.creator_address or contract.address)[:10]}"


async def assign_first_pass(
    session: AsyncSession,
    contract: Contract,
) -> GroupingDecision:
    """Assign a project at enrichment time. Strategy:

    1. If implementation_hash is known, look for any contract sharing it; reuse its project.
    2. Else if creator_address is known, look for any contract sharing it (within an
       ad-hoc time window); reuse its project.
    3. Else create a new singleton project (status=watchlist).
    """
    role = contract.kind
    confidence = 0.5

    # Signal 1: implementation hash.
    if contract.implementation_hash:
        siblings = await contracts_repo.list_by_implementation_hash(
            session, contract.implementation_hash
        )
        for s in siblings:
            if s.id == contract.id:
                continue
            if s.project_id:
                await projects_repo.link_contract(
                    session,
                    project_id=s.project_id,
                    contract_id=contract.id,
                    role=role,
                    confidence=0.85,
                )
                await contracts_repo.set_project(session, contract.id, s.project_id)
                await projects_repo.touch_last_seen(session, s.project_id)
                return GroupingDecision(s.project_id, role, 0.85, False)

    # Signal 2: creator address.
    if contract.creator_address:
        siblings = await contracts_repo.list_by_creator(session, contract.creator_address)
        for s in siblings:
            if s.id == contract.id:
                continue
            if s.project_id:
                await projects_repo.link_contract(
                    session,
                    project_id=s.project_id,
                    contract_id=contract.id,
                    role=role,
                    confidence=0.7,
                )
                await contracts_repo.set_project(session, contract.id, s.project_id)
                await projects_repo.touch_last_seen(session, s.project_id)
                return GroupingDecision(s.project_id, role, 0.7, False)

    # Signal 3: new singleton project.
    name = _proposed_name(contract)
    project = await projects_repo.get_or_create(
        session,
        canonical_name=name,
        creator_cluster=contract.creator_address,
        status="watchlist",
    )
    await projects_repo.link_contract(
        session,
        project_id=project.id,
        contract_id=contract.id,
        role=role,
        confidence=confidence,
    )
    await contracts_repo.set_project(session, contract.id, project.id)
    return GroupingDecision(project.id, role, confidence, True)


async def regroup_status(session: AsyncSession, project_id: str) -> str:
    """Recompute a project's status from its contracts. Pure read + write."""
    contract_ids = await projects_repo.list_contract_ids(session, project_id)
    if not contract_ids:
        await projects_repo.set_status(session, project_id, "noise_or_dead")
        return "noise_or_dead"

    risk_tiers: list[str] = []
    has_liquidity = False
    for cid in contract_ids:
        c = await contracts_repo.get_by_id(session, cid)
        if not c:
            continue
        if c.risk_tier:
            risk_tiers.append(c.risk_tier)
        df = await contracts_repo.get_dynamic_features(session, cid)
        if df.get("has_liquidity"):
            has_liquidity = True

    if any(t == "CRITICAL" for t in risk_tiers):
        status = "suspicious_cluster"
    elif has_liquidity:
        status = "live_project"
    elif all(t in ("SAFE", "CAUTION") for t in risk_tiers):
        status = "infra_only"
    else:
        status = "watchlist"

    await projects_repo.set_status(session, project_id, status)
    return status
