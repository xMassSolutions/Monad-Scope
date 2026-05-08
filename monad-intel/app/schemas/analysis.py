"""Analysis + finding API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.common import Action, AnalysisStage, RiskTier, Severity


class FindingRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    code: str
    severity: Severity
    weight: int
    evidence: dict[str, Any]
    source_type: str
    created_at: datetime


class AnalysisRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    analysis_version: int
    risk_score: float
    confidence_score: float
    risk_tier: RiskTier
    action: Action
    analysis_stage: AnalysisStage
    summary_json: dict[str, Any]
    unknowns_json: dict[str, Any]
    created_at: datetime
