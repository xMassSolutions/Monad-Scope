"""Local provider — synthesizes a deep-analysis result from existing free signals.

Used in production when no external AI provider is configured. Charges nothing.
Returns a useful narrative built mechanically from findings + features so the
public API has a well-formed Prime block even without a paid model.
"""

from __future__ import annotations

from app.services.deep_analysis.base import (
    DeepAnalysisProvider,
    NormalizedPrimeResult,
    PrimePayload,
)


class LocalProvider(DeepAnalysisProvider):
    name = "local"
    version = "1.0"

    async def analyze_contract(self, payload: PrimePayload) -> NormalizedPrimeResult:
        sf = payload.static_features
        df = payload.dynamic_features

        attack_paths: list[dict] = []
        if sf.get("owner_can_mint"):
            attack_paths.append({
                "name": "owner_mint_dilution",
                "steps": ["Owner calls mint to self", "Existing holders are diluted"],
                "preconditions": ["owner_can_mint"],
                "severity": "high",
            })
        if sf.get("upgradeable_proxy"):
            attack_paths.append({
                "name": "upgrade_swap",
                "steps": [
                    "Admin calls upgradeTo with malicious implementation",
                    "User calls forwarded to malicious logic",
                ],
                "preconditions": ["upgradeable_proxy"],
                "severity": "critical",
            })
        if sf.get("admin_can_withdraw_user_funds"):
            attack_paths.append({
                "name": "rugpull_withdraw",
                "steps": ["Admin calls withdrawTo to drain pool"],
                "preconditions": ["admin_can_withdraw_user_funds"],
                "severity": "critical",
            })

        preconditions = sorted({k for k, v in sf.items() if v is True})
        scenarios: list[str] = []
        if df.get("top_10_holder_pct") and df["top_10_holder_pct"] >= 60:
            scenarios.append("Concentrated holders coordinate exit, draining liquidity.")
        if sf.get("blacklist_function") and sf.get("trading_can_pause"):
            scenarios.append("Blacklist + pause used in tandem to honeypot late buyers.")

        mitigations = []
        if sf.get("upgradeable_proxy"):
            mitigations.append("Verify implementation source on every upgrade.")
        if not sf.get("source_verified"):
            mitigations.append("Require source verification before listing.")
        if df.get("liquidity_lock_days") is not None and df["liquidity_lock_days"] < 1:
            mitigations.append("Lock liquidity for >= 30 days.")

        narrative = (
            f"Local deterministic deep-analysis for {payload.address}. "
            f"Risk={payload.risk_score} confidence={payload.confidence_score}. "
            f"{len(payload.findings)} free findings considered."
        )

        return NormalizedPrimeResult(
            attack_paths=attack_paths,
            exploit_preconditions=preconditions,
            likely_abuse_scenarios=scenarios,
            blast_radius={
                "affected_users": "holders" if sf.get("owner_can_mint") else "interactors",
                "asset_loss": "partial" if not sf.get("admin_can_withdraw_user_funds") else "total",
            },
            mitigations=mitigations,
            narrative_summary=narrative,
            provider_metadata={"model": "local-deterministic"},
        )
