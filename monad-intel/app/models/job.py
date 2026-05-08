"""Async job rows. Used for Prime jobs, rescans, recalibration runs."""

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


class Job(Base):
    __tablename__ = "jobs"
    __table_args__ = (
        # Only one active job per (kind, dedup_key) at a time. NULL dedup_key
        # is allowed multiple times; uniqueness is enforced via partial index
        # in PG; on SQLite the unique constraint still works because NULLs
        # don't conflict.
        UniqueConstraint("kind", "dedup_key", "active_marker", name="uq_jobs_active"),
        Index("ix_jobs_status", "status"),
        Index("ix_jobs_kind", "kind"),
        Index("ix_jobs_created_at", "created_at"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    kind: Mapped[str] = mapped_column(String(32), nullable=False)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="queued")
    # `active_marker` is set to 1 when status in (queued, running) and NULL when
    # finished — together with `dedup_key` this enforces "one active job per key".
    active_marker: Mapped[int | None] = mapped_column(Integer)
    dedup_key: Mapped[str | None] = mapped_column(String(128))
    payload: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    result: Mapped[dict[str, Any] | None] = mapped_column(JSON)
    error: Mapped[str | None] = mapped_column(String(2048))

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
