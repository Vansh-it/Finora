"""Tests for the bounded TTL+LRU cache with single-flight protection."""
import time
import threading
import pytest
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.cache import BoundedTTLCache, single_flight, resolution_cache


class TestBoundedTTLCache:
    def test_set_get(self):
        c = BoundedTTLCache(maxsize=10, ttl=60, name="test")
        c.set("k1", {"data": "hello"})
        result = c.get("k1")
        assert result is not None
        assert result["data"] == "hello"

    def test_miss(self):
        c = BoundedTTLCache(maxsize=10, ttl=60, name="test")
        assert c.get("nonexistent") is None

    def test_ttl_expiry(self):
        c = BoundedTTLCache(maxsize=10, ttl=0.05, name="test")
        c.set("k1", "value")
        assert c.get("k1") == "value"
        time.sleep(0.1)
        assert c.get("k1") is None

    def test_lru_eviction(self):
        c = BoundedTTLCache(maxsize=3, ttl=60, name="test")
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        c.set("d", 4)  # should evict 'a'
        assert c.get("a") is None
        assert c.get("b") == 2

    def test_lru_access_refreshes_position(self):
        c = BoundedTTLCache(maxsize=3, ttl=60, name="test")
        c.set("a", 1)
        c.set("b", 2)
        c.set("c", 3)
        c.get("a")  # refresh 'a' -> moves to end
        c.set("d", 4)  # should evict 'b' (oldest untouched)
        assert c.get("a") == 1
        assert c.get("b") is None

    def test_bounded_size(self):
        c = BoundedTTLCache(maxsize=5, ttl=60, name="test")
        for i in range(20):
            c.set(f"key_{i}", i)
        assert len(c) <= 5

    def test_invalidate_prefix(self):
        c = BoundedTTLCache(maxsize=10, ttl=60, name="test")
        c.set("sec:msft", 1)
        c.set("sec:aapl", 2)
        c.set("tavily:msft", 3)
        removed = c.invalidate_prefix("sec:")
        assert removed == 2
        assert c.get("sec:msft") is None
        assert c.get("sec:aapl") is None
        assert c.get("tavily:msft") == 3

    def test_company_isolation(self):
        c = BoundedTTLCache(maxsize=10, ttl=60, name="test")
        c.set("research:MSFT:latest", "msft_data")
        c.set("research:AAPL:latest", "aapl_data")
        c.invalidate_prefix("research:MSFT:")
        assert c.get("research:MSFT:latest") is None
        assert c.get("research:AAPL:latest") == "aapl_data"

    def test_period_isolation(self):
        c = BoundedTTLCache(maxsize=10, ttl=60, name="test")
        c.set("research:MSFT:FY2024", "fy24")
        c.set("research:MSFT:FY2023", "fy23")
        c.delete("research:MSFT:FY2024")
        assert c.get("research:MSFT:FY2024") is None
        assert c.get("research:MSFT:FY2023") == "fy23"

    def test_stats(self):
        c = BoundedTTLCache(maxsize=10, ttl=60, name="test")
        c.get("miss1")
        c.set("hit1", "val")
        c.get("hit1")
        stats = c.stats()
        assert stats["misses"] >= 1
        assert stats["hits"] >= 1
        assert stats["name"] == "test"


class TestSingleFlight:
    def test_basic_coalescing(self):
        results = []
        barrier = threading.Barrier(5)

        def worker():
            barrier.wait()
            result = single_flight("same_key", "id1", lambda: "result")
            results.append(result)

        threads = [threading.Thread(target=worker) for _ in range(5)]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert len(results) == 5
        assert all(r == "result" for r in results)

    def test_different_keys_independent(self):
        results_a = []
        results_b = []
        barrier = threading.Barrier(4)

        def worker_a():
            barrier.wait()
            results_a.append(single_flight("key_a", "a1", lambda: "a_result"))

        def worker_b():
            barrier.wait()
            results_b.append(single_flight("key_b", "b1", lambda: "b_result"))

        threads = [
            threading.Thread(target=worker_a),
            threading.Thread(target=worker_a),
            threading.Thread(target=worker_b),
            threading.Thread(target=worker_b),
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=5)

        assert all(r == "a_result" for r in results_a)
        assert all(r == "b_result" for r in results_b)

    def test_exception_propagation(self):
        def bad_fn():
            raise ValueError("test error")

        with pytest.raises(ValueError, match="test error"):
            single_flight("err_key", "id1", bad_fn)


class TestGlobalCaches:
    def test_resolution_cache_exists(self):
        assert resolution_cache is not None
        assert isinstance(resolution_cache, BoundedTTLCache)
