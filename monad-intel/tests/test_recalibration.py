"""Recalibration: seed default ruleset, propose a new one, verify status='proposed'."""

from __future__ import annotations

import pytest

from app.repositories import rulesets as rulesets_repo
from app.services import recalibration as recal_svc


@pytest.mark.asyncio
async def test_seed_default_creates_v1(db) -> None:
    sf = db()
    async with sf as s:
        await recal_svc.seed_default_ruleset_if_empty(s)
        active = await rulesets_repo.get_active(s)
    assert active is not None
    assert active.version == 1
    assert active.status == "active"
    # Sanity-check that the canonical weights survived seeding.
    assert active.weights_json["OWNER_CAN_MINT"] == 18


@pytest.mark.asyncio
async def test_seed_is_idempotent(db) -> None:
    sf = db()
    async with sf as s:
        await recal_svc.seed_default_ruleset_if_empty(s)
        await recal_svc.seed_default_ruleset_if_empty(s)
        rows = await rulesets_repo.list_all(s)
    assert len(rows) == 1


@pytest.mark.asyncio
async def test_propose_creates_proposed_row(db) -> None:
    sf = db()
    async with sf as s:
        await recal_svc.seed_default_ruleset_if_empty(s)
        result = await recal_svc.propose_new_ruleset(s)
        rows = await rulesets_repo.list_all(s)
    assert any(r.version == result["version"] and r.status == "proposed" for r in rows)


@pytest.mark.asyncio
async def test_promote_activates_new_and_archives_old(db) -> None:
    sf = db()
    async with sf as s:
        await recal_svc.seed_default_ruleset_if_empty(s)
        proposed = await recal_svc.propose_new_ruleset(s)
        await recal_svc.promote_ruleset(s, proposed["version"])
        active = await rulesets_repo.get_active(s)
        all_rows = await rulesets_repo.list_all(s)
    assert active is not None and active.version == proposed["version"]
    statuses = {r.version: r.status for r in all_rows}
    assert statuses[1] == "archived"
    assert statuses[proposed["version"]] == "active"
