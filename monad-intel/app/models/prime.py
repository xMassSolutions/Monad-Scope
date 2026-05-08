"""Cached deep-analysis (Prime) results."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class PrimeAnalysis(Base):
    __tablename__ = "prime_analyses"
    __table_args__ = (
        Index("ix_pa_contract", "contract_id"),
        Index("ix_pa_impl_hash", "implementation_hash"),
        Index("ix_pa_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(String(40), ForeignKey("contracts.id"), nullable=False)
    implementation_hash: Mapped[str | None] = mapped_column(String(80))
    provider_name: Mapped[str] = mapped_column(String(64), nullable=False)
    prime_version: Mapped[str] = mapped_column(String(64), nullable=False)

    request_payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    public_visible: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
