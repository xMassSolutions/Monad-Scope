"""Versioned per-contract analysis snapshots."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ContractAnalysis(Base):
    __tablename__ = "contract_analyses"
    __table_args__ = (
        Index("ix_ca_contract", "contract_id"),
        Index("ix_ca_created_at", "created_at"),
        Index("ix_ca_stage", "analysis_stage"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(String(40), ForeignKey("contracts.id"), nullable=False)
    analysis_version: Mapped[int] = mapped_column(Integer, nullable=False)

    risk_score: Mapped[float] = mapped_column(Float, nullable=False)
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    risk_tier: Mapped[str] = mapped_column(String(16), nullable=False)
    action: Mapped[str] = mapped_column(String(16), nullable=False)

    summary_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    unknowns_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    analysis_stage: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
