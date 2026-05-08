"""Projects and the contract <-> project link."""

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
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Project(Base):
    __tablename__ = "projects"
    __table_args__ = (
        UniqueConstraint("slug", name="uq_projects_slug"),
        Index("ix_projects_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    canonical_name: Mapped[str] = mapped_column(String(128), nullable=False)
    slug: Mapped[str] = mapped_column(String(128), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="watchlist")

    creator_cluster: Mapped[str | None] = mapped_column(String(96))
    website: Mapped[str | None] = mapped_column(String(256))
    socials: Mapped[dict[str, Any] | None] = mapped_column(JSON)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ProjectContractLink(Base):
    __tablename__ = "project_contract_links"
    __table_args__ = (
        UniqueConstraint("project_id", "contract_id", name="uq_pcl_project_contract"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    project_id: Mapped[str] = mapped_column(String(40), ForeignKey("projects.id"), nullable=False)
    contract_id: Mapped[str] = mapped_column(String(40), ForeignKey("contracts.id"), nullable=False)
    role: Mapped[str | None] = mapped_column(String(32))
    confidence: Mapped[float | None] = mapped_column()
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
