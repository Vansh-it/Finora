"""Regression tests for provider network fail-fast behavior.

Covers the DNS-timeout DNS resolver, error classification, the network
circuit breaker, and NIM-down/OpenRouter-up failover ordering.

All tests are hermetic: real networks are never touched.
"""

import time
import unittest

import lib.provider_manager as pm
from lib.provider_manager import (
    DNS_TIMEOUT,
    MAX_NETWORK_HOST_FAILURES,
    NETWORK_FAILURE_BUDGET,
    ProviderManager,
    TaskType,
    classify_error,
    resolve_host,
)


class TestClassifyError(unittest.TestCase):
    def test_dns_failure_is_network(self):
        msg = "nvidia_nemotron_lightning: cannot resolve integrate.api.nvidia.com"
        self.assertEqual(classify_error(msg), "network")

    def test_integrate_does_not_match_rate(self):
        # Regression: the substring "rate" used to falsely match "integrate".
        msg = "nvidia_nemotron_lightning: cannot resolve integrate.api.nvidia.com"
        self.assertNotEqual(classify_error(msg), "rate_limit")

    def test_winerror_10065_is_network(self):
        self.assertEqual(classify_error("socket.gaierror: [Errno 11001] getaddrinfo failed"), "network")
        self.assertEqual(classify_error("[WinError 10065] unreachable host"), "network")

    def test_read_timeout_is_timeout(self):
        self.assertEqual(classify_error("The read operation timed out"), "timeout")

    def test_http_429_is_rate_limit(self):
        self.assertEqual(classify_error("HTTP 429: Too Many Requests"), "rate_limit")

    def test_http_404_is_unknown(self):
        self.assertEqual(classify_error('HTTP 404: {"message": "gone"}'), "unknown")

    def test_401_is_auth(self):
        self.assertEqual(classify_error("HTTP 401: Unauthorized"), "auth")


class TestResolveHost(unittest.TestCase):
    def test_timeout_is_bounded(self):
        original = pm.socket.getaddrinfo

        def hanging(*args, **kwargs):
            time.sleep(DNS_TIMEOUT * 3)

        pm.socket.getaddrinfo = hanging
        pm._DNS_CACHE.clear()
        try:
            t0 = time.time()
            ok, err = resolve_host("hang.example-not-real")
            elapsed = time.time() - t0
            self.assertFalse(ok)
            self.assertIn("exceeded", err.lower())
            self.assertLess(elapsed, DNS_TIMEOUT + 1.0)
        finally:
            pm.socket.getaddrinfo = original
            pm._DNS_CACHE.clear()

    def test_failure_is_cached(self):
        original = pm.socket.getaddrinfo
        calls = []

        def failing(*args, **kwargs):
            calls.append(1)
            raise OSError("no such host")

        pm.socket.getaddrinfo = failing
        pm._DNS_CACHE.clear()
        try:
            ok1, _ = resolve_host("cache.example-not-real")
            ok2, _ = resolve_host("cache.example-not-real")
            self.assertFalse(ok1)
            self.assertFalse(ok2)
            self.assertEqual(len(calls), 1, "second lookup must hit the failure cache")
        finally:
            pm.socket.getaddrinfo = original
            pm._DNS_CACHE.clear()

    def test_success_is_cached(self):
        original = pm.socket.getaddrinfo
        calls = []

        def succeeding(*args, **kwargs):
            calls.append(1)
            return [("AF_INET", "SOCK_STREAM", 6, "", ("127.0.0.1", 0))]

        pm.socket.getaddrinfo = succeeding
        pm._DNS_CACHE.clear()
        try:
            ok1, _ = resolve_host("ok.example-not-real")
            ok2, _ = resolve_host("ok.example-not-real")
            self.assertTrue(ok1 and ok2)
            self.assertEqual(len(calls), 1)
        finally:
            pm.socket.getaddrinfo = original
            pm._DNS_CACHE.clear()


class TestNetworkCircuitBreaker(unittest.TestCase):
    def test_all_hosts_down_fails_fast_with_network_error(self):
        manager = ProviderManager()
        original = pm.resolve_host
        pm.resolve_host = lambda host, timeout=DNS_TIMEOUT: (False, "simulated DNS outage")
        try:
            t0 = time.time()
            with self.assertRaises(pm.NetworkError) as ctx:
                manager.generate_chat(
                    [{"role": "user", "content": "hello"}],
                    task_type=TaskType.QUICK_CHAT,
                )
            elapsed = time.time() - t0
            self.assertLess(elapsed, 15.0, "fail-fast must not burn tens of seconds")
            self.assertIn("network unavailable", str(ctx.exception).lower())
        finally:
            pm.resolve_host = original

    def test_nim_down_falls_through_to_openrouter(self):
        manager = ProviderManager()
        original = pm.ProviderManager._call_provider

        tried = []

        def fake_call(self, provider, messages, max_tokens=512, temperature=0.5, top_p=0.9):
            tried.append(provider.name)
            if "nvidia.com" in provider.base_url:
                raise pm.NetworkError(f"{provider.name}: cannot resolve integrate.api.nvidia.com")
            return f"ok via {provider.name}"

        pm.ProviderManager._call_provider = fake_call
        try:
            out = manager.generate_chat(
                [{"role": "user", "content": "hi"}],
                task_type=TaskType.QUICK_CHAT,
            )
            self.assertIn("ok via openrouter_", out)
            nim = [t for t in tried if t.startswith("nvidia_")]
            self.assertEqual(len(nim), 3, "all three NIM providers must be tried first")
            or_index = next(i for i, t in enumerate(tried) if t.startswith("openrouter_"))
            self.assertEqual(or_index, 3, "openrouter must come strictly after every NIM provider")
        finally:
            pm.ProviderManager._call_provider = original

    def test_budget_constants_sane(self):
        self.assertGreaterEqual(DNS_TIMEOUT, 2.0)
        self.assertLessEqual(DNS_TIMEOUT, 8.0)
        self.assertGreaterEqual(MAX_NETWORK_HOST_FAILURES, 2)
        self.assertLessEqual(NETWORK_FAILURE_BUDGET, 30.0)


if __name__ == "__main__":
    unittest.main()