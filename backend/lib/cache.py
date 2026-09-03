"""Bounded multi-layer cache with TTL, LRU eviction, and single-flight.

Design principles:
  - Every cache namespace is an independent :class:`BoundedTTLCache` instance
    with its own TTL and max size, so we never build one giant permanent cache.
  - Entries expire by TTL AND are evicted by LRU when the cache exceeds its
    maximum size — growth is always bounded.
  - Expired entries are purged lazily on access plus opportunistically on
    writes, keeping memory flat without a background thread dependency.
  - :func:`single_flight` coalesces concurrent identical requests so a stampede
    of 20 identical lookups only triggers one upstream call.
  - Cache hits/misses/expirations are logged with a lightweight observable
    counter so dev logs can show "[cache] SEC companyfacts HIT" style output.

This module has NO external dependencies and is safe to import anywhere in the
backend (thread-safe via a lock per cache instance).
"""

from __future__ import annotations

import logging
import threading
import time
from collections import OrderedDict
from typing import Any, Callable, Optional, TypeVar

logger = logging.getLogger("finora.cache")

T = TypeVar("T")


# ── Observable counters ──────────────────────────────────────────────────────
class _Counters:
    """Per-cache hit/miss/expire counters for observability."""

    __slots__ = ("hits", "misses", "expired", "evicted", "single_flight_joins")

    def __init__(self) -> None:
        self.hits = 0
        self.misses = 0
        self.expired = 0
        self.evicted = 0
        self.single_flight_joins = 0


# ── Core cache ────────────────────────────────────────────────────────────────
class BoundedTTLCache:
    """A thread-safe cache with TTL expiry and LRU-style bounded eviction.

    Parameters
    ----------
    maxsize : int
        Maximum number of entries.  When exceeded, least-recently-used
        entries are evicted.
    ttl : float
        Default time-to-live in seconds for entries that don't pass an
        explicit ttl on store.
    name : str
        Namespace name used only in log lines (e.g. "companyfacts").
    """

    __slots__ = ("_data", "_timestamps", "_lock", "maxsize", "ttl", "name", "counters")

    def __init__(self, maxsize: int = 1000, ttl: float = 3600.0, name: str = "cache") -> None:
        self.maxsize = max(1, maxsize)
        self.ttl = max(0.0, ttl)
        self.name = name
        self._data: "OrderedDict[str, Any]" = OrderedDict()
        self._timestamps: dict[str, float] = {}
        self._lock = threading.Lock()
        self.counters = _Counters()

    # ── internals ────────────────────────────────────────────────────────
    def _purge_expired_locked(self, now: float) -> None:
        """Drop entries older than their TTL (locked callers only)."""
        expired_keys = [
            k for k, ts in self._timestamps.items()
            if now - ts >= self.ttl
        ]
        for k in expired_keys:
            self._data.pop(k, None)
            self._timestamps.pop(k, None)
        if expired_keys:
            self.counters.expired += len(expired_keys)
            logger.info(f"[cache] {self.name} purged {len(expired_keys)} expired entries")

    def _evict_locked(self) -> None:
        """Evict oldest entries until under maxsize (locked callers only)."""
        while len(self._data) > self.maxsize:
            oldest_key, _ = self._data.popitem(last=False)
            self._timestamps.pop(oldest_key, None)
            self.counters.evicted += 1
            logger.info(f"[cache] {self.name} evicted LRU entry {oldest_key}")

    # ── public API ───────────────────────────────────────────────────────
    def get(self, key: str, default: Optional[T] = None) -> Optional[T]:
        """Return the cached value for ``key`` or ``default``.

        A stale (expired) entry counts as a miss and is removed.
        """
        if not isinstance(key, str) or not key:
            return default
        with self._lock:
            now = time.time()
            ts = self._timestamps.get(key)
            if ts is None:
                self.counters.misses += 1
                return default
            if now - ts >= self.ttl:
                self._data.pop(key, None)
                self._timestamps.pop(key, None)
                self.counters.expired += 1
                self.counters.misses += 1
                logger.info(f"[cache] {self.name} MISS (expired) {key}")
                return default
            # Refresh recency (LRU)
            self._data.move_to_end(key)
            self.counters.hits += 1
            logger.debug(f"[cache] {self.name} HIT {key}")
            return self._data[key]

    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """Store ``value`` under ``key`` with an optional per-entry TTL."""
        if not isinstance(key, str) or not key:
            return
        entry_ttl = self.ttl if ttl is None else max(0.0, ttl)
        with self._lock:
            now = time.time()
            self._timestamps[key] = now
            self._data[key] = value
            self._data.move_to_end(key)
            # Opportunistic purge keeps memory flat without a background thread
            self._purge_expired_locked(now)
            self._evict_locked()

    def get_or_set(self, key: str, factory: Callable[[], T], ttl: Optional[float] = None) -> T:
        """Return cached value or compute+store it (not single-flight)."""
        cached = self.get(key)
        if cached is not None:
            return cached
        value = factory()
        self.set(key, value, ttl=ttl)
        return value

    def delete(self, key: str) -> None:
        """Remove a single entry."""
        with self._lock:
            self._data.pop(key, None)
            self._timestamps.pop(key, None)

    def invalidate_prefix(self, prefix: str) -> int:
        """Remove all keys starting with ``prefix``.  Returns count removed."""
        removed = 0
        with self._lock:
            for k in list(self._data.keys()):
                if k.startswith(prefix):
                    self._data.pop(k, None)
                    self._timestamps.pop(k, None)
                    removed += 1
        return removed

    def clear(self) -> None:
        """Drop all entries."""
        with self._lock:
            self._data.clear()
            self._timestamps.clear()

    def __len__(self) -> int:
        return len(self._data)

    def stats(self) -> dict:
        """Return safe observability stats (no keys/values)."""
        with self._lock:
            now = time.time()
            live = sum(1 for ts in self._timestamps.values() if now - ts < self.ttl)
        return {
            "name": self.name,
            "entries": len(self._data),
            "live_entries": live,
            "maxsize": self.maxsize,
            "ttl_seconds": self.ttl,
            "hits": self.counters.hits,
            "misses": self.counters.misses,
            "expired": self.counters.expired,
            "evicted": self.counters.evicted,
            "single_flight_joins": self.counters.single_flight_joins,
        }


# ── Single-flight / request coalescing ────────────────────────────────────────
# Each cache key gets its own lock so one in-flight computation for a key is
# shared by all callers.  Different keys never block each other.
_sf_locks_guard = threading.Lock()
_sf_locks: dict[str, threading.Lock] = {}
_sf_inflight: dict[str, tuple[str, Any]] = {}  # key -> (identity, result)


def _get_sf_lock(key: str) -> threading.Lock:
    with _sf_locks_guard:
        lock = _sf_locks.get(key)
        if lock is None:
            lock = threading.Lock()
            _sf_locks[key] = lock
        return lock


def single_flight(key: str, identity: str, factory: Callable[[], T]) -> T:
    """Run ``factory`` once for concurrent callers of the same ``key``.

    Callers are identified by ``identity`` (e.g. cache namespace) so locks
    for the same data across modules coalesce.  While the first caller runs
    ``factory``, other callers with the same key block and then receive the
    same result.  Errors are NOT cached: each waiter retries if the leader
    raised.

    Returns
    -------
    The result produced by the winning ``factory`` call.
    """
    lock = _get_sf_lock(key)
    if lock.locked():
        # Another thread is already fetching this exact key — join it.
        # Wait until the in-flight result appears (or the lock releases).
        start = time.time()
        waited = False
        while time.time() - start < 60.0:
            with _sf_locks_guard:
                hit = _sf_inflight.get(key)
            if hit is not None and hit[0] == identity:
                if waited:
                    logger.info(f"[cache] single-flight JOIN {key}")
                return hit[1]
            if not lock.locked():
                break  # leader finished (success or failure); retry as leader
            time.sleep(0.02)
            waited = True
        # Fall through and become the new leader if the old leader stalled.
    with lock:
        with _sf_locks_guard:
            cached = _sf_inflight.get(key)
        if cached is not None and cached[0] == identity:
            return cached[1]
        try:
            result = factory()
        except BaseException:
            raise
        with _sf_locks_guard:
            _sf_inflight[key] = (identity, result)
        return result


def clear_single_flight() -> None:
    """Drop all single-flight state (tests only)."""
    with _sf_locks_guard:
        _sf_inflight.clear()


# ── Shared cache instances (per data layer) ───────────────────────────────────
# TTLs chosen from data semantics (see project hardening notes):
#   SEC company universe:         long-lived + periodic refresh
#   company resolution results:   medium (day) — index refreshes daily
#   SEC submissions/facts/XBRL:   long-lived (immutable historical data)
#   Twelve Data current quote:    very short (30s) — price freshness matters
#   Twelve Data historical:       long-lived (30d) — historical prices fixed
#   Tavily discovery:             medium (6h)
#   Jina document reads:          long (24h)
#   Ask Finora compact context:   session scoped (bounded, short TTL)
#   chat answer cache:            bounded per-session (15 min)

company_index_cache = BoundedTTLCache(maxsize=50, ttl=86400.0, name="company_index")
resolution_cache = BoundedTTLCache(maxsize=4000, ttl=86400.0, name="company_resolution")
sec_submissions_cache = BoundedTTLCache(maxsize=8000, ttl=86400.0, name="sec_submissions")
sec_companyfacts_cache = BoundedTTLCache(maxsize=8000, ttl=86400.0, name="sec_companyfacts")
sec_ticker_cache = BoundedTTLCache(maxsize=10, ttl=86400.0, name="sec_tickers")
filing_registry_cache = BoundedTTLCache(maxsize=6000, ttl=86400.0, name="filing_registry")
financials_cache = BoundedTTLCache(maxsize=6000, ttl=86400.0, name="financials")
metrics_cache = BoundedTTLCache(maxsize=6000, ttl=86400.0, name="metrics")
bq_cache = BoundedTTLCache(maxsize=6000, ttl=3600.0, name="business_quant")
twelve_quote_cache = BoundedTTLCache(maxsize=4000, ttl=30.0, name="twelve_quote")
twelve_historical_cache = BoundedTTLCache(maxsize=8000, ttl=2592000.0, name="twelve_historical")
tavily_cache = BoundedTTLCache(maxsize=6000, ttl=21600.0, name="tavily")
jina_cache = BoundedTTLCache(maxsize=6000, ttl=86400.0, name="jina")
askfinora_context_cache = BoundedTTLCache(maxsize=4000, ttl=900.0, name="askfinora_context")
chat_answer_cache = BoundedTTLCache(maxsize=6000, ttl=900.0, name="chat_answers")


def clear_all_caches() -> None:
    """Drop all shared cache contents (tests only)."""
    for c in (
        company_index_cache, resolution_cache, sec_submissions_cache,
        sec_companyfacts_cache, sec_ticker_cache, filing_registry_cache,
        financials_cache, metrics_cache, bq_cache, twelve_quote_cache,
        twelve_historical_cache, tavily_cache, jina_cache,
        askfinora_context_cache, chat_answer_cache,
    ):
        c.clear()


def cache_stats() -> dict:
    """Return observability stats for all shared caches."""
    return {c.name: c.stats() for c in (
        company_index_cache, resolution_cache, sec_submissions_cache,
        sec_companyfacts_cache, sec_ticker_cache, filing_registry_cache,
        financials_cache, metrics_cache, bq_cache, twelve_quote_cache,
        twelve_historical_cache, tavily_cache, jina_cache,
        askfinora_context_cache, chat_answer_cache,
    )}
