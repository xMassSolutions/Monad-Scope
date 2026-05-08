"""Block-processing worker — invoked by both the WS listener and the bootstrap crawler.

Per block:
1. fetch full block (with txs)
2. fetch all receipts (bounded retry)
3. extract contract creations
4. upsert contract shells
5. upsert the block ledger row
6. enqueue per-contract enrichment via the in-process semaphore (no external queue
   needed for this scaffold; production can switch to a real queue here)
"""

from __future__ import annotations

import asyncio

from app.db import session_scope
from app.logging import get_logger
from app.repositories import blocks as blocks_repo
from app.repositories import contracts as contracts_repo
from app.services.receipts import extract_creations
from app.services.rpc import JsonRpcClient
from app.utils.time import from_unix, parse_hex_qty
from app.workers.enrichment import enqueue_enrichment

log = get_logger(__name__)


class BlockProcessor:
    def __init__(self, rpc: JsonRpcClient) -> None:
        self._rpc = rpc

    async def process(self, number: int) -> None:
        block = await self._rpc.get_block_by_number(number, full_tx=True)
        if not block:
            log.warning("block.missing", number=number)
            return

        # Receipts (with bounded retry per Monad's near-head behavior).
        tx_hashes = [tx["hash"] for tx in (block.get("transactions") or []) if tx.get("hash")]
        receipts = await self._rpc.get_transaction_receipts_with_retry(tx_hashes)

        creations = extract_creations(block, receipts)

        async with session_scope() as session:
            for c in creations:
                await contracts_repo.upsert_contract_shell(
                    session,
                    chain="monad",
                    address=c.address,
                    creator_address=c.creator,
                    creation_tx_hash=c.tx_hash,
                    creation_block_number=c.block_number,
                )
            await blocks_repo.upsert_block(
                session,
                number=number,
                block_hash=block.get("hash") or "",
                parent_hash=block.get("parentHash"),
                timestamp=from_unix(parse_hex_qty(block.get("timestamp")) or 0),
                tx_count=len(tx_hashes),
                contracts_created=len(creations),
            )

        # Enqueue enrichment for each new contract (best-effort; cancellation-safe).
        for c in creations:
            await enqueue_enrichment(c.address)

        log.info("block.processed", number=number, txs=len(tx_hashes), created=len(creations))
