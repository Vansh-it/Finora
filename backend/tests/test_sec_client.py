"""Tests for SEC EDGAR HTTP client."""

import json
import os
import time
from unittest.mock import patch, MagicMock
from urllib.error import HTTPError, URLError

import pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.sec_client import (
    sec_get,
    get_ticker_mapping,
    clear_cache,
    _get_user_agent,
    _get_cached,
    _set_cache,
    _sec_cache,
)


@pytest.fixture(autouse=True)
def _clean_cache():
    """Clear cache before each test."""
    clear_cache()
    yield
    clear_cache()


# ── User-Agent tests ──────────────────────────────────────────────────────────
class TestUserAgent:
    def test_reads_from_env(self):
        with patch.dict(os.environ, {"FINORA_SEC_USER_AGENT": "TestBot/1.0 test@test.com"}):
            assert _get_user_agent() == "TestBot/1.0 test@test.com"

    def test_raises_when_missing(self):
        with patch.dict(os.environ, {"FINORA_SEC_USER_AGENT": ""}):
            with pytest.raises(RuntimeError, match="FINORA_SEC_USER_AGENT not set"):
                _get_user_agent()

    def test_raises_when_not_set(self):
        with patch.dict(os.environ, {}, clear=True):
            with pytest.raises(RuntimeError, match="FINORA_SEC_USER_AGENT not set"):
                _get_user_agent()


# ── Cache tests ───────────────────────────────────────────────────────────────
class TestCache:
    def test_set_and_get(self):
        _set_cache("test_url", {"data": "hello"})
        result = _get_cached("test_url", ttl_seconds=60)
        assert result == {"data": "hello"}

    def test_cache_miss(self):
        result = _get_cached("nonexistent_url")
        assert result is None

    def test_cache_expiry(self):
        from lib.sec_client import _sec_cache
        # Temporarily override the cache TTL to expire quickly
        old_ttl = _sec_cache.ttl
        _sec_cache.ttl = 0.01
        try:
            _set_cache("expiring_url", {"data": "old"})
            import time as _time
            _time.sleep(0.02)
            result = _get_cached("expiring_url")
            assert result is None
        finally:
            _sec_cache.ttl = old_ttl

    def test_clear_cache(self):
        _set_cache("clear_test", {"data": "yes"})
        clear_cache()
        result = _get_cached("clear_test")
        assert result is None


# ── sec_get tests ─────────────────────────────────────────────────────────────
class TestSecGet:
    def test_successful_get(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"hello": "world"}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("lib.sec_client.urlopen", return_value=mock_response):
            result = sec_get("https://data.sec.gov/test.json", cache_ttl=0)
            assert result == {"hello": "world"}

    def test_caches_response(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"cached": True}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("lib.sec_client.urlopen", return_value=mock_response) as mock_open:
            # First call
            sec_get("https://data.sec.gov/cache_test.json", cache_ttl=3600)
            # Second call should use cache
            result = sec_get("https://data.sec.gov/cache_test.json", cache_ttl=3600)
            assert result == {"cached": True}
            # urlopen should only be called once (second hit from cache)
            assert mock_open.call_count == 1

    def test_404_raises_value_error(self):
        mock_response = MagicMock()
        mock_response.status = 404
        with patch("lib.sec_client.urlopen", side_effect=HTTPError(
            "url", 404, "Not Found", {}, None
        )):
            with pytest.raises(ValueError, match="not found"):
                sec_get("https://data.sec.gov/missing.json")

    def test_500_retries(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": True}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise HTTPError("url", 500, "Server Error", {}, None)
            return mock_response

        with patch("lib.sec_client.urlopen", side_effect=side_effect):
            result = sec_get("https://data.sec.gov/retry_test.json", cache_ttl=0)
            assert result == {"ok": True}
            assert call_count == 2

    def test_timeout_retries(self):
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps({"ok": True}).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        call_count = 0
        def side_effect(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                raise URLError("timeout")
            return mock_response

        with patch("lib.sec_client.urlopen", side_effect=side_effect):
            result = sec_get("https://data.sec.gov/timeout_test.json", cache_ttl=0)
            assert result == {"ok": True}

    def test_all_retries_fail_raises(self):
        with patch("lib.sec_client.urlopen", side_effect=URLError("network error")):
            with pytest.raises(RuntimeError, match="failed after"):
                sec_get("https://data.sec.gov/fail.json", cache_ttl=0)

    def test_invalid_json_raises(self):
        mock_response = MagicMock()
        mock_response.read.return_value = b"not json at all"
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("lib.sec_client.urlopen", return_value=mock_response):
            with pytest.raises(ValueError, match="Invalid JSON"):
                sec_get("https://data.sec.gov/bad_json.json", cache_ttl=0)


# ── Ticker mapping tests ─────────────────────────────────────────────────────
class TestTickerMapping:
    def test_returns_data(self):
        mock_data = {"fields": ["cik_str", "ticker", "title"], "data": [[789019, "MSFT", "MICROSOFT CORP"]]}
        mock_response = MagicMock()
        mock_response.read.return_value = json.dumps(mock_data).encode()
        mock_response.__enter__ = MagicMock(return_value=mock_response)
        mock_response.__exit__ = MagicMock(return_value=False)

        with patch("lib.sec_client.urlopen", return_value=mock_response):
            result = get_ticker_mapping(cache_ttl=60)
            assert "fields" in result or "data" in result
