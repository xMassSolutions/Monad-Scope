"""Outcome ingestion + per-rule support and precision-like metrics."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import ContractFinding
from app.models.outcome import Outcome
from app.repositories import outcomes as outcomes_repo
from app.utils.time import days, utc_now


# Outcome labels considered "bad" for precision computation.
BAD_LABELS = {"rug_pull", "honeypot", "lp_removed", "exploited"}


async def record(
    session: AsyncSession,
    *,
    contract_id: str | None,
    project_id: str | None,
    outcome_label: str,
    notes: str | None = None,
) -> Outcome:
    return await outcomes_repo.insert(
        session,
        contract_id=contract_id,
        project_id=project_id,
        outcome_label=outcome_label,
        notes=notes,
    )


async def per_rule_metrics(
    session: AsyncSession, since: datetime | None = None
) -> dict[str, dict[str, Any]]:
    """For each finding code, compute support (count) and precision-like metric.

    precision = bad_outcomes_when_present / total_outcomes_when_present

    Returns a mapping: {code: {support, bad, precision}}.
    """
    since = since or (utc_now() - days(90))
    outcomes = await outcomes_repo.list_in_window(session, since)
    if not outcomes:
        return {}

    # Build a contract -> label index.
    contract_label: dict[str, str] = {}
    for o in outcomes:
        if o.contract_id:
            contract_label[o.contract_id] = o.outcome_label

    if not contract_label:
        return {}

    res = await session.execute(
        select(ContractFinding.contract_id, ContractFinding.code).where(
            ContractFinding.contract_id.in_(list(contract_label.keys()))
        )
    )
    counts: dict[str, dict[str, int]] = defaultdict(lambda: {"support": 0, "bad": 0})
    seen = set()
    for cid, code in res.all():
        key = (cid, code)
        if key in seen:
            continue
        seen.add(key)
        counts[code]["support"] += 1
        if contract_label[cid] in BAD_LABELS:
            counts[code]["bad"] += 1

    metrics: dict[str, dict[str, Any]] = {}
    for code, c in counts.items():
        sup = c["support"]
        bad = c["bad"]
        precision = (bad / sup) if sup else 0.0
        metrics[code] = {"support": sup, "bad": bad, "precision": round(precision, 4)}
    return metrics
