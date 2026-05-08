"""Scoring engine tests — tier boundaries + confidence decay."""

from __future__ import annotations

from app.models.finding import ContractFinding
from app.services.findings import HARD_FAIL_CODES
from app.services.scoring import score
from app.utils.time import utc_now


def _f(code: str, weight: int) -> ContractFinding:
    return ContractFinding(
        code=code, severity="high", weight=weight,
        evidence={}, source_type="static", created_at=utc_now(),
    )


def _features_full() -> tuple[dict, dict]:
    sf = {"source_verified": True, "is_proxy": False, "implementation_verified": None}
    df = {"has_liquidity": True, "holder_count": 100, "tx_count_1d": 10, "tx_count_7d": 50}
    return sf, df


def test_safe_with_no_findings() -> None:
    sf, df = _features_full()
    v = score(static_features=sf, dynamic_features=df, findings=[])
    assert v.risk_tier == "SAFE"
    assert v.action == "ALLOW"
    assert v.risk_score == 0.0


def test_caution_threshold() -> None:
    # Score uses ruleset weights, not f.weight: UPGRADEABLE_PROXY=12 + OWNER_CAN_CHANGE_FEES=13 = 25 → CAUTION.
    sf, df = _features_full()
    v = score(
        static_features=sf, dynamic_features=df,
        findings=[_f("UPGRADEABLE_PROXY", 12), _f("OWNER_CAN_CHANGE_FEES", 13)],
    )
    assert v.risk_tier == "CAUTION"


def test_high_risk_threshold() -> None:
    # OWNER_CAN_MINT=18 + BLACKLIST_FUNCTION=14 + UPGRADEABLE_PROXY=12 + TOP_HOLDER_CONCENTRATION_HIGH=14 = 58 → HIGH_RISK.
    sf, df = _features_full()
    v = score(
        static_features=sf, dynamic_features=df,
        findings=[
            _f("OWNER_CAN_MINT", 18),
            _f("BLACKLIST_FUNCTION", 14),
            _f("UPGRADEABLE_PROXY", 12),
            _f("TOP_HOLDER_CONCENTRATION_HIGH", 14),
        ],
    )
    assert v.risk_tier in ("HIGH_RISK", "CRITICAL")


def test_hard_fail_forces_critical() -> None:
    sf, df = _features_full()
    hf = HARD_FAIL_CODES[0]
    v = score(
        static_features=sf, dynamic_features=df,
        findings=[_f(hf, 100)],
    )
    assert v.risk_tier == "CRITICAL"
    assert v.action == "BLOCK"
    assert v.risk_score >= 90.0


def test_confidence_decay_unverified() -> None:
    sf = {"source_verified": False, "is_proxy": True, "implementation_verified": False}
    df = {"has_liquidity": None, "holder_count": None, "tx_count_1d": None, "tx_count_7d": None}
    v = score(static_features=sf, dynamic_features=df, findings=[])
    assert v.confidence_score < 0.8


def test_action_mapping_complete() -> None:
    sf, df = _features_full()
    safe = score(static_features=sf, dynamic_features=df, findings=[])
    assert safe.action == "ALLOW"
    crit = score(static_features=sf, dynamic_features=df, findings=[_f(HARD_FAIL_CODES[0], 100)])
    assert crit.action == "BLOCK"
