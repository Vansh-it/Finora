"""Tests for FMP (Financial Modeling Prep) client."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock
from lib.fmp_client import (
    is_available, get_company_profile, get_income_statement,
    get_balance_sheet, get_cash_flow, get_key_metrics,
    get_financial_ratios, get_enterprise_value, get_market_cap,
    get_quote, get_historical_price, get_shares_outstanding,
    get_ebitda, clear_cache, get_instrumentation, reset_instrumentation,
    _fmp_get, _get_api_key, _cache_get, _cache_set, _fmp_cache,
)


@pytest.fixture(autouse=True)
def _reset():
    """Reset state between tests."""
    clear_cache()
    reset_instrumentation()
    yield
    clear_cache()
    reset_instrumentation()


# ── API Key ───────────────────────────────────────────────────────────────────

class TestAPIKey:
    def test_is_available_with_key(self):
        with patch.dict(os.environ, {"FMP_API_KEY": "test_key_12345"}):
            assert is_available() is True

    def test_is_available_without_key(self):
        with patch.dict(os.environ, {"FMP_API_KEY": ""}):
            assert is_available() is False

    def test_is_available_with_short_key(self):
        with patch.dict(os.environ, {"FMP_API_KEY": "abc"}):
            assert is_available() is False


# ── Company Profile ───────────────────────────────────────────────────────────

class TestCompanyProfile:
    def test_valid_response(self):
        mock_data = [{"symbol": "AAPL", "companyName": "Apple Inc.", "mktCap": 3000000000000}]
        with patch("lib.fmp_client._fmp_get", return_value=mock_data):
            result = get_company_profile("AAPL")
            assert result["symbol"] == "AAPL"
            assert result["mktCap"] == 3000000000000

    def test_empty_response(self):
        with patch("lib.fmp_client._fmp_get", return_value=[]):
            result = get_company_profile("INVALID")
            assert result is None

    def test_none_response(self):
        with patch("lib.fmp_client._fmp_get", return_value=None):
            result = get_company_profile("AAPL")
            assert result is None


# ── Error Handling ────────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_429_rate_limit(self):
        import urllib.error
        with patch("lib.fmp_client._get_api_key", return_value="test_key_12345"):
            with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
                "https://example.com", 429, "Rate Limited", {}, None
            )):
                result = _fmp_get("quote/AAPL")
                assert result is None

    def test_403_plan_restriction(self):
        import urllib.error
        with patch("lib.fmp_client._get_api_key", return_value="test_key_12345"):
            with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
                "https://example.com", 403, "Forbidden", {}, None
            )):
                result = _fmp_get("quote/AAPL")
                assert result is None

    def test_500_server_error(self):
        import urllib.error
        with patch("lib.fmp_client._get_api_key", return_value="test_key_12345"):
            with patch("urllib.request.urlopen", side_effect=urllib.error.HTTPError(
                "https://example.com", 500, "Server Error", {}, None
            )):
                result = _fmp_get("quote/AAPL")
                assert result is None

    def test_timeout(self):
        with patch("lib.fmp_client._get_api_key", return_value="test_key_12345"):
            with patch("urllib.request.urlopen", side_effect=TimeoutError("timeout")):
                result = _fmp_get("quote/AAPL")
                assert result is None

    def test_malformed_json(self):
        with patch("lib.fmp_client._get_api_key", return_value="test_key_12345"):
            mock_resp = MagicMock()
            mock_resp.read.return_value = b"not json at all"
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            with patch("urllib.request.urlopen", return_value=mock_resp):
                result = _fmp_get("quote/AAPL")
                assert result is None

    def test_empty_response(self):
        with patch("lib.fmp_client._get_api_key", return_value="test_key_12345"):
            mock_resp = MagicMock()
            mock_resp.read.return_value = b""
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            with patch("urllib.request.urlopen", return_value=mock_resp):
                result = _fmp_get("quote/AAPL")
                assert result is None

    def test_fmp_error_message(self):
        with patch("lib.fmp_client._get_api_key", return_value="test_key_12345"):
            mock_resp = MagicMock()
            mock_resp.read.return_value = json.dumps({"Error Message": "Invalid API KEY"}).encode()
            mock_resp.__enter__ = lambda s: s
            mock_resp.__exit__ = MagicMock(return_value=False)
            with patch("urllib.request.urlopen", return_value=mock_resp):
                result = _fmp_get("quote/AAPL")
                assert result is None

    def test_no_api_key_returns_none(self):
        with patch("lib.fmp_client._get_api_key", return_value=""):
            result = _fmp_get("quote/AAPL")
            assert result is None


# ── Cache ─────────────────────────────────────────────────────────────────────

class TestCache:
    def test_cache_hit(self):
        """Directly test cache mechanism."""
        cache_key = "test:quote:AAPL"
        _cache_set(cache_key, {"close": 150.0})
        result = _cache_get(cache_key)
        assert result == {"close": 150.0}

    def test_cache_miss(self):
        result = _cache_get("nonexistent_key")
        assert result is None

    def test_clear_cache(self):
        _cache_set("test:clear", {"data": 1})
        clear_cache()
        result = _cache_get("test:clear")
        assert result is None


# ── Instrumentation ───────────────────────────────────────────────────────────

class TestInstrumentation:
    def test_reset(self):
        reset_instrumentation()
        instr = get_instrumentation()
        assert instr["requests_this_research"] == 0
        assert instr["cache_hits"] == 0
        assert instr["cache_misses"] == 0


# ── Historical Price ─────────────────────────────────────────────────────────

class TestHistoricalPrice:
    def test_valid_historical(self):
        mock_data = {"historical": [{"date": "2023-09-29", "close": 171.0}]}
        with patch("lib.fmp_client._fmp_get", return_value=mock_data):
            result = get_historical_price("AAPL", "2023-09-29")
            assert result is not None
            assert len(result) == 1
            assert result[0]["close"] == 171.0

    def test_empty_historical(self):
        with patch("lib.fmp_client._fmp_get", return_value={"historical": []}):
            result = get_historical_price("AAPL", "2023-01-01")
            assert result is not None
            assert len(result) == 0


# ── Market Cap ────────────────────────────────────────────────────────────────

class TestMarketCap:
    def test_from_profile(self):
        mock_profile = {"mktCap": 3e12}
        with patch("lib.fmp_client.get_company_profile", return_value=mock_profile):
            result = get_market_cap("AAPL")
            assert result == 3e12

    def test_no_profile(self):
        with patch("lib.fmp_client.get_company_profile", return_value=None):
            result = get_market_cap("INVALID")
            assert result is None
