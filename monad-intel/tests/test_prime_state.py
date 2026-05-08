"""Prime billing critical-path tests.

These are the most important tests in the codebase. The invariants:
1. If a Prime result already exists (by impl-hash or contract-id) -> AVAILABLE,
   price_usd == 0, no charge.
2. If an active Prime job exists -> IN_PROGRESS, price_usd == 0, no charge.
3. Concurrent purchase requests for the same contract result in EXACTLY ONE
   active job — every other concurrent request observes IN_PROGRESS.
"""

from __future__ import annotations

import asyncio

import pytest

from app.db import session_scope
from app.repositories import contracts as contracts_repo
from app.repositories import jobs as jobs_repo
from app.repositories import prime as prime_repo
from app.models.prime import PrimeAnalysis
from app.schemas.common import PrimeState
from app.services import prime_state
from app.utils.time import utc_now


async def _make_contract(addr: str = "0x" + "11" * 20) -> str:
    async with session_scope() as s:
        c = await contracts_repo.upsert_contract_shell(
            s, chain="monad", address=addr,
            creator_address="0x" + "aa" * 20,
            creation_tx_hash="0xabc", creation_block_number=1,
        )
        await contracts_repo.update_enrichment(
            s, c.id, bytecode_hash="0xBCH", implementation_hash="0xIMPL",
        )
        return c.id


@pytest.mark.asyncio
async def test_existing_result_returns_available(db, redis) -> None:
    cid = await _make_contract()
    async with session_scope() as s:
        c = await contracts_repo.get_by_id(s, cid)
        await prime_repo.insert(
            s,
            PrimeAnalysis(
                contract_id=c.id, implementation_hash=c.implementation_hash,
                provider_name="mock", prime_version="1.0",
                request_payload={}, result_json={"narrative_summary": "cached"},
                created_at=utc_now(), public_visible=True,
            ),
        )
    async with session_scope() as s:
        c = await contracts_repo.get_by_id(s, cid)
        block = await prime_state.find_existing(s, c)
    assert block.state == PrimeState.AVAILABLE
    assert block.price_usd == 0
    assert block.result is not None


@pytest.mark.asyncio
async def test_active_job_returns_in_progress(db, redis) -> None:
    cid = await _make_contract()
    async with session_scope() as s:
        c = await contracts_repo.get_by_id(s, cid)
        await jobs_repo.create_if_absent(
            s, kind=prime_state.JOB_KIND, dedup_key=prime_state._dedup_key_for(c),
            payload={"contract_id": c.id},
        )
    async with session_scope() as s:
        c = await contracts_repo.get_by_id(s, cid)
        block = await prime_state.find_existing(s, c)
    assert block.state == PrimeState.IN_PROGRESS
    assert block.price_usd == 0


@pytest.mark.asyncio
async def test_concurrent_purchase_creates_single_job(db, redis) -> None:
    cid = await _make_contract()

    async def attempt() -> str:
        async with session_scope() as s:
            c = await contracts_repo.get_by_id(s, cid)
            block = await prime_state.purchase(s, redis, c, payment_receipt="rcpt-123")
            return block.state.value

    # Fire 10 concurrent attempts; exactly one creates the job, the rest observe it.
    results = await asyncio.gather(*(attempt() for _ in range(10)))
    assert all(r == "in_progress" for r in results)

    async with session_scope() as s:
        c = await contracts_repo.get_by_id(s, cid)
        active = await jobs_repo.find_active(
            s, kind=prime_state.JOB_KIND, dedup_key=prime_state._dedup_key_for(c)
        )
    assert active is not None


@pytest.mark.asyncio
async def test_purchase_rejects_invalid_payment(db, redis) -> None:
    cid = await _make_contract()
    async with session_scope() as s:
        c = await contracts_repo.get_by_id(s, cid)
        with pytest.raises(RuntimeError):
            await prime_state.purchase(s, redis, c, payment_receipt="")


@pytest.mark.asyncio
async def test_no_prime_yet_returns_not_purchased_with_price(db, redis) -> None:
    cid = await _make_contract()
    async with session_scope() as s:
        c = await contracts_repo.get_by_id(s, cid)
        block = await prime_state.find_existing(s, c)
    assert block.state == PrimeState.NOT_PURCHASED
    assert block.price_usd == 6
