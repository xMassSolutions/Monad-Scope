"""Prime API schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict

from app.schemas.common import PrimeState


class PrimeResultRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    provider_name: str
    prime_version: str
    attack_paths: list[dict[str, Any]]
    exploit_preconditions: list[str]
    likely_abuse_scenarios: list[str]
    blast_radius: dict[str, Any]
    mitigations: list[str]
    narrative_summary: str
    provider_metadata: dict[str, Any]
    created_at: datetime


class PrimeStatusBlock(BaseModel):
    """Always present in `ContractFull` — single canonical Prime block."""

    state: PrimeState
    price_usd: int
    job_id: str | None = None
    result: PrimeResultRead | None = None
    error: str | None = None


class PrimePurchaseRequest(BaseModel):
    """Server-side payment confirmation. Spec is silent on the payment provider,
    so we accept an opaque receipt id; replace with your real PSP integration.
    """

    payment_receipt: str
    requested_by: str | None = None  # opaque user identifier
