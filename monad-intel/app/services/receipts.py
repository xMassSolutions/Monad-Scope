"""Block-to-contract-creation extraction.

A contract creation is identified by `receipt.contractAddress != null` AND
`receipt.status == 1`. We also surface the creator (tx.from), the tx hash,
and the block number for the contract-shell row.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.utils.time import parse_hex_qty


@dataclass(frozen=True)
class CreationEvent:
    address: str
    creator: str
    tx_hash: str
    block_number: int


def extract_creations(
    block: dict[str, Any], receipts: dict[str, dict[str, Any] | None]
) -> list[CreationEvent]:
    """Find all successful contract creations in a fully-loaded block.

    `block` is the result of `eth_getBlockByNumber(..., full_tx=True)`.
    `receipts` maps tx hash -> receipt (or None if still unavailable).
    """
    out: list[CreationEvent] = []
    block_number = parse_hex_qty(block.get("number")) or 0
    for tx in block.get("transactions") or []:
        tx_hash = tx.get("hash")
        if not tx_hash:
            continue
        receipt = receipts.get(tx_hash)
        if not receipt:
            continue
        # Status: 1 = success (post-Byzantium). Some nodes use "0x1".
        status = parse_hex_qty(receipt.get("status"))
        if status != 1:
            continue
        contract_addr = receipt.get("contractAddress")
        if not contract_addr:
            continue
        # `tx.to` should be None for a creation tx; trust receipt.contractAddress.
        creator = (tx.get("from") or "").lower()
        out.append(
            CreationEvent(
                address=contract_addr.lower(),
                creator=creator,
                tx_hash=tx_hash,
                block_number=block_number,
            )
        )
    return out
