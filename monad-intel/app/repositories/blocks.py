"""Block ledger repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.block import Block
from app.utils.time import utc_now


async def upsert_block(
    session: AsyncSession,
    *,
    number: int,
    block_hash: str,
    parent_hash: str | None,
    timestamp: datetime,
    tx_count: int,
    contracts_created: int,
    processed_at: datetime | None = None,
) -> Block:
    values = dict(
        number=number,
        hash=block_hash,
        parent_hash=parent_hash,
        timestamp=timestamp,
        tx_count=tx_count,
        contracts_created=contracts_created,
        processed_at=processed_at or utc_now(),
    )
    dialect = session.bind.dialect.name if session.bind else "sqlite"
    insert = pg_insert if dialect == "postgresql" else sqlite_insert
    stmt = insert(Block).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=[Block.number],
        set_={
            "hash": stmt.excluded.hash,
            "parent_hash": stmt.excluded.parent_hash,
            "timestamp": stmt.excluded.timestamp,
            "tx_count": stmt.excluded.tx_count,
            "contracts_created": stmt.excluded.contracts_created,
            "processed_at": stmt.excluded.processed_at,
        },
    )
    await session.execute(stmt)
    res = await session.execute(select(Block).where(Block.number == number))
    return res.scalar_one()


async def get_max_processed_block(session: AsyncSession) -> int | None:
    res = await session.execute(select(Block.number).order_by(Block.number.desc()).limit(1))
    return res.scalar_one_or_none()


async def has_block(session: AsyncSession, number: int) -> bool:
    res = await session.execute(select(Block.number).where(Block.number == number))
    return res.first() is not None
