"""Historical block-range crawler.

Reuses the same per-block processing as the live listener.

- Chunked: processes `chunk_size` blocks at a time, `concurrency` blocks in parallel.
- Restart-safe: any block already in `blocks` (with processed_at set) is skipped.
- Idempotent: contract upserts use ON CONFLICT DO NOTHING; re-running the same
  range is a no-op.
"""

from __future__ import annotations

import asyncio
from typing import Awaitable, Callable

from app.config import get_settings
from app.logging import get_logger
from app.repositories import blocks as blocks_repo
from app.db import session_scope

log = get_logger(__name__)


BlockProcessor = Callable[[int], Awaitable[None]]
"""Same shape as the WS listener's on_block: takes block number, processes E2E."""


async def crawl_range(
    process_block: BlockProcessor,
    *,
    from_block: int,
    to_block: int,
    chunk_size: int | None = None,
    concurrency: int | None = None,
    skip_existing: bool = True,
) -> dict[str, int]:
    settings = get_settings()
    chunk = chunk_size or settings.bootstrap_chunk_size
    conc = concurrency or settings.enrichment_concurrency
    if from_block > to_block:
        raise ValueError("from_block must be <= to_block")

    sem = asyncio.Semaphore(conc)
    processed = 0
    skipped = 0
    failed = 0

    async def one(n: int) -> None:
        nonlocal processed, skipped, failed
        if skip_existing:
            async with session_scope() as s:
                exists = await blocks_repo.has_block(s, n)
            if exists:
                skipped += 1
                return
        async with sem:
            try:
                await process_block(n)
                processed += 1
            except Exception as e:  # noqa: BLE001
                failed += 1
                log.exception("bootstrap.block_failed", number=n, err=str(e))

    cur = from_block
    while cur <= to_block:
        end = min(cur + chunk - 1, to_block)
        await asyncio.gather(*(one(n) for n in range(cur, end + 1)))
        log.info("bootstrap.chunk_done", from_block=cur, to_block=end, processed=processed, skipped=skipped, failed=failed)
        cur = end + 1

    return {"processed": processed, "skipped": skipped, "failed": failed}
