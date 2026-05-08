"""Deterministic mock provider — used in tests and dev."""

from __future__ import annotations

import hashlib

from app.services.deep_analysis.base import (
    DeepAnalysisProvider,
    NormalizedPrimeResult,
    PrimePayload,
)


class MockProvider(DeepAnalysisProvider):
    name = "mock"
    version = "1.0"

    async def analyze_contract(self, payload: PrimePayload) -> NormalizedPrimeResult:
        seed = hashlib.sha1(payload.address.encode("utf-8")).hexdigest()
        return NormalizedPrimeResult(
            attack_paths=[
                {
                    "name": "owner_grief",
                    "steps": [
                        "Owner calls setFee to 99%",
                        "Trade-out becomes economically infeasible",
                    ],
                    "preconditions": ["owner_can_change_fees"],
                    "severity": "high",
                }
            ] if payload.static_features.get("owner_can_change_fees") else [],
            exploit_preconditions=[k for k, v in payload.static_features.items() if v],
            likely_abuse_scenarios=[
                f"Deterministic mock scenario for {payload.address[:10]}…"
            ],
            blast_radius={"affected_users": "all_holders", "asset_loss": "tvl"},
            mitigations=[
                "Renounce ownership",
                "Lock liquidity",
                "Verify implementation source",
            ],
            narrative_summary=f"Mock deep analysis (seed={seed[:8]})",
            provider_metadata={"seed": seed, "model": "mock"},
        )
