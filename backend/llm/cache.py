"""
cache.py — Redis-backed cache for LLM-generated regex patterns.

Cache key: SHA-256 hash of the normalised prompt.
Why hash it?
  - Keeps keys short and fixed-length (safe for Redis key size limits).
  - Normalising (strip + lowercase) means "Find emails" and "find emails "
    hit the same cache entry.
TTL: 7 days. Regex for "find email addresses" won't change — long TTL is safe.
"""

import hashlib
from django.core.cache import cache

CACHE_TTL = 60 * 60 * 24 * 7  # 7 days in seconds
CACHE_KEY_PREFIX = "rhombus:regex:"


def _make_key(prompt: str) -> str:
    normalised = prompt.strip().lower()
    digest = hashlib.sha256(normalised.encode()).hexdigest()
    return f"{CACHE_KEY_PREFIX}{digest}"


def get_cached_regex(prompt: str) -> str | None:
    """Return cached regex string or None if not cached."""
    return cache.get(_make_key(prompt))


def set_cached_regex(prompt: str, regex: str) -> None:
    """Store a regex in Redis with a 7-day TTL."""
    cache.set(_make_key(prompt), regex, timeout=CACHE_TTL)
