"""Per-contract findings (typed evidence-bearing records)."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class ContractFinding(Base):
    __tablename__ = "contract_findings"
    __table_args__ = (
        Index("ix_cf_contract", "contract_id"),
        Index("ix_cf_code", "code"),
        Index("ix_cf_created_at", "created_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(String(40), ForeignKey("contracts.id"), nullable=False)
    code: Mapped[str] = mapped_column(String(64), nullable=False)
    severity: Mapped[str] = mapped_column(String(16), nullable=False)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    evidence: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    source_type: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
