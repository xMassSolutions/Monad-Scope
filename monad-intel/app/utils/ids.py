"""ID generation. UUIDv7-style: time-ordered + random."""

from __future__ import annotations

import os
import time
import uuid


def new_id() -> str:
    """Time-ordered ID safe to use as a primary key.

    Uses uuid7-style layout: 48 bits of ms timestamp, then 74 bits random.
    """
    ms = int(time.time() * 1000) & 0xFFFFFFFFFFFF
    rand = int.from_bytes(os.urandom(10), "big") & ((1 << 74) - 1)
    # Compose 128 bits.
    raw = (ms << 80) | (rand & ((1 << 80) - 1))
    # Set version (7) and variant bits per RFC 4122 layout.
    raw &= ~(0xF000 << 64)  # clear version nibble
    raw |= 0x7000 << 64  # set version 7
    raw &= ~(0xC000 << 48)  # clear variant
    raw |= 0x8000 << 48  # variant 10xx
    return str(uuid.UUID(int=raw))
