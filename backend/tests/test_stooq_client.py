"""Tests for Stooq free historical price fallback client."""

import pytest
from unittest.mock import patch, MagicMock
from lib.stooq_client import (
    normalize_symbol, fetch_historical_price, fetch_historical_series,
    clear_cache, _parse_csv, stooq_cache,
)


@pytest.fixture(autouse=True)
def _reset():
    """Reset state between tests."""
    clear_cache()
    yield
    clear_cache()


# ── Symbol Normalization ──────────────────────────────────────────────────────

class TestSymbolNormalization:
    def test_aapl(self):
        assert normalize_symbol("AAPL") == "aapl.us"

    def test_msft(self):
        assert normalize_symbol("MSFT") == "msft.us"

    def test_wmt(self):
        assert normalize_symbol("WMT") == "wmt.us"

    def test_lowercase(self):
        assert normalize_symbol("aapl") == "aapl.us"

    def test_with_suffix(self):
        assert normalize_symbol("AAPL.US") == "aapl.us"

    def test_hyphenated_ticker(self):
        assert normalize_symbol("BRK-B") == "brk-b.us"

    def test_empty_string(self):
        assert normalize_symbol("") is None

    def test_none(self):
        assert normalize_symbol(None) is None

    def test_non_alphanumeric(self):
        assert normalize_symbol("AAPL@#$") is None


# ── CSV Parsing ───────────────────────────────────────────────────────────────

class TestCSVParsing:
    def test_valid_csv(self):
        csv = "Symbol,Date,Time,Open,High,Low,Close,Volume\naapl.us,2023-09-29,16:00,170.0,172.0,169.0,171.0,50000000\n"
        records = _parse_csv(csv, "aapl.us")
        assert len(records) == 1
        assert records[0]["close"] == 171.0
        assert records[0]["date"] == "2023-09-29"
        assert records[0]["symbol"] == "aapl.us"

    def test_multiple_rows(self):
        csv = "Symbol,Date,Time,Open,High,Low,Close,Volume\naapl.us,2023-09-28,16:00,169.0,171.0,168.0,170.0,40000000\naapl.us,2023-09-29,16:00,170.0,172.0,169.0,171.0,50000000\n"
        records = _parse_csv(csv, "aapl.us")
        assert len(records) == 2

    def test_nd_values_skipped(self):
        csv = "Symbol,Date,Time,Open,High,Low,Close,Volume\naapl.us,2023-09-29,16:00,N/D,N/D,N/D,N/D,N/D\n"
        records = _parse_csv(csv, "aapl.us")
        assert len(records) == 0

    def test_empty_csv(self):
        records = _parse_csv("", "aapl.us")
        assert len(records) == 0

    def test_malformed_csv(self):
        records = _parse_csv("not,a,valid,csv", "aapl.us")
        assert len(records) == 0

    def test_zero_price_skipped(self):
        csv = "Symbol,Date,Time,Open,High,Low,Close,Volume\naapl.us,2023-09-29,16:00,0,0,0,0,0\n"
        records = _parse_csv(csv, "aapl.us")
        assert len(records) == 0

    def test_negative_price_skipped(self):
        csv = "Symbol,Date,Time,Open,High,Low,Close,Volume\naapl.us,2023-09-29,16:00,0,0,0,-10,0\n"
        records = _parse_csv(csv, "aapl.us")
        assert len(records) == 0


# ── Fetch Historical Price ────────────────────────────────────────────────────

class TestFetchHistoricalPrice:
    def test_valid_fetch(self):
        csv_response = "Symbol,Date,Time,Open,High,Low,Close,Volume\naapl.us,2023-09-29,16:00,170.0,172.0,169.0,171.0,50000000\n"
        mock_resp = MagicMock()
        mock_resp.read.return_value = csv_response.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_historical_price("AAPL", "2023-09-29")
            assert result is not None
            assert result["close"] == 171.0
            assert result["source"] == "stooq"

    def test_empty_response(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b""
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_historical_price("AAPL", "2023-09-29")
            assert result is None

    def test_invalid_ticker(self):
        result = fetch_historical_price("", "2023-09-29")
        assert result is None

    def test_invalid_date(self):
        result = fetch_historical_price("AAPL", "invalid-date")
        assert result is None

    def test_cache_hit(self):
        csv_response = "Symbol,Date,Time,Open,High,Low,Close,Volume\naapl.us,2023-09-29,16:00,171.0,172.0,169.0,171.0,50000000\n"
        mock_resp = MagicMock()
        mock_resp.read.return_value = csv_response.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_url:
            result1 = fetch_historical_price("AAPL", "2023-09-29")
            result2 = fetch_historical_price("AAPL", "2023-09-29")
            assert result1 == result2
            # Only one HTTP call
            assert mock_url.call_count == 1

    def test_network_error(self):
        with patch("urllib.request.urlopen", side_effect=ConnectionError("network")):
            # After retries, should return None
            result = fetch_historical_price("AAPL", "2023-09-29")
            assert result is None


# ── Fetch Historical Series ───────────────────────────────────────────────────

class TestFetchHistoricalSeries:
    def test_valid_series(self):
        csv_response = (
            "Symbol,Date,Time,Open,High,Low,Close,Volume\n"
            "aapl.us,2023-09-28,16:00,170.0,171.0,169.0,170.5,40000000\n"
            "aapl.us,2023-09-29,16:00,171.0,172.0,170.0,171.5,50000000\n"
        )
        mock_resp = MagicMock()
        mock_resp.read.return_value = csv_response.encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_historical_series("AAPL", "2023-09-28", "2023-09-29")
            assert len(result) == 2
            assert result[0]["date"] == "2023-09-28"
            assert result[1]["date"] == "2023-09-29"
            assert all(r["source"] == "stooq" for r in result)

    def test_empty_series(self):
        mock_resp = MagicMock()
        mock_resp.read.return_value = b""
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)
        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_historical_series("AAPL", "2023-09-28")
            assert len(result) == 0
