"""Tests for Jina Reader API client."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.jina_client import (
    read_url,
    clear_cache,
    get_read_count,
    reset_read_count,
    _get_api_key,
)


@pytest.fixture(autouse=True)
def _clean_cache():
    clear_cache()
    reset_read_count()
    yield
    clear_cache()
    reset_read_count()


def _mock_jina_response(content="Test content", title="Test Title", status=200):
    data = {
        "data": [{"content": content, "title": title}],
        "code": 200,
    }
    raw = json.dumps(data).encode("utf-8")
    mock_resp = MagicMock()
    mock_resp.read.return_value = raw
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    mock_resp.status = status
    mock_resp.code = status
    return mock_resp


class TestApiKey:
    def test_api_key_loads(self):
        key = _get_api_key()
        assert key.startswith("jina_")

    @patch.dict(os.environ, {"JINA_API_KEY": ""})
    def test_missing_key_raises(self):
        with pytest.raises(RuntimeError, match="JINA_API_KEY not set"):
            _get_api_key()


class TestReadUrl:
    @patch("lib.jina_client.urlopen")
    def test_basic_read(self, mock_urlopen):
        mock_urlopen.return_value = _mock_jina_response()
        result = read_url("https://example.com", cache_ttl=0)

        assert result["status"] == "success"
        assert result["content"] == "Test content"
        assert result["title"] == "Test Title"
        assert result["content_length"] == len("Test content")
        assert get_read_count() == 1

    @patch("lib.jina_client.urlopen")
    def test_caching(self, mock_urlopen):
        mock_urlopen.return_value = _mock_jina_response()

        result1 = read_url("https://cached.com", cache_ttl=3600)
        result2 = read_url("https://cached.com", cache_ttl=3600)

        assert result1 == result2
        assert mock_urlopen.call_count == 1

    @patch("lib.jina_client.urlopen")
    def test_empty_content(self, mock_urlopen):
        mock_urlopen.return_value = _mock_jina_response(content="")
        result = read_url("https://empty.com", cache_ttl=0)

        assert result["status"] == "empty"
        assert result["content_length"] == 0

    @patch("lib.jina_client.urlopen")
    def test_content_truncation(self, mock_urlopen):
        long_content = "x" * 150_000
        mock_urlopen.return_value = _mock_jina_response(content=long_content)
        result = read_url("https://long.com", cache_ttl=0)

        assert result["content_length"] <= 100_100  # MAX + truncation message
        assert "truncated" in result["content"]

    @patch("lib.jina_client.urlopen")
    def test_404_returns_not_found(self, mock_urlopen):
        from urllib.error import HTTPError
        mock_urlopen.side_effect = HTTPError("url", 404, "Not Found", {}, None)

        result = read_url("https://missing.com", cache_ttl=0)
        assert result["status"] == "not_found"

    @patch("lib.jina_client.urlopen")
    def test_429_retries(self, mock_urlopen):
        from urllib.error import HTTPError
        mock_urlopen.side_effect = [
            HTTPError("url", 429, "Too Many Requests", {}, None),
            _mock_jina_response(),
        ]

        result = read_url("https://rate-limited.com", cache_ttl=0)
        assert result["status"] == "success"
        assert mock_urlopen.call_count == 2

    @patch("lib.jina_client.urlopen")
    def test_timeout_returns_error(self, mock_urlopen):
        mock_urlopen.side_effect = TimeoutError("timed out")

        result = read_url("https://slow.com", cache_ttl=0, timeout=1)
        assert result["status"] == "error"

    @patch("lib.jina_client.urlopen")
    def test_malformed_json(self, mock_urlopen):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b"not json"
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        mock_urlopen.return_value = mock_resp

        with pytest.raises(ValueError, match="Invalid JSON"):
            read_url("https://bad-json.com", cache_ttl=0)

    @patch("lib.jina_client.urlopen")
    def test_read_count(self, mock_urlopen):
        mock_urlopen.return_value = _mock_jina_response()

        read_url("https://count1.com", cache_ttl=0)
        read_url("https://count2.com", cache_ttl=0)
        assert get_read_count() == 2

    @patch("lib.jina_client.urlopen")
    def test_clear_cache(self, mock_urlopen):
        mock_urlopen.return_value = _mock_jina_response()

        read_url("https://clear.com", cache_ttl=3600)
        clear_cache()
        read_url("https://clear.com", cache_ttl=3600)
        assert mock_urlopen.call_count == 2
