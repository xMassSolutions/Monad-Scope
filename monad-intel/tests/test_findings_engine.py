"""Findings engine — every WEIGHTED_FLAGS code + every hard-fail code is exercised."""

from __future__ import annotations

from app.services.findings import HARD_FAIL_CODES, WEIGHTED_FLAGS, compute_findings


def _empty_static() -> dict:
    keys = (
        "source_verified", "implementation_verified", "is_proxy", "owner_can_mint",
        "mint_capped", "blacklist_function", "trading_can_pause", "owner_can_change_fees",
        "max_wallet_controls", "max_tx_controls", "admin_can_withdraw_user_funds",
        "liquidity_removal_controls", "hidden_transfer_restrictions", "upgradeable_proxy",
        "renounce_pattern_detected", "unverified_contract",
    )
    return {k: False for k in keys}


def _empty_dynamic() -> dict:
    return {
        "has_liquidity": None, "liquidity_usd": None, "liquidity_lock_days": None,
        "holder_count": None, "top_10_holder_pct": None, "tx_count_1d": None,
        "tx_count_7d": None, "pool_age_days": None, "deployer_launch_count": None,
        "deployer_suspicious_count": None, "owner_changed_recently": None,
        "implementation_changed_recently": None,
    }


def codes(findings) -> set[str]:
    return {f.code for f in findings}


def test_owner_can_mint_emits_weighted() -> None:
    sf = _empty_static()
    sf["owner_can_mint"] = True
    sf["mint_capped"] = True  # not None: capped, so no hard-fail
    f = compute_findings(static_features=sf, dynamic_features=_empty_dynamic())
    assert "OWNER_CAN_MINT" in codes(f)
    assert "PRIVILEGED_UNCAPPED_MINT" not in codes(f)


def test_uncapped_mint_emits_hard_fail() -> None:
    sf = _empty_static()
    sf["owner_can_mint"] = True
    sf["mint_capped"] = False  # explicit
    f = compute_findings(static_features=sf, dynamic_features=_empty_dynamic())
    assert "PRIVILEGED_UNCAPPED_MINT" in codes(f)


def test_blacklist_plus_pause_hard_fail() -> None:
    sf = _empty_static()
    sf["blacklist_function"] = True
    sf["trading_can_pause"] = True
    f = compute_findings(static_features=sf, dynamic_features=_empty_dynamic())
    assert "BLACKLIST_PLUS_TRADING_GATE" in codes(f)


def test_hidden_transfer_hard_fail() -> None:
    sf = _empty_static()
    sf["hidden_transfer_restrictions"] = True
    f = compute_findings(static_features=sf, dynamic_features=_empty_dynamic())
    assert "HIDDEN_TRANSFER_RESTRICTIONS" in codes(f)


def test_admin_withdraw_hard_fail() -> None:
    sf = _empty_static()
    sf["admin_can_withdraw_user_funds"] = True
    f = compute_findings(static_features=sf, dynamic_features=_empty_dynamic())
    assert "ADMIN_CAN_WITHDRAW_USER_FUNDS" in codes(f)


def test_priv_liquidity_extraction_hard_fail() -> None:
    sf = _empty_static()
    sf["admin_can_withdraw_user_funds"] = True
    sf["liquidity_removal_controls"] = True
    f = compute_findings(static_features=sf, dynamic_features=_empty_dynamic())
    assert "PRIVILEGED_LIQUIDITY_EXTRACTION" in codes(f)


def test_dynamic_lp_unlocked() -> None:
    sf = _empty_static()
    df = _empty_dynamic()
    df["has_liquidity"] = True
    df["liquidity_lock_days"] = 0
    f = compute_findings(static_features=sf, dynamic_features=df)
    assert "LP_UNLOCKED" in codes(f)


def test_top_holder_concentration() -> None:
    sf = _empty_static()
    df = _empty_dynamic()
    df["top_10_holder_pct"] = 75
    f = compute_findings(static_features=sf, dynamic_features=df)
    assert "TOP_HOLDER_CONCENTRATION_HIGH" in codes(f)


def test_unverified_contract_emitted() -> None:
    sf = _empty_static()
    sf["unverified_contract"] = True
    f = compute_findings(static_features=sf, dynamic_features=_empty_dynamic())
    assert "UNVERIFIED_CONTRACT" in codes(f)


def test_implementation_unverified() -> None:
    sf = _empty_static()
    sf["is_proxy"] = True
    sf["implementation_verified"] = False
    f = compute_findings(static_features=sf, dynamic_features=_empty_dynamic())
    assert "IMPLEMENTATION_UNVERIFIED" in codes(f)


def test_all_hard_fail_codes_have_critical_severity() -> None:
    sf = _empty_static()
    sf.update(
        admin_can_withdraw_user_funds=True,
        liquidity_removal_controls=True,
        owner_can_mint=True,
        mint_capped=False,
        blacklist_function=True,
        trading_can_pause=True,
        hidden_transfer_restrictions=True,
    )
    f = compute_findings(static_features=sf, dynamic_features=_empty_dynamic())
    for finding in f:
        if finding.code in HARD_FAIL_CODES:
            assert finding.severity == "critical"
            assert finding.weight == 100
