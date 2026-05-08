"""Contract repository: shells, features, lookups."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

from sqlalchemy import and_, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.contract import Contract, ContractDynamicFeatures, ContractStaticFeatures
from app.utils.hashes import contract_key
from app.utils.ids import new_id
from app.utils.time import utc_now


def _insert(dialect: str):
    return pg_insert if dialect == "postgresql" else sqlite_insert


async def upsert_contract_shell(
    session: AsyncSession,
    *,
    chain: str,
    address: str,
    creator_address: str | None,
    creation_tx_hash: str | None,
    creation_block_number: int | None,
) -> Contract:
    address = address.lower()
    key = contract_key(address, chain)
    now = utc_now()
    dialect = session.bind.dialect.name if session.bind else "sqlite"
    insert = _insert(dialect)
    stmt = insert(Contract).values(
        id=new_id(),
        chain=chain,
        address=address,
        contract_key=key,
        creator_address=(creator_address or "").lower() or None,
        creation_tx_hash=creation_tx_hash,
        creation_block_number=creation_block_number,
        kind="unknown",
        first_seen_at=now,
        prime_available=False,
        is_proxy=False,
        verified=False,
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=[Contract.chain, Contract.address])
    await session.execute(stmt)
    res = await session.execute(
        select(Contract).where(Contract.chain == chain, Contract.address == address)
    )
    return res.scalar_one()


async def get_by_address(session: AsyncSession, address: str, chain: str = "monad") -> Contract | None:
    address = address.lower()
    res = await session.execute(
        select(Contract).where(Contract.chain == chain, Contract.address == address)
    )
    return res.scalar_one_or_none()


async def get_by_id(session: AsyncSession, contract_id: str) -> Contract | None:
    res = await session.execute(select(Contract).where(Contract.id == contract_id))
    return res.scalar_one_or_none()


async def update_enrichment(
    session: AsyncSession,
    contract_id: str,
    **fields: Any,
) -> None:
    if not fields:
        return
    fields.setdefault("last_refreshed_at", utc_now())
    await session.execute(
        update(Contract).where(Contract.id == contract_id).values(**fields)
    )


async def set_project(
    session: AsyncSession, contract_id: str, project_id: str | None
) -> None:
    await session.execute(
        update(Contract).where(Contract.id == contract_id).values(project_id=project_id)
    )


async def list_recent(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> list[Contract]:
    res = await session.execute(
        select(Contract).order_by(Contract.first_seen_at.desc()).limit(limit).offset(offset)
    )
    return list(res.scalars().all())


async def list_high_risk(
    session: AsyncSession, limit: int = 50, offset: int = 0
) -> list[Contract]:
    res = await session.execute(
        select(Contract)
        .where(Contract.risk_tier.in_(("HIGH_RISK", "CRITICAL")))
        .order_by(Contract.first_seen_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(res.scalars().all())


async def list_by_creator(session: AsyncSession, creator_address: str) -> list[Contract]:
    creator_address = creator_address.lower()
    res = await session.execute(
        select(Contract).where(Contract.creator_address == creator_address)
    )
    return list(res.scalars().all())


async def list_by_implementation_hash(session: AsyncSession, impl_hash: str) -> list[Contract]:
    res = await session.execute(
        select(Contract).where(Contract.implementation_hash == impl_hash)
    )
    return list(res.scalars().all())


async def list_due_for_refresh(
    session: AsyncSession, now: datetime, limit: int = 100
) -> list[Contract]:
    res = await session.execute(
        select(Contract)
        .where(or_(Contract.next_refresh_at == None, Contract.next_refresh_at <= now))  # noqa: E711
        .order_by(Contract.next_refresh_at.asc().nulls_first())
        .limit(limit)
    )
    return list(res.scalars().all())


# ---------------- features ----------------


async def upsert_static_features(
    session: AsyncSession, contract_id: str, features: dict[str, Any]
) -> None:
    dialect = session.bind.dialect.name if session.bind else "sqlite"
    insert = _insert(dialect)
    now = utc_now()
    stmt = insert(ContractStaticFeatures).values(
        contract_id=contract_id, features=features, extracted_at=now
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[ContractStaticFeatures.contract_id],
        set_={"features": stmt.excluded.features, "extracted_at": now},
    )
    await session.execute(stmt)


async def upsert_dynamic_features(
    session: AsyncSession, contract_id: str, features: dict[str, Any]
) -> None:
    dialect = session.bind.dialect.name if session.bind else "sqlite"
    insert = _insert(dialect)
    now = utc_now()
    stmt = insert(ContractDynamicFeatures).values(
        contract_id=contract_id, features=features, refreshed_at=now
    )
    stmt = stmt.on_conflict_do_update(
        index_elements=[ContractDynamicFeatures.contract_id],
        set_={"features": stmt.excluded.features, "refreshed_at": now},
    )
    await session.execute(stmt)


async def get_static_features(session: AsyncSession, contract_id: str) -> dict[str, Any]:
    res = await session.execute(
        select(ContractStaticFeatures.features).where(
            ContractStaticFeatures.contract_id == contract_id
        )
    )
    row = res.scalar_one_or_none()
    return dict(row or {})


async def get_dynamic_features(session: AsyncSession, contract_id: str) -> dict[str, Any]:
    res = await session.execute(
        select(ContractDynamicFeatures.features).where(
            ContractDynamicFeatures.contract_id == contract_id
        )
    )
    row = res.scalar_one_or_none()
    return dict(row or {})


async def count_creator_launches(session: AsyncSession, creator: str) -> int:
    creator = creator.lower()
    res = await session.execute(
        select(Contract.id).where(Contract.creator_address == creator)
    )
    return len(res.scalars().all())
