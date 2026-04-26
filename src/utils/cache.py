"""
Small in-process TTL cache utilities.

This project runs in both CLI (long-lived process) and Vercel serverless (warm instances).
An in-memory TTL cache is a high-impact latency/cost optimization while preserving the
public API surface (no route/schema changes).
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Dict, Generic, Optional, Tuple, TypeVar


T = TypeVar("T")


@dataclass(frozen=True)
class CacheStats:
    hits: int
    misses: int
    items: int


class TTLCache(Generic[T]):
    """
    Minimal TTL cache with max-items eviction.

    - TTL is per-entry.
    - Eviction is approximate LRU via "last_access" timestamps.
    - Designed to be dependency-free and safe in serverless.
    """

    def __init__(self, max_items: int = 512):
        self._max_items = max(16, int(max_items))
        # key -> (value, expires_at, last_access)
        self._data: Dict[str, Tuple[T, float, float]] = {}
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Optional[T]:
        now = time.time()
        item = self._data.get(key)
        if not item:
            self._misses += 1
            return None

        value, expires_at, _last_access = item
        if expires_at <= now:
            # Expired
            self._data.pop(key, None)
            self._misses += 1
            return None

        self._data[key] = (value, expires_at, now)
        self._hits += 1
        return value

    def set(self, key: str, value: T, ttl_seconds: int) -> None:
        now = time.time()
        ttl = max(1, int(ttl_seconds))
        expires_at = now + ttl
        self._data[key] = (value, expires_at, now)
        self._evict_if_needed(now)

    def _evict_if_needed(self, now: float) -> None:
        # Drop expired first
        expired = [k for k, (_v, exp, _a) in self._data.items() if exp <= now]
        for k in expired:
            self._data.pop(k, None)

        if len(self._data) <= self._max_items:
            return

        # Evict least-recently-accessed entries
        over = len(self._data) - self._max_items
        oldest = sorted(self._data.items(), key=lambda kv: kv[1][2])[:over]
        for k, _ in oldest:
            self._data.pop(k, None)

    def clear(self) -> None:
        self._data.clear()

    def stats(self) -> CacheStats:
        return CacheStats(
            hits=self._hits,
            misses=self._misses,
            items=len(self._data),
        )


def stable_cache_key(*parts: Any) -> str:
    """
    Build a stable string key from arbitrary parts.
    """
    return "|".join("" if p is None else str(p) for p in parts)

