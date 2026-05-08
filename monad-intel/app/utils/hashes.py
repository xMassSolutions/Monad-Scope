"""Hashing + key helpers shared across services."""

from __future__ import annotations

import re

from Crypto.Hash import keccak

# Solidity compiler appends a CBOR-encoded metadata blob to runtime bytecode.
# The blob ends with the two-byte big-endian length of the blob itself.
# We strip it before hashing so two contracts with identical logic but different
# metadata (different compiler/source paths) get the same `implementation_hash`.
_CBOR_TAIL_RE = re.compile(rb"a264697066[0-9a-fA-F]*$")  # heuristic: starts with `a2 64 ipfs` CBOR map


def keccak256(data: bytes) -> str:
    h = keccak.new(digest_bits=256)
    h.update(data)
    return "0x" + h.hexdigest()


def normalize_bytecode(code_hex: str) -> bytes:
    """Strip leading 0x and any trailing CBOR metadata blob.

    Tolerant: if no CBOR tail is detected, returns the raw bytes.
    """
    if not code_hex:
        return b""
    if code_hex.startswith("0x") or code_hex.startswith("0X"):
        code_hex = code_hex[2:]
    raw = bytes.fromhex(code_hex)
    if len(raw) < 2:
        return raw
    # Last 2 bytes: big-endian length of CBOR blob.
    tail_len = int.from_bytes(raw[-2:], "big")
    if 0 < tail_len < len(raw) - 2:
        candidate = raw[-2 - tail_len : -2]
        # Solidity CBOR blobs reliably start with 0xa2 0x64 (map of 2, key length 4).
        if len(candidate) >= 2 and candidate[0] == 0xA2 and candidate[1] == 0x64:
            return raw[: -2 - tail_len]
    return raw


def bytecode_hash(code_hex: str) -> str:
    raw = code_hex if not code_hex.startswith(("0x", "0X")) else code_hex[2:]
    return keccak256(bytes.fromhex(raw)) if raw else "0x" + "00" * 32


def implementation_hash(code_hex: str) -> str:
    return keccak256(normalize_bytecode(code_hex)) if code_hex else "0x" + "00" * 32


def contract_key(address: str, chain: str = "monad") -> str:
    return f"{chain}:{address.lower()}"


def implementation_cache_key(impl_hash: str | None, byte_hash: str | None, chain: str = "monad") -> str:
    h = impl_hash or byte_hash
    return f"{chain}:{h}"


def function_selector(signature: str) -> str:
    """keccak256(signature)[:4] as 0x-prefixed hex."""
    h = keccak.new(digest_bits=256)
    h.update(signature.encode("utf-8"))
    return "0x" + h.hexdigest()[:8]


def contains_selector(code_hex: str, selector: str) -> bool:
    """Cheap check: does the bytecode contain the 4-byte selector?

    Not a parser; some false positives possible if the selector bytes appear in
    immutables. Good enough for first-pass classification heuristics.
    """
    if not code_hex:
        return False
    needle = selector[2:].lower() if selector.startswith("0x") else selector.lower()
    haystack = code_hex.lower()
    if haystack.startswith("0x"):
        haystack = haystack[2:]
    return needle in haystack
