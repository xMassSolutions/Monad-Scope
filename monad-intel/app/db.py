"""Async SQLAlchemy engine, session factory, and Base."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import AsyncIterator

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings


class Base(DeclarativeBase):
    """Single declarative Base for all ORM models. Alembic-ready."""


_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[AsyncSession] | None = None


def get_engine() -> AsyncEngine:
    global _engine
    if _engine is None:
        settings = get_settings()

        connect_args: dict = {}
        # If using Postgres, set the search_path so all queries land in the
        # configured schema (default "monadscope"). Lets us share a Supabase
        # project with other apps without table-name collisions. SQLite
        # ignores this (and asyncpg doesn't accept "options").
        is_pg = settings.database_url.startswith(("postgres", "postgresql"))
        if is_pg:
            schema = (
                getattr(settings, "database_schema", None)
                or os.getenv("DATABASE_SCHEMA")
                or "monadscope"
            )
            # asyncpg uses server_settings rather than libpq "options".
            connect_args["server_settings"] = {"search_path": f"{schema},public"}

        _engine = create_async_engine(
            settings.database_url,
            echo=settings.database_echo,
            pool_pre_ping=True,
            future=True,
            connect_args=connect_args,
        )
    return _engine


def get_session_factory() -> async_sessionmaker[AsyncSession]:
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            expire_on_commit=False,
            autoflush=False,
            class_=AsyncSession,
        )
    return _session_factory


@asynccontextmanager
async def session_scope() -> AsyncIterator[AsyncSession]:
    """Use in worker code: `async with session_scope() as s: ...`."""
    sf = get_session_factory()
    async with sf() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


async def get_session() -> AsyncIterator[AsyncSession]:
    """FastAPI dependency."""
    sf = get_session_factory()
    async with sf() as session:
        try:
            yield session
        finally:
            await session.close()


async def create_all() -> None:
    """Dev-only convenience: create tables from metadata. Production uses Alembic."""
    # Import models so they register on Base.metadata.
    from app import models  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
