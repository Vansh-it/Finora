"""Tests for company resolver."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.company_resolver import resolve_company, _parse_ticker_map, _is_ticker, _normalize, _ALIASES


# ── Mock SEC ticker data ─────────────────────────────────────────────────────
MOCK_TICKER_DATA = {
    "fields": ["cik_str", "ticker", "title"],
    "data": [
        [789019, "MSFT", "MICROSOFT CORP"],
        [320193, "AAPL", "APPLE INC"],
        [1045810, "NVDA", "NVIDIA CORP"],
        [1018724, "AMZN", "AMAZON COM INC"],
        [1652044, "GOOGL", "ALPHABET INC"],
        [1326801, "META", "META PLATFORMS INC"],
        [1318605, "TSLA", "TESLA INC"],
        [1067983, "BRK.B", "BERKSHIRE HATHAWAY INC"],
        [796343, "NFLX", "NETFLIX INC"],
        [200406, "JNJ", "JOHNSON & JOHNSON"],
        [886982, "V", "VISA INC"],
        [1141391, "MA", "MASTERCARD INC"],
    ]
}


def _mock_ticker_response():
    """Create a mock urllib response for ticker data."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(MOCK_TICKER_DATA).encode()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


# ── Helper tests ──────────────────────────────────────────────────────────────
class TestHelpers:
    def test_is_ticker_uppercase(self):
        assert _is_ticker("MSFT") is True

    def test_is_ticker_lowercase(self):
        assert _is_ticker("msft") is True

    def test_is_ticker_company_name(self):
        assert _is_ticker("Microsoft") is False

    def test_is_ticker_long_string(self):
        assert _is_ticker("MICROSOFT") is False

    def test_normalize_whitespace(self):
        assert _normalize("  Microsoft   Corp  ") == "microsoft corp"

    def test_normalize_case(self):
        assert _normalize("MSFT") == "msft"

    def test_aliases_exist(self):
        assert "microsoft" in _ALIASES
        assert "apple" in _ALIASES
        assert "nvidia" in _ALIASES


# ── Parse ticker map tests ───────────────────────────────────────────────────
class TestParseTickerMap:
    def test_parse_fields_data_format(self):
        result = _parse_ticker_map(MOCK_TICKER_DATA)
        assert len(result) == 12
        assert result[0]["ticker"] == "MSFT"
        assert result[0]["name"] == "MICROSOFT CORP"
        assert result[0]["cik"] == "0000789019"

    def test_parse_dict_format(self):
        data = {
            "0": {"cik_str": 789019, "ticker": "MSFT", "title": "MICROSOFT CORP"},
            "1": {"cik_str": 320193, "ticker": "AAPL", "title": "APPLE INC"},
        }
        result = _parse_ticker_map(data)
        assert len(result) == 2
        assert result[0]["ticker"] == "MSFT"

    def test_parse_list_of_lists_format(self):
        data = [[789019, "MICROSOFT CORP", "MSFT"], [320193, "APPLE INC", "AAPL"]]
        result = _parse_ticker_map(data)
        assert len(result) == 2
        assert result[0]["ticker"] == "MSFT"


# ── Resolve by ticker tests ──────────────────────────────────────────────────
class TestResolveByTicker:
    def test_resolve_msft(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("MSFT")
            assert company.ticker == "MSFT"
            assert company.name == "MICROSOFT CORP"
            assert company.cik == "0000789019"
            assert company.status == "resolved"

    def test_resolve_aapl(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("AAPL")
            assert company.ticker == "AAPL"
            assert company.name == "APPLE INC"

    def test_resolve_nvda(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("NVDA")
            assert company.ticker == "NVDA"
            assert company.name == "NVIDIA CORP"

    def test_resolve_amzn(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("AMZN")
            assert company.ticker == "AMZN"

    def test_resolve_googl(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("GOOGL")
            assert company.ticker == "GOOGL"
            assert company.name == "ALPHABET INC"

    def test_resolve_lowercase_ticker(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("msft")
            assert company.ticker == "MSFT"

    def test_invalid_ticker(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            with pytest.raises(ValueError, match="Could not resolve"):
                resolve_company("ZZZZZ")


# ── Resolve by name tests ────────────────────────────────────────────────────
class TestResolveByName:
    def test_resolve_microsoft_exact(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("MICROSOFT CORP")
            assert company.ticker == "MSFT"
            assert company.cik == "0000789019"

    def test_resolve_microsoft_alias(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("microsoft")
            assert company.ticker == "MSFT"

    def test_resolve_apple_alias(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("apple")
            assert company.ticker == "AAPL"

    def test_resolve_nvidia_alias(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("nvidia")
            assert company.ticker == "NVDA"

    def test_resolve_amazon_alias(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("amazon")
            assert company.ticker == "AMZN"

    def test_resolve_alphabet_alias(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("alphabet")
            assert company.ticker == "GOOGL"

    def test_resolve_google_alias(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("google")
            assert company.ticker == "GOOGL"

    def test_resolve_meta_alias(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("meta")
            assert company.ticker == "META"

    def test_resolve_facebook_alias(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("facebook")
            assert company.ticker == "META"

    def test_resolve_tesla_alias(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("tesla")
            assert company.ticker == "TSLA"


# ── Edge cases ────────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_empty_query(self):
        with pytest.raises(ValueError, match="non-empty string"):
            resolve_company("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="non-empty string"):
            resolve_company("   ")

    def test_none_like_query(self):
        with pytest.raises((ValueError, TypeError)):
            resolve_company(None)  # type: ignore

    def test_unresolvable_company(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            with pytest.raises(ValueError, match="Could not resolve"):
                resolve_company("XYZXYZ Corp that does not exist")

    def test_to_dict(self):
        with patch("lib.company_resolver.get_ticker_mapping", return_value=MOCK_TICKER_DATA):
            company = resolve_company("MSFT")
            d = company.to_dict()
            assert d["ticker"] == "MSFT"
            assert d["name"] == "MICROSOFT CORP"
            assert d["cik"] == "0000789019"
            assert d["status"] == "resolved"
