"""Trivial text helpers."""

from __future__ import annotations

import re
import unicodedata

_SLUG_RE = re.compile(r"[^a-z0-9]+")


def slugify(value: str, max_len: int = 80) -> str:
    if not value:
        return ""
    norm = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    slug = _SLUG_RE.sub("-", norm.lower()).strip("-")
    return slug[:max_len] if len(slug) > max_len else slug


def safe_truncate(value: str | None, max_len: int = 256) -> str | None:
    if value is None:
        return None
    return value if len(value) <= max_len else value[: max_len - 1] + "…"
