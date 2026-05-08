"""Drift detection: compare recent vs historical finding-frequency distributions.

Uses symmetric KL divergence with Laplace smoothing — robust on small samples.
Produces a *report*, not an action. Promotion stays a manual admin step.
"""

from __future__ import annotations

import math
from collections import Counter
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.finding import ContractFinding
from app.utils.time import days, utc_now


def _smoothed_distribution(counts: dict[str, int], keys: list[str]) -> dict[str, float]:
    n = sum(counts.values()) + len(keys)  # +1 per key (Laplace)
    return {k: (counts.get(k, 0) + 1) / n for k in keys}


def _kl(p: dict[str, float], q: dict[str, float]) -> float:
    return sum(p[k] * math.log(p[k] / q[k]) for k in p if p[k] > 0 and q[k] > 0)


def _symmetric_kl(p: dict[str, float], q: dict[str, float]) -> float:
    return 0.5 * (_kl(p, q) + _kl(q, p))


async def compute_finding_drift(
    session: AsyncSession,
    *,
    recent_window: timedelta = timedelta(days=14),
    historical_window: timedelta = timedelta(days=90),
) -> dict[str, Any]:
    now = utc_now()
    historical_start = now - historical_window
    recent_start = now - recent_window

    res = await session.execute(
        select(ContractFinding.code, ContractFinding.created_at).where(
            ContractFinding.created_at >= historical_start
        )
    )
    rows = list(res.all())
    if not rows:
        return {"sample_size": 0, "kl_divergence": 0.0, "by_code": {}}

    historical = Counter()
    recent = Counter()
    for code, ts in rows:
        historical[code] += 1
        if ts >= recent_start:
            recent[code] += 1

    keys = sorted(set(historical) | set(recent))
    p = _smoothed_distribution(dict(historical), keys)
    q = _smoothed_distribution(dict(recent), keys)
    kl = _symmetric_kl(p, q)

    by_code = {
        k: {
            "historical_freq": round(p[k], 4),
            "recent_freq": round(q[k], 4),
            "delta": round(q[k] - p[k], 4),
        }
        for k in keys
    }
    return {
        "sample_size": len(rows),
        "recent_window_days": recent_window.days,
        "historical_window_days": historical_window.days,
        "kl_divergence": round(kl, 4),
        "by_code": by_code,
    }
