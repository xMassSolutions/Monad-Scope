"""Offline ruleset recalibration.

Pipeline:
1. Read per-rule precision metrics (services/outcomes.per_rule_metrics).
2. Propose new weights: weight_new = base_weight * (1 + alpha * (precision - 0.5))
   clipped to a sensible band. Codes with low support (< MIN_SUPPORT) are not changed.
3. Replay the candidate ruleset over recent analyses; compute tier-distribution diff.
4. Insert a new `rulesets` row with status='proposed' + the metrics report.
5. Promotion to 'active' is a separate admin call — never automatic.
"""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.logging import get_logger
from app.models.analysis import ContractAnalysis
from app.models.finding import ContractFinding
from app.repositories import contracts as contracts_repo
from app.repositories import findings as findings_repo
from app.repositories import rulesets as rulesets_repo
from app.services import outcomes as outcomes_svc
from app.services.findings import HARD_FAIL_CODES, WEIGHTED_FLAGS
from app.services.scoring import score
from app.utils.time import days, utc_now

log = get_logger(__name__)


MIN_SUPPORT = 5
ALPHA = 0.4
WEIGHT_FLOOR = 1
WEIGHT_CEIL = 40


def _propose_weights(
    base_weights: dict[str, int], rule_metrics: dict[str, dict[str, Any]]
) -> dict[str, int]:
    out = dict(base_weights)
    for code, base in base_weights.items():
        m = rule_metrics.get(code)
        if not m or m["support"] < MIN_SUPPORT:
            continue
        precision = float(m["precision"])
        new = int(round(base * (1 + ALPHA * (precision - 0.5))))
        out[code] = max(WEIGHT_FLOOR, min(WEIGHT_CEIL, new))
    return out


async def _replay(
    session: AsyncSession, weights: dict[str, int], window: timedelta
) -> dict[str, Any]:
    cutoff = utc_now() - window
    res = await session.execute(
        select(ContractAnalysis).where(ContractAnalysis.created_at >= cutoff)
    )
    analyses = list(res.scalars().all())
    tier_counts = {t: 0 for t in ("SAFE", "CAUTION", "HIGH_RISK", "CRITICAL")}
    diff_count = 0
    for a in analyses:
        # Pull the findings + features that were valid at analysis time.
        fres = await session.execute(
            select(ContractFinding).where(ContractFinding.contract_id == a.contract_id)
        )
        findings = list(fres.scalars().all())
        sf = await contracts_repo.get_static_features(session, a.contract_id)
        df = await contracts_repo.get_dynamic_features(session, a.contract_id)
        verdict = score(static_features=sf, dynamic_features=df, findings=findings, weights=weights)
        tier_counts[verdict.risk_tier] += 1
        if verdict.risk_tier != a.risk_tier:
            diff_count += 1
    return {
        "sample": len(analyses),
        "tier_counts": tier_counts,
        "tier_diff_vs_active": diff_count,
        "window_days": window.days,
    }


async def propose_new_ruleset(
    session: AsyncSession,
    *,
    replay_window: timedelta = timedelta(days=30),
) -> dict[str, Any]:
    """Build the next candidate ruleset and insert it as 'proposed'.

    Returns a small report describing what was proposed (also persisted on the row).
    """
    base = WEIGHTED_FLAGS
    active = await rulesets_repo.get_active(session)
    if active and active.weights_json:
        base = {**base, **active.weights_json}

    metrics = await outcomes_svc.per_rule_metrics(session)
    candidate = _propose_weights(base, metrics)
    replay = await _replay(session, candidate, replay_window)

    next_v = await rulesets_repo.next_version(session)
    report = {
        "base_version": active.version if active else None,
        "metrics_used": metrics,
        "weights_before": base,
        "weights_after": candidate,
        "replay": replay,
    }
    row = await rulesets_repo.insert(
        session,
        version=next_v,
        weights_json=candidate,
        metrics_json=report,
        status="proposed",
    )
    log.info(
        "recalibration.proposed",
        version=row.version,
        rules_changed=sum(1 for k in candidate if base.get(k) != candidate[k]),
        replay=replay,
    )
    return {"version": row.version, "report": report}


async def promote_ruleset(session: AsyncSession, version: int) -> None:
    await rulesets_repo.promote(session, version)
    log.info("recalibration.promoted", version=version)


async def seed_default_ruleset_if_empty(session: AsyncSession) -> None:
    """Bootstraps ruleset v1 (the WEIGHTED_FLAGS constants) on fresh installs."""
    existing = await rulesets_repo.list_all(session)
    if existing:
        return
    v = 1
    await rulesets_repo.insert(
        session,
        version=v,
        weights_json=dict(WEIGHTED_FLAGS),
        metrics_json={"seed": True, "hard_fail_codes": list(HARD_FAIL_CODES)},
        status="active",
    )
    log.info("recalibration.seeded_default", version=v)
