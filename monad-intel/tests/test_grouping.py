"""Grouping tests — first-pass via creator + impl-hash sharing."""

from __future__ import annotations

import pytest

from app.repositories import contracts as contracts_repo
from app.services import grouping as grouping_svc


@pytest.mark.asyncio
async def test_first_pass_creates_singleton(db) -> None:
    sf = db()
    async with sf as s:
        c = await contracts_repo.upsert_contract_shell(
            s, chain="monad", address="0x" + "11" * 20, creator_address="0x" + "aa" * 20,
            creation_tx_hash="0xabc", creation_block_number=1,
        )
        decision = await grouping_svc.assign_first_pass(s, c)
        assert decision.created_new is True
        assert decision.project_id


@pytest.mark.asyncio
async def test_first_pass_reuses_via_creator(db) -> None:
    sf = db()
    async with sf as s:
        a = await contracts_repo.upsert_contract_shell(
            s, chain="monad", address="0x" + "11" * 20, creator_address="0x" + "aa" * 20,
            creation_tx_hash="0xabc", creation_block_number=1,
        )
        d1 = await grouping_svc.assign_first_pass(s, a)
        b = await contracts_repo.upsert_contract_shell(
            s, chain="monad", address="0x" + "22" * 20, creator_address="0x" + "aa" * 20,
            creation_tx_hash="0xdef", creation_block_number=2,
        )
        d2 = await grouping_svc.assign_first_pass(s, b)
        assert d2.created_new is False
        assert d2.project_id == d1.project_id


@pytest.mark.asyncio
async def test_first_pass_reuses_via_impl_hash(db) -> None:
    sf = db()
    async with sf as s:
        a = await contracts_repo.upsert_contract_shell(
            s, chain="monad", address="0x" + "11" * 20, creator_address="0x" + "aa" * 20,
            creation_tx_hash="0xabc", creation_block_number=1,
        )
        await contracts_repo.update_enrichment(s, a.id, implementation_hash="0xIMPL")
        d1 = await grouping_svc.assign_first_pass(s, await contracts_repo.get_by_id(s, a.id))
        b = await contracts_repo.upsert_contract_shell(
            s, chain="monad", address="0x" + "22" * 20, creator_address="0x" + "bb" * 20,
            creation_tx_hash="0xdef", creation_block_number=2,
        )
        await contracts_repo.update_enrichment(s, b.id, implementation_hash="0xIMPL")
        d2 = await grouping_svc.assign_first_pass(s, await contracts_repo.get_by_id(s, b.id))
        assert d2.project_id == d1.project_id
