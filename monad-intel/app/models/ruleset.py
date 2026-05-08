"""Versioned scoring rulesets. The active row drives production scoring."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Ruleset(Base):
    __tablename__ = "rulesets"
    __table_args__ = (
        UniqueConstraint("version", name="uq_rulesets_version"),
        Index("ix_rulesets_status", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    weights_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    metrics_json: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    # one of: active, proposed, shadow, archived
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="proposed")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
