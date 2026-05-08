"""Block ledger row — one per Monad block we processed."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Block(Base):
    __tablename__ = "blocks"
    __table_args__ = (
        UniqueConstraint("number", name="uq_blocks_number"),
        Index("ix_blocks_processed_at", "processed_at"),
    )

    number: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    hash: Mapped[str] = mapped_column(String(80), nullable=False)
    parent_hash: Mapped[str | None] = mapped_column(String(80))
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    tx_count: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    contracts_created: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
