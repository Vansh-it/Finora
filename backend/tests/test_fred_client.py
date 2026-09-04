"""Tests for FRED macro context client."""

import json
import os
import pytest
from unittest.mock import patch, MagicMock
from lib.fred_client import (
    is_available, get_macro_snapshot, get_macro_for_dashboard,
    clear_cache, _fred_get,
)


@pytest.fixture(autouse=True)
def _reset():
    clear_cache()
    yield
    clear_cache()


# ── Availability ──────────────────────────────────────────────────────────────

class TestAvailability:
    def test_available_with_key(self):
        with patch.dict(os.environ, {"FRED_API_KEY": "test_key_12345"}):
            assert is_available() is True

    def test_not_available_without_key(self):
        with patch.dict(os.environ, {"FRED_API_KEY": ""}):
            assert is_available() is False

    def test_not_available_with_short_key(self):
        with patch.dict(os.environ, {"FRED_API_KEY": "abc"}):
            assert is_available() is False


# ── Macro Snapshot ────────────────────────────────────────────────────────────

class TestMacroSnapshot:
    def test_missing_key_returns_unavailable(self):
        with patch.dict(os.environ, {"FRED_API_KEY": ""}):
            result = get_macro_snapshot()
            assert result["available"] is False
            assert "FRED_API_KEY" in result.get("reason", "")

    def test_valid_response(self):
        mock_obs = {"observations": [{"date": "2024-01-01", "value": "5.25"}]}
        with patch.dict(os.environ, {"FRED_API_KEY": "test_key_12345"}):
            with patch("lib.fred_client._fred_get", return_value=mock_obs.get("observations")[0]):
                result = get_macro_snapshot()
                assert result["available"] is True
                assert result["fed_funds_rate"] is not None
                assert result["treasury_10y"] is not None
                assert result["cpi"] is not None

    def test_cache_hit(self):
        mock_obs = {"date": "2024-01-01", "value": "5.25", "series_id": "DFF"}
        with patch.dict(os.environ, {"FRED_API_KEY": "test_key_12345"}):
            with patch("lib.fred_client._fred_get", return_value=mock_obs) as mock_fred:
                result1 = get_macro_snapshot()
                result2 = get_macro_snapshot()
                assert result1 == result2
                # Only one FRED call per series
                assert mock_fred.call_count == 3  # 3 series

    def test_graceful_degradation(self):
        with patch.dict(os.environ, {"FRED_API_KEY": "test_key_12345"}):
            with patch("lib.fred_client._fred_get", return_value=None):
                result = get_macro_snapshot()
                assert result["available"] is True
                assert result["fed_funds_rate"] is None


# ── Dashboard Mapping ─────────────────────────────────────────────────────────

class TestDashboardMapping:
    def test_dashboard_format(self):
        with patch.dict(os.environ, {"FRED_API_KEY": ""}):
            result = get_macro_for_dashboard()
            assert "available" in result
            assert "strip" in result
            assert "attribution" in result

    def test_dashboard_strip_empty_when_unavailable(self):
        with patch.dict(os.environ, {"FRED_API_KEY": ""}):
            result = get_macro_for_dashboard()
            assert result["strip"] == []

    def test_attribution_present(self):
        with patch.dict(os.environ, {"FRED_API_KEY": ""}):
            result = get_macro_for_dashboard()
            assert "FRED" in result["attribution"]
            assert "Federal Reserve" in result["attribution"]


# ── Error Handling ────────────────────────────────────────────────────────────

class TestErrorHandling:
    def test_timeout(self):
        with patch.dict(os.environ, {"FRED_API_KEY": "test_key_12345"}):
            with patch("urllib.request.urlopen", side_effect=TimeoutError("timeout")):
                result = _fred_get("DFF")
                assert result is None

    def test_network_error(self):
        with patch.dict(os.environ, {"FRED_API_KEY": "test_key_12345"}):
            with patch("urllib.request.urlopen", side_effect=ConnectionError("network")):
                result = _fred_get("DFF")
                assert result is None

    def test_no_api_key(self):
        with patch.dict(os.environ, {"FRED_API_KEY": ""}):
            result = _fred_get("DFF")
            assert result is None
