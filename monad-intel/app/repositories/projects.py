"""Project repository."""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.project import Project, ProjectContractLink
from app.utils.ids import new_id
from app.utils.text import slugify
from app.utils.time import utc_now


def _insert(dialect: str):
    return pg_insert if dialect == "postgresql" else sqlite_insert


async def get_by_id(session: AsyncSession, project_id: str) -> Project | None:
    res = await session.execute(select(Project).where(Project.id == project_id))
    return res.scalar_one_or_none()


async def get_by_slug(session: AsyncSession, slug: str) -> Project | None:
    res = await session.execute(select(Project).where(Project.slug == slug))
    return res.scalar_one_or_none()


async def get_or_create(
    session: AsyncSession,
    *,
    canonical_name: str,
    creator_cluster: str | None = None,
    status: str = "watchlist",
) -> Project:
    base_slug = slugify(canonical_name) or "unnamed"
    # Suffix the slug with a short id chunk to avoid collisions across clusters.
    slug = base_slug
    existing = await get_by_slug(session, slug)
    if existing is not None:
        slug = f"{base_slug}-{new_id().split('-')[0]}"

    now = utc_now()
    project = Project(
        id=new_id(),
        canonical_name=canonical_name,
        slug=slug,
        status=status,
        creator_cluster=creator_cluster,
        first_seen_at=now,
        last_seen_at=now,
    )
    session.add(project)
    await session.flush()
    return project


async def touch_last_seen(session: AsyncSession, project_id: str) -> None:
    await session.execute(
        update(Project).where(Project.id == project_id).values(last_seen_at=utc_now())
    )


async def set_status(session: AsyncSession, project_id: str, status: str) -> None:
    await session.execute(
        update(Project).where(Project.id == project_id).values(status=status)
    )


async def link_contract(
    session: AsyncSession,
    *,
    project_id: str,
    contract_id: str,
    role: str | None,
    confidence: float,
) -> None:
    dialect = session.bind.dialect.name if session.bind else "sqlite"
    insert = _insert(dialect)
    stmt = insert(ProjectContractLink).values(
        project_id=project_id,
        contract_id=contract_id,
        role=role,
        confidence=confidence,
        created_at=utc_now(),
    )
    stmt = stmt.on_conflict_do_nothing(index_elements=["project_id", "contract_id"])
    await session.execute(stmt)


async def list_contract_ids(session: AsyncSession, project_id: str) -> list[str]:
    res = await session.execute(
        select(ProjectContractLink.contract_id).where(
            ProjectContractLink.project_id == project_id
        )
    )
    return list(res.scalars().all())
