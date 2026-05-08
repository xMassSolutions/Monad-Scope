"""Findings engine.

Inputs:
- static_features: dict (see feature_static.STATIC_FEATURE_KEYS)
- dynamic_features: dict (see feature_dynamic.DYNAMIC_FEATURE_KEYS)
- ruleset weights (mapping from finding code -> weight)

Outputs: list[ContractFinding] ORM rows (not yet attached to a session).

Hard-fail findings are emitted with severity="critical" and weight=100; they
trigger the CRITICAL tier in scoring. Weighted findings carry their ruleset
weight; severity is derived from weight bands.
"""

from __future__ import annotations

from typing import Any

from app.models.finding import ContractFinding
from app.utils.time import utc_now


# The starter weighted rule set. Persisted as ruleset v1 on first boot.
WEIGHTED_FLAGS: dict[str, int] = {
    "OWNER_CAN_MINT": 18,
    "BLACKLIST_FUNCTION": 14,
    "TRADING_CAN_PAUSE": 10,
    "OWNER_CAN_CHANGE_FEES": 13,
    "MAX_WALLET_CONTROLS": 6,
    "MAX_TX_CONTROLS": 5,
    "UPGRADEABLE_PROXY": 12,
    "UNVERIFIED_CONTRACT": 8,
    "IMPLEMENTATION_UNVERIFIED": 10,
    "LP_UNLOCKED": 15,
    "TOP_HOLDER_CONCENTRATION_HIGH": 14,
    "DEPLOYER_REUSED_SUSPICIOUS_BYTECODE": 12,
    "OWNER_CHANGED_RECENTLY": 8,
    "IMPLEMENTATION_CHANGED_RECENTLY": 10,
}

HARD_FAIL_CODES = (
    "ADMIN_CAN_WITHDRAW_USER_FUNDS",
    "PRIVILEGED_UNCAPPED_MINT",
    "BLACKLIST_PLUS_TRADING_GATE",
    "HIDDEN_TRANSFER_RESTRICTIONS",
    "PRIVILEGED_LIQUIDITY_EXTRACTION",
)


# Vulnerability taxonomy — broad categories drawn from the SlowMist
# Blockchain Common Vulnerability List. Each entry pairs a MonadScope
# finding code with the SlowMist category it represents and a short
# description. Codes prefixed with `*` lack a static detector today but are
# valid targets for exploit-feed mapping (so historical exploits still
# calibrate them, and a future detector inherits the calibration).
VULNERABILITY_TAXONOMY: dict[str, dict[str, str]] = {
    "OWNER_CAN_MINT": {
        "category": "Privilege Escalation",
        "description": "Owner has uncapped mint access — direct path to dilution attacks.",
    },
    "PRIVILEGED_UNCAPPED_MINT": {
        "category": "Privilege Escalation",
        "description": "Mint privilege with no enforced cap — historically the root of many infinite-mint exploits.",
    },
    "BLACKLIST_FUNCTION": {
        "category": "Privilege Escalation",
        "description": "Owner can blacklist holders, locking funds in place.",
    },
    "TRADING_CAN_PAUSE": {
        "category": "Privilege Escalation",
        "description": "Owner can globally halt all transfers.",
    },
    "OWNER_CAN_CHANGE_FEES": {
        "category": "Privilege Escalation",
        "description": "Tax / fee parameters mutable by the owner — soft rug vector.",
    },
    "ADMIN_CAN_WITHDRAW_USER_FUNDS": {
        "category": "Access Control",
        "description": "Privileged role can drain user balances.",
    },
    "BLACKLIST_PLUS_TRADING_GATE": {
        "category": "Honeypot",
        "description": "Blacklist combined with global pause = canonical honeypot.",
    },
    "HIDDEN_TRANSFER_RESTRICTIONS": {
        "category": "Honeypot",
        "description": "Transfer paths gated by hidden allowlists or runtime checks.",
    },
    "PRIVILEGED_LIQUIDITY_EXTRACTION": {
        "category": "Rug Pull",
        "description": "Owner-callable liquidity removal — terminal rug risk.",
    },
    "LP_UNLOCKED": {
        "category": "Rug Pull",
        "description": "Liquidity pool tokens are not time-locked.",
    },
    "TOP_HOLDER_CONCENTRATION_HIGH": {
        "category": "Centralisation",
        "description": "A few wallets hold disproportionate supply.",
    },
    "UPGRADEABLE_PROXY": {
        "category": "Upgradeability",
        "description": "Logic can be hot-swapped by the proxy admin.",
    },
    "IMPLEMENTATION_UNVERIFIED": {
        "category": "Upgradeability",
        "description": "Proxy points at unverified bytecode — opaque logic.",
    },
    "IMPLEMENTATION_CHANGED_RECENTLY": {
        "category": "Upgradeability",
        "description": "Implementation pointer mutated within the rolling window.",
    },
    "UNVERIFIED_CONTRACT": {
        "category": "Verification",
        "description": "Source not published; static analysis is bytecode-only.",
    },
    "DEPLOYER_REUSED_SUSPICIOUS_BYTECODE": {
        "category": "Reputation",
        "description": "Deployer address has shipped flagged contracts before.",
    },
    "OWNER_CHANGED_RECENTLY": {
        "category": "Key Compromise",
        "description": "Ownership transfer within the rolling window — possible key-loss event.",
    },
    "MAX_WALLET_CONTROLS": {
        "category": "Trading Restrictions",
        "description": "Per-wallet holding caps configurable by owner.",
    },
    "MAX_TX_CONTROLS": {
        "category": "Trading Restrictions",
        "description": "Per-transaction caps configurable by owner.",
    },
    # SlowMist-derived: no static detector yet, but historical exploits
    # mapping to these codes still feed the calibration so they are ready
    # for the day a detector is added.
    "*ORACLE_PRICE_MANIPULATION": {
        "category": "Oracle",
        "description": "Single-source or flash-loan-manipulable price feed (SlowMist: Oracle Price Manipulation).",
    },
    "*MEV_VULNERABILITY": {
        "category": "MEV",
        "description": "Logic susceptible to front-running, sandwiching, or ordering attacks (SlowMist: MEV).",
    },
    "*CROSS_CHAIN_VERIFICATION_WEAK": {
        "category": "Cross-chain",
        "description": "Bridge message verification is forgeable (SlowMist: Forged Cross-Chain Message).",
    },
    "*FALSE_TOPUP_VULNERABILITY": {
        "category": "Accounting",
        "description": "Receipt parser does not validate token movement vs metadata (SlowMist: False Top-Up).",
    },
    "*TRANSACTION_REPLAY": {
        "category": "Replay",
        "description": "Missing nonce / chain-id binding allows replay across chains or branches (SlowMist: Replay Attack).",
    },
}


def _severity_for_weight(w: int) -> str:
    if w >= 100:
        return "critical"
    if w >= 14:
        return "high"
    if w >= 10:
        return "medium"
    if w >= 6:
        return "low"
    return "info"


def _make(
    *,
    code: str,
    weight: int,
    evidence: dict[str, Any],
    source_type: str,
) -> ContractFinding:
    return ContractFinding(
        code=code,
        severity=_severity_for_weight(weight),
        weight=weight,
        evidence=evidence,
        source_type=source_type,
        created_at=utc_now(),
    )


def compute_findings(
    *,
    static_features: dict[str, Any],
    dynamic_features: dict[str, Any],
    weights: dict[str, int] | None = None,
) -> list[ContractFinding]:
    weights = {**WEIGHTED_FLAGS, **(weights or {})}
    sf, df = static_features or {}, dynamic_features or {}
    out: list[ContractFinding] = []

    def w(code: str) -> int:
        return int(weights.get(code, WEIGHTED_FLAGS.get(code, 0)))

    # ---------- HARD-FAIL ----------
    if sf.get("admin_can_withdraw_user_funds"):
        out.append(_make(
            code="ADMIN_CAN_WITHDRAW_USER_FUNDS",
            weight=100,
            evidence={"source": "static", "feature": "admin_can_withdraw_user_funds"},
            source_type="static",
        ))

    if sf.get("owner_can_mint") and sf.get("mint_capped") is False:
        # Capped is False (explicit) — we know there is no cap.
        out.append(_make(
            code="PRIVILEGED_UNCAPPED_MINT",
            weight=100,
            evidence={"source": "static", "owner_can_mint": True, "mint_capped": False},
            source_type="static",
        ))

    if sf.get("blacklist_function") and sf.get("trading_can_pause"):
        out.append(_make(
            code="BLACKLIST_PLUS_TRADING_GATE",
            weight=100,
            evidence={"source": "static", "blacklist_function": True, "trading_can_pause": True},
            source_type="static",
        ))

    if sf.get("hidden_transfer_restrictions"):
        out.append(_make(
            code="HIDDEN_TRANSFER_RESTRICTIONS",
            weight=100,
            evidence={"source": "static", "feature": "hidden_transfer_restrictions"},
            source_type="static",
        ))

    if sf.get("liquidity_removal_controls") and sf.get("admin_can_withdraw_user_funds"):
        out.append(_make(
            code="PRIVILEGED_LIQUIDITY_EXTRACTION",
            weight=100,
            evidence={"source": "static", "liquidity_removal_controls": True},
            source_type="static",
        ))

    # ---------- WEIGHTED (static) ----------
    if sf.get("owner_can_mint"):
        out.append(_make(
            code="OWNER_CAN_MINT",
            weight=w("OWNER_CAN_MINT"),
            evidence={"feature": "owner_can_mint"},
            source_type="static",
        ))

    if sf.get("blacklist_function"):
        out.append(_make(
            code="BLACKLIST_FUNCTION",
            weight=w("BLACKLIST_FUNCTION"),
            evidence={"feature": "blacklist_function"},
            source_type="static",
        ))

    if sf.get("trading_can_pause"):
        out.append(_make(
            code="TRADING_CAN_PAUSE",
            weight=w("TRADING_CAN_PAUSE"),
            evidence={"feature": "trading_can_pause"},
            source_type="static",
        ))

    if sf.get("owner_can_change_fees"):
        out.append(_make(
            code="OWNER_CAN_CHANGE_FEES",
            weight=w("OWNER_CAN_CHANGE_FEES"),
            evidence={"feature": "owner_can_change_fees"},
            source_type="static",
        ))

    if sf.get("max_wallet_controls"):
        out.append(_make(
            code="MAX_WALLET_CONTROLS",
            weight=w("MAX_WALLET_CONTROLS"),
            evidence={"feature": "max_wallet_controls"},
            source_type="static",
        ))

    if sf.get("max_tx_controls"):
        out.append(_make(
            code="MAX_TX_CONTROLS",
            weight=w("MAX_TX_CONTROLS"),
            evidence={"feature": "max_tx_controls"},
            source_type="static",
        ))

    if sf.get("upgradeable_proxy"):
        out.append(_make(
            code="UPGRADEABLE_PROXY",
            weight=w("UPGRADEABLE_PROXY"),
            evidence={"feature": "upgradeable_proxy"},
            source_type="static",
        ))

    if sf.get("unverified_contract"):
        out.append(_make(
            code="UNVERIFIED_CONTRACT",
            weight=w("UNVERIFIED_CONTRACT"),
            evidence={"feature": "unverified_contract"},
            source_type="static",
        ))

    if sf.get("is_proxy") and sf.get("implementation_verified") is False:
        out.append(_make(
            code="IMPLEMENTATION_UNVERIFIED",
            weight=w("IMPLEMENTATION_UNVERIFIED"),
            evidence={"feature": "implementation_verified", "value": False},
            source_type="static",
        ))

    # ---------- WEIGHTED (dynamic) ----------
    liq_locked_days = df.get("liquidity_lock_days")
    if df.get("has_liquidity") and (liq_locked_days is not None and liq_locked_days < 1):
        out.append(_make(
            code="LP_UNLOCKED",
            weight=w("LP_UNLOCKED"),
            evidence={"liquidity_lock_days": liq_locked_days},
            source_type="dynamic",
        ))

    top10 = df.get("top_10_holder_pct")
    if top10 is not None and top10 >= 60:
        out.append(_make(
            code="TOP_HOLDER_CONCENTRATION_HIGH",
            weight=w("TOP_HOLDER_CONCENTRATION_HIGH"),
            evidence={"top_10_holder_pct": top10},
            source_type="dynamic",
        ))

    susp = df.get("deployer_suspicious_count")
    if susp is not None and susp > 0:
        out.append(_make(
            code="DEPLOYER_REUSED_SUSPICIOUS_BYTECODE",
            weight=w("DEPLOYER_REUSED_SUSPICIOUS_BYTECODE"),
            evidence={"deployer_suspicious_count": susp},
            source_type="dynamic",
        ))

    if df.get("owner_changed_recently"):
        out.append(_make(
            code="OWNER_CHANGED_RECENTLY",
            weight=w("OWNER_CHANGED_RECENTLY"),
            evidence={"window_days": 2},
            source_type="dynamic",
        ))

    if df.get("implementation_changed_recently"):
        out.append(_make(
            code="IMPLEMENTATION_CHANGED_RECENTLY",
            weight=w("IMPLEMENTATION_CHANGED_RECENTLY"),
            evidence={"window_days": 2},
            source_type="dynamic",
        ))

    return out
