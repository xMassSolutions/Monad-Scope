"""Contract + static/dynamic feature rows."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Contract(Base):
    __tablename__ = "contracts"
    __table_args__ = (
        UniqueConstraint("chain", "address", name="uq_contracts_chain_address"),
        UniqueConstraint("contract_key", name="uq_contracts_key"),
        Index("ix_contracts_creator", "creator_address"),
        Index("ix_contracts_kind", "kind"),
        Index("ix_contracts_risk_tier", "risk_tier"),
        Index("ix_contracts_first_seen_at", "first_seen_at"),
        Index("ix_contracts_next_refresh_at", "next_refresh_at"),
        Index("ix_contracts_implementation_hash", "implementation_hash"),
        Index("ix_contracts_bytecode_hash", "bytecode_hash"),
    )

    id: Mapped[str] = mapped_column(String(40), primary_key=True)
    chain: Mapped[str] = mapped_column(String(32), nullable=False, default="monad")
    address: Mapped[str] = mapped_column(String(64), nullable=False)
    contract_key: Mapped[str] = mapped_column(String(96), nullable=False)

    creator_address: Mapped[str | None] = mapped_column(String(64))
    creation_tx_hash: Mapped[str | None] = mapped_column(String(80))
    creation_block_number: Mapped[int | None] = mapped_column(BigInteger)

    bytecode_hash: Mapped[str | None] = mapped_column(String(80))
    implementation_hash: Mapped[str | None] = mapped_column(String(80))

    verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verifier_source: Mapped[str | None] = mapped_column(String(32))
    contract_name: Mapped[str | None] = mapped_column(String(128))
    symbol: Mapped[str | None] = mapped_column(String(64))

    is_proxy: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    implementation_address: Mapped[str | None] = mapped_column(String(64))

    kind: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    project_id: Mapped[str | None] = mapped_column(String(40), ForeignKey("projects.id"))

    risk_score: Mapped[float | None] = mapped_column(Float)
    confidence_score: Mapped[float | None] = mapped_column(Float)
    risk_tier: Mapped[str | None] = mapped_column(String(16))
    action: Mapped[str | None] = mapped_column(String(16))
    analysis_stage: Mapped[str | None] = mapped_column(String(16))

    prime_available: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)

    first_seen_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_refreshed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    next_refresh_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class ContractStaticFeatures(Base):
    __tablename__ = "contract_static_features"
    __table_args__ = (
        UniqueConstraint("contract_id", name="uq_csf_contract"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(String(40), ForeignKey("contracts.id"), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    extracted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class ContractDynamicFeatures(Base):
    __tablename__ = "contract_dynamic_features"
    __table_args__ = (
        UniqueConstraint("contract_id", name="uq_cdf_contract"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    contract_id: Mapped[str] = mapped_column(String(40), ForeignKey("contracts.id"), nullable=False)
    features: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    refreshed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
