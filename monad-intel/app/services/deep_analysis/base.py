"""Provider Protocol + normalized result schema.

This is the contract every provider must satisfy. The manager + workers code
talks only in terms of this Protocol — never about specific vendors.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass
class PrimePayload:
    """Built by `prime_state.build_payload` from per-contract data."""

    chain: str
    address: str
    contract_name: str | None
    verified: bool
    verified_source: str | None
    implementation_address: str | None
    implementation_source: str | None
    static_features: dict[str, Any]
    dynamic_features: dict[str, Any]
    findings: list[dict[str, Any]]
    risk_score: float | None
    confidence_score: float | None
    task_instruction: str


@dataclass
class NormalizedPrimeResult:
    """Fixed shape — every provider must produce this. Drives the public API."""

    attack_paths: list[dict[str, Any]] = field(default_factory=list)
    exploit_preconditions: list[str] = field(default_factory=list)
    likely_abuse_scenarios: list[str] = field(default_factory=list)
    blast_radius: dict[str, Any] = field(default_factory=dict)
    mitigations: list[str] = field(default_factory=list)
    narrative_summary: str = ""
    provider_metadata: dict[str, Any] = field(default_factory=dict)


class DeepAnalysisProvider(Protocol):
    name: str
    version: str

    async def analyze_contract(self, payload: PrimePayload) -> NormalizedPrimeResult: ...
