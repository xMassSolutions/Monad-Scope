"""TTL-driven rescan scheduler.

Picks contracts whose `next_refresh_at` is in the past (or NULL) and dispatches
them for re-enrichment. The next refresh interval depends on risk tier and
whether the project has liquidity.

Per-feature TTLs are advisory and used by the dynamic refresh service to
decide which feature buckets to actually re-fetch.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract
from app.repositories import contracts as contracts_repo
from app.utils.time import days, hours, utc_now


# Per-feature TTLs (used by feature_dynamic / refresh logic to decide what to re-fetch).
FEATURE_TTL = {
    "source_code": days(30),
    "proxy_impl": days(1),
    "owner_state": days(1),
    "liquidity": hours(6),
    "holder_distribution": days(7),
    "pair_activity": hours(6),
    "deployer_profile": days(7),
    "verification_state": days(14),
}


def next_refresh(*, risk_tier: str | None, has_liquidity: bool, is_live_project: bool) -> datetime:
    if risk_tier == "CRITICAL":
        return utc_now() + hours(6)
    if risk_tier == "HIGH_RISK":
        return utc_now() + days(1)
    if is_live_project and has_liquidity:
        return utc_now() + days(2)
    return utc_now() + days(7)


@dataclass
class ScheduledItem:
    contract_id: str
    address: str
    next_due: datetime | None


async def list_due(
    session: AsyncSession, now: datetime | None = None, limit: int = 100
) -> list[ScheduledItem]:
    now = now or utc_now()
    rows = await contracts_repo.list_due_for_refresh(session, now=now, limit=limit)
    return [
        ScheduledItem(contract_id=c.id, address=c.address, next_due=c.next_refresh_at)
        for c in rows
    ]
