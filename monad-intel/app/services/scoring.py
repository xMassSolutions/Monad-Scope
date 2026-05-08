"""Pure scoring engine.

Signature: (features, findings, ruleset, exploit_match?) -> Verdict
This module reads no globals. The active ruleset is passed in by the caller,
which is what makes shadow-replay against historical data safe.

If a `MatchReport` from app.services.exploit_match is passed in, its
calibrated bonus is added to the risk score (capped) and its evidence is
exposed in `summary.exploit_calibration`. Without it, scoring behaves
exactly as before — the exploit registry is purely additive.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.models.finding import ContractFinding
from app.services.exploit_match import MatchReport
from app.services.findings import HARD_FAIL_CODES, WEIGHTED_FLAGS


@dataclass(frozen=True)
class Verdict:
    risk_score: float        # 0..100
    confidence_score: float  # 0..1
    risk_tier: str           # SAFE | CAUTION | HIGH_RISK | CRITICAL
    action: str              # ALLOW | WARN | ESCALATE | BLOCK
    summary: dict[str, Any]
    unknowns: dict[str, Any]


# Tier thresholds expressed as risk-score bands.
TIER_THRESHOLDS = (
    ("CRITICAL", 75),
    ("HIGH_RISK", 50),
    ("CAUTION", 25),
    ("SAFE", 0),
)

ACTION_BY_TIER = {
    "CRITICAL": "BLOCK",
    "HIGH_RISK": "ESCALATE",
    "CAUTION": "WARN",
    "SAFE": "ALLOW",
}


def _tier_for(risk_score: float, has_hard_fail: bool) -> str:
    if has_hard_fail:
        return "CRITICAL"
    for tier, threshold in TIER_THRESHOLDS:
        if risk_score >= threshold:
            return tier
    return "SAFE"


def _confidence(static_features: dict[str, Any], dynamic_features: dict[str, Any]) -> tuple[float, dict[str, Any]]:
    """Confidence starts at 1.0 and is decreased by knowledge gaps."""
    score = 1.0
    unknowns: dict[str, Any] = {}

    if not static_features.get("source_verified"):
        score -= 0.20
        unknowns["source_verified"] = False
    if static_features.get("is_proxy") and not static_features.get("implementation_verified"):
        score -= 0.15
        unknowns["implementation_verified"] = False

    if dynamic_features.get("has_liquidity") is None:
        score -= 0.10
        unknowns["liquidity"] = None
    if dynamic_features.get("holder_count") is None:
        score -= 0.10
        unknowns["holder_count"] = None
    if dynamic_features.get("tx_count_1d") is None and dynamic_features.get("tx_count_7d") is None:
        score -= 0.05
        unknowns["activity"] = None

    return max(0.05, min(1.0, score)), unknowns


def score(
    *,
    static_features: dict[str, Any],
    dynamic_features: dict[str, Any],
    findings: list[ContractFinding],
    weights: dict[str, int] | None = None,
    exploit_match: MatchReport | None = None,
) -> Verdict:
    weights = {**WEIGHTED_FLAGS, **(weights or {})}
    sf = static_features or {}
    df = dynamic_features or {}

    has_hard_fail = any(f.code in HARD_FAIL_CODES for f in findings)

    # Risk = clipped weighted sum of non-hard-fail findings.
    weighted_total = sum(weights.get(f.code, f.weight) for f in findings if f.code not in HARD_FAIL_CODES)
    # Historical-exploit calibration. Adds a bonded bonus when the contract's
    # findings overlap with patterns that have caused real losses in the past.
    exploit_bonus = float(exploit_match.total_bonus) if exploit_match else 0.0
    raw_risk = float(weighted_total) + exploit_bonus
    # Soft cap: each weighted point worth ~1 risk-score point, capped at 95 to leave room for hard-fail.
    risk = min(95.0, raw_risk)
    if has_hard_fail:
        risk = max(risk, 90.0)

    tier = _tier_for(risk, has_hard_fail)
    action = ACTION_BY_TIER[tier]
    confidence, unknowns = _confidence(sf, df)

    summary: dict[str, Any] = {
        "weighted_finding_total": weighted_total,
        "hard_fail_codes": [f.code for f in findings if f.code in HARD_FAIL_CODES],
        "non_hard_fail_codes": [f.code for f in findings if f.code not in HARD_FAIL_CODES],
        "ruleset_weight_count": len(weights),
        "exploit_bonus": round(exploit_bonus, 3),
    }
    if exploit_match is not None:
        summary["exploit_calibration"] = exploit_match.as_dict()
    return Verdict(
        risk_score=round(risk, 2),
        confidence_score=round(confidence, 3),
        risk_tier=tier,
        action=action,
        summary=summary,
        unknowns=unknowns,
    )
