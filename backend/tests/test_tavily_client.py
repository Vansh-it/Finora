"""Tests for Tavily API client."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch, MagicMock
from io import BytesIO

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.tavily_client import (
    tavily_search,
    clear_cache,
    get_search_count,
    reset_search_count,
    _get_api_key,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _clean_cache():
    """Clear cache and search count before each test."""
    clear_cache()
    reset_search_count()
    yield
    clear_cache()
    reset_search_count()


def _mock_tavily_response(results=None, status=200):
    """Create a mock urllib response."""
    data = {
        "results": results or [
            {
                "title": "Microsoft 2025 Annual Report",
                "url": "https://www.microsoft.com/investor/",
                "content": "Official investor relations page.",
                "score": 0.95,
            }
        ],
        "query": "Microsoft investor relations",
    }
    raw = json.dumps(data).encode("utf-8")

    mock_resp = MagicMock()
    mock_resp.read.return_value = raw
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = status
    mock_resp.code = status
    return mock_resp


# ── API Key Tests ────────────────────────────────────────────────────────────
class TestApiKey:
    def test_api_key_loads(self):
        """Should load TAVILY_API_KEY from environment."""
        key = _get_api_key()
        assert key.startswith("tvly-")

    @patch.dict(os.environ, {"TAVILY_API_KEY": ""})
    def test_missing_key_raises(self):
        """Should raise RuntimeError if key not set."""
        with pytest.raises(RuntimeError, match="TAVILY_API_KEY not set"):
            _get_api_key()

    @patch.dict(os.environ, {"TAVILY_API_KEY": "  "})
    def test_empty_key_raises(self):
        """Should raise RuntimeError for whitespace-only key."""
        with pytest.raises(RuntimeError, match="TAVILY_API_KEY not set"):
            _get_api_key()


# ── Search Tests ─────────────────────────────────────────────────────────────
class TestTavilySearch:
    @patch("lib.tavily_client.urlopen")
    def test_basic_search(self, mock_urlopen):
        """Should return parsed results."""
        mock_urlopen.return_value = _mock_tavily_response()
        result = tavily_search("Microsoft investor relations", cache_ttl=0)

        assert "results" in result
        assert len(result["results"]) == 1
        assert result["results"][0]["title"] == "Microsoft 2025 Annual Report"
        assert get_search_count() == 1

    @patch("lib.tavily_client.urlopen")
    def test_search_caching(self, mock_urlopen):
        """Should cache results and not make duplicate requests."""
        mock_urlopen.return_value = _mock_tavily_response()

        result1 = tavily_search("cached query", cache_ttl=3600)
        result2 = tavily_search("cached query", cache_ttl=3600)

        assert result1 == result2
        assert mock_urlopen.call_count == 1  # Only one HTTP request
        assert get_search_count() == 1  # Cache hit doesn't increment counter

    @patch("lib.tavily_client.urlopen")
    def test_search_caching_expired(self, mock_urlopen):
        """Should re-fetch when cache expires."""
        mock_urlopen.return_value = _mock_tavily_response()

        tavily_search("expire test", cache_ttl=0)  # No cache
        tavily_search("expire test", cache_ttl=0)  # No cache

        assert mock_urlopen.call_count == 2

    @patch("lib.tavily_client.urlopen")
    def test_search_retries_on_server_error(self, mock_urlopen):
        """Should retry on 5xx errors."""
        from urllib.error import HTTPError

        error_resp = MagicMock()
        error_resp.code = 500
        error_resp.reason = "Internal Server Error"

        # First call fails, second succeeds
        mock_urlopen.side_effect = [
            HTTPError("url", 500, "Internal Server Error", {}, None),
            _mock_tavily_response(),
        ]

        result = tavily_search("retry test", cache_ttl=0)
        assert "results" in result
        assert mock_urlopen.call_count == 2

    @patch("lib.tavily_client.urlopen")
    def test_search_retries_on_rate_limit(self, mock_urlopen):
        """Should retry on 429 rate limit."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = [
            HTTPError("url", 429, "Too Many Requests", {}, None),
            _mock_tavily_response(),
        ]

        result = tavily_search("rate limit test", cache_ttl=0)
        assert "results" in result

    @patch("lib.tavily_client.urlopen")
    def test_search_fails_on_client_error(self, mock_urlopen):
        """Should raise on non-429 4xx errors."""
        from urllib.error import HTTPError

        mock_urlopen.side_effect = HTTPError("url", 401, "Unauthorized", {}, None)

        with pytest.raises(RuntimeError, match="Tavily HTTP 401"):
            tavily_search("auth fail", cache_ttl=0)

    @patch("lib.tavily_client.urlopen")
    def test_search_timeout(self, mock_urlopen):
        """Should retry on timeout."""
        mock_urlopen.side_effect = TimeoutError("timed out")

        with pytest.raises(RuntimeError, match="failed after"):
            tavily_search("timeout test", cache_ttl=0, timeout=1)

    @patch("lib.tavily_client.urlopen")
    def test_search_malformed_json(self, mock_urlopen):
        """Should raise ValueError on bad JSON."""
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with pytest.raises(ValueError, match="Invalid JSON"):
            tavily_search("bad json", cache_ttl=0)


# ── Search Count Tests ───────────────────────────────────────────────────────
class TestSearchCount:
    @patch("lib.tavily_client.urlopen")
    def test_count_increments(self, mock_urlopen):
        """Should track search count."""
        mock_urlopen.return_value = _mock_tavily_response()

        tavily_search("count test 1", cache_ttl=0)
        tavily_search("count test 2", cache_ttl=0)

        assert get_search_count() == 2

    def test_reset_count(self):
        """Should reset counter."""
        reset_search_count()
        assert get_search_count() == 0


# ── Cache Tests ──────────────────────────────────────────────────────────────
class TestCache:
    @patch("lib.tavily_client.urlopen")
    def test_clear_cache(self, mock_urlopen):
        """Should clear cache and allow re-fetch."""
        mock_urlopen.return_value = _mock_tavily_response()

        tavily_search("clear test", cache_ttl=3600)
        assert mock_urlopen.call_count == 1

        clear_cache()
        tavily_search("clear test", cache_ttl=3600)
        assert mock_urlopen.call_count == 2
