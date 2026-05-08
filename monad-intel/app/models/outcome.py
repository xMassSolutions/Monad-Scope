"""Ground-truth outcomes labeled by humans. Drives recalibration."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Outcome(Base):
    __tablename__ = "outcomes"
    __table_args__ = (
        Index("ix_outcomes_contract", "contract_id"),
        Index("ix_outcomes_project", "project_id"),
        Index("ix_outcomes_label", "outcome_label"),
        Index("ix_outcomes_updated_at", "updated_at"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("contracts.id"))
    project_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("projects.id"))
    outcome_label: Mapped[str] = mapped_column(String(32), nullable=False)
    notes: Mapped[str | None] = mapped_column(String(2048))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
