"""Contract API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.analysis import AnalysisRead, FindingRead
from app.schemas.common import Action, AnalysisStage, ContractKind, RiskTier
from app.schemas.prime import PrimeStatusBlock


class ContractRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    chain: str
    address: str
    contract_key: str
    creator_address: str | None
    creation_tx_hash: str | None
    creation_block_number: int | None
    bytecode_hash: str | None
    implementation_hash: str | None
    verified: bool
    verifier_source: str | None
    contract_name: str | None
    symbol: str | None
    is_proxy: bool
    implementation_address: str | None
    kind: ContractKind
    project_id: str | None
    risk_score: float | None
    confidence_score: float | None
    risk_tier: RiskTier | None
    action: Action | None
    analysis_stage: AnalysisStage | None
    prime_available: bool
    first_seen_at: datetime
    last_refreshed_at: datetime | None
    next_refresh_at: datetime | None


class ContractFull(BaseModel):
    """Unified payload — single source of truth for the contract page.

    The Prime block is always present so the UI never needs an extra request.
    """

    contract: ContractRead
    static_features: dict[str, Any]
    dynamic_features: dict[str, Any]
    findings: list[FindingRead]
    latest_analysis: AnalysisRead | None
    prime: PrimeStatusBlock
