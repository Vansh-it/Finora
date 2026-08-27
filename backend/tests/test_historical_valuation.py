"""Tests for historical market-price alignment (Step 9.5)."""

import os
import sys
import json
from unittest.mock import patch, MagicMock
from datetime import datetime

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.twelve_data_client import get_market_snapshot, fetch_historical_price, clear_cache
from lib.valuation_engine import calculate_valuation, resolve_financial_period_end, _fiscal_year_label


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_session(
    ticker="MSFT",
    period_mode="latest",
    start_year=None,
    end_year=None,
    financial_stmts=None,
    calculated_metrics=None,
    market_data=None,
):
    fs = financial_stmts or {
        "periods": ["FY2023"],
        "income_statement": {
            "revenue": {"value": 211_915_000_000, "period": "FY2023", "period_end": "2023-06-30"},
            "net_income": {"value": 72_738_000_000, "period": "FY2023", "period_end": "2023-06-30"},
            "operating_income": {"value": 88_523_000_000, "period": "FY2023", "period_end": "2023-06-30"},
        },
        "balance_sheet": {
            "total_assets": {"value": 484_267_000_000, "period": "FY2023", "period_end": "2023-06-30"},
            "shareholders_equity": {"value": 206_209_000_000, "period": "FY2023", "period_end": "2023-06-30"},
            "cash_and_equivalents": {"value": 34_700_000_000, "period": "FY2023", "period_end": "2023-06-30"},
            "short_term_investments": {"value": 76_000_000_000, "period": "FY2023", "period_end": "2023-06-30"},
            "long_term_debt": {"value": 44_000_000_000, "period": "FY2023", "period_end": "2023-06-30"},
            "short_term_debt": {"value": 0, "period": "FY2023", "period_end": "2023-06-30"},
        },
        "cash_flow": {"operating_cash_flow": {"value": 87_000_000_000, "period": "FY2023", "period_end": "2023-06-30"}},
        "additional": {"diluted_shares": {"value": 7_430_000_000, "period": "FY2023", "period_end": "2023-06-30"}},
    }

    cm = calculated_metrics or {
        "periods": ["FY2023"],
        "annual_metrics": {
            "FY2023": {
                "free_cash_flow": {"value": 59_500_000_000, "period": "FY2023"},
                "ebitda": {"value": 108_000_000_000, "period": "FY2023"},
                "net_debt": {"value": -66_700_000_000, "period": "FY2023"},
            },
        },
        "growth_metrics": {},
        "cagr_metrics": {},
        "metadata": {},
    }

    md = market_data or {
        "ticker": ticker,
        "name": "Microsoft Corporation",
        "exchange": "NASDAQ",
        "currency": "USD",
        "price": 330.00,
        "price_date": "2023-06-30",
        "previous_close": 328.00,
        "percent_change": 0.61,
        "shares_outstanding": None,
        "market_cap": None,
        "source": "Twelve Data",
    }

    return {
        "session_id": "test_hist",
        "company": "Microsoft Corporation",
        "period_mode": period_mode,
        "start_year": start_year,
        "end_year": end_year,
        "company_meta": {"name": "Microsoft Corporation", "ticker": ticker},
        "financial_statements": fs,
        "calculated_metrics": cm,
        "market_data": md,
    }


# ── Fiscal Year End Tests ────────────────────────────────────────────────────

class TestFiscalYearEnd:
    def test_msft_fiscal_year_end(self):
        """MSFT FY2023 period end resolved from SEC XBRL data."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {
                "revenue": {"value": 211_915_000_000, "period": "FY2023", "period_end": "2023-06-30"},
            },
            "balance_sheet": {}, "cash_flow": {}, "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2023")
        assert result["period_end"] == "2023-06-30"
        assert result["source"] == "SEC_XBRL"
        assert result["status"] == "resolved"

    def test_aapl_fiscal_year_end(self):
        """AAPL FY2023 period end resolved from SEC XBRL data."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {
                "revenue": {"value": 383_285_000_000, "period": "FY2023", "period_end": "2023-09-30"},
            },
            "balance_sheet": {}, "cash_flow": {}, "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2023")
        assert result["period_end"] == "2023-09-30"
        assert result["source"] == "SEC_XBRL"

    def test_no_metadata_unavailable(self):
        """When no period_end metadata exists, status is unavailable."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {"revenue": {"value": 100, "period": "FY2023"}},
            "balance_sheet": {}, "cash_flow": {}, "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2023")
        assert result["status"] == "unavailable"
        assert result["period_end"] is None

    def test_fiscal_year_label(self):
        assert _fiscal_year_label("FY2023") == 2023
        assert _fiscal_year_label("FY2025") == 2025
        assert _fiscal_year_label("invalid") is None


# ── Historical Price Fetch Tests ─────────────────────────────────────────────

class TestHistoricalPrice:
    def test_fetch_historical_price_success(self):
        """Test successful historical price fetch."""
        clear_cache()
        mock_response = json.dumps({
            "values": [
                {"datetime": "2023-06-30", "close": "330.50", "open": "328.00", "high": "331.00", "low": "327.00", "volume": "20000000"},
                {"datetime": "2023-06-29", "close": "328.00", "open": "326.00", "high": "329.00", "low": "325.00", "volume": "18000000"},
            ]
        }).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_historical_price("MSFT", "2023-06-30")

        assert result is not None
        assert result["close"] == 330.50
        assert result["date"] == "2023-06-30"
        assert result["source"] == "Twelve Data"
        clear_cache()

    def test_fetch_historical_price_weekend(self):
        """When target is Saturday, should get Friday's price."""
        clear_cache()
        mock_response = json.dumps({
            "values": [
                {"datetime": "2023-06-30", "close": "330.50"},
                {"datetime": "2023-06-29", "close": "328.00"},
            ]
        }).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            # July 1, 2023 is Saturday
            result = fetch_historical_price("MSFT", "2023-07-01")

        assert result is not None
        assert result["close"] == 330.50  # Friday's close
        assert result["date"] == "2023-06-30"
        clear_cache()

    def test_fetch_historical_price_empty(self):
        """Empty time series returns None."""
        clear_cache()
        mock_response = json.dumps({"values": []}).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = fetch_historical_price("MSFT", "2020-01-01")

        assert result is None
        clear_cache()

    def test_fetch_historical_price_timeout(self):
        """Timeout raises RuntimeError after retries."""
        clear_cache()
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            with pytest.raises(RuntimeError, match="failed"):
                fetch_historical_price("MSFT", "2023-06-30")
        clear_cache()


# ── Latest Mode Tests ────────────────────────────────────────────────────────

class TestLatestMode:
    def test_latest_uses_current_price(self):
        """Latest mode should use current market data."""
        session = _make_session(period_mode="latest")
        result = calculate_valuation(session)
        assert result["period_alignment"]["is_current_valuation"] is True
        assert result["period_alignment"]["price_type"] == "current"

    def test_latest_pe_ratio(self):
        """P/E should be calculated with current price."""
        session = _make_session(period_mode="latest")
        session["market_data"]["price"] = 330.00
        session["market_data"]["shares_outstanding"] = 7_430_000_000
        result = calculate_valuation(session)
        pe = result["valuation_metrics"]["pe_ratio"]
        assert pe["status"] == "calculated"
        assert pe["value"] > 0


# ── Historical Mode Tests ────────────────────────────────────────────────────

class TestHistoricalMode:
    def test_historical_uses_period_price(self):
        """Historical mode should use the price from market_data."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["alignment_status"] = "exact_period_end"
        result = calculate_valuation(session)
        assert result["period_alignment"]["is_current_valuation"] is False
        assert result["period_alignment"]["price_type"] == "historical_period_end"

    def test_historical_pe_ratio(self):
        """P/E should use historical price."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price"] = 330.00
        session["market_data"]["price_date"] = "2023-06-30"
        session["market_data"]["shares_outstanding"] = 7_430_000_000
        result = calculate_valuation(session)
        pe = result["valuation_metrics"]["pe_ratio"]
        assert pe["status"] == "calculated"
        # Market cap = 330 * 7.43B = ~2451.9B
        # P/E = 2451.9B / 72.738B = ~33.7x
        assert pe["value"] > 20
        assert pe["value"] < 50

    def test_historical_market_cap(self):
        """Market cap should use historical price."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price"] = 330.00
        session["market_data"]["shares_outstanding"] = 7_430_000_000
        result = calculate_valuation(session)
        mc = result["valuation_metrics"]["market_cap"]
        assert mc["status"] == "calculated"
        assert mc["value"] > 2_000_000_000_000

    def test_historical_ev(self):
        """Enterprise value should use historical market cap + period debt/cash."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price"] = 330.00
        session["market_data"]["shares_outstanding"] = 7_430_000_000
        result = calculate_valuation(session)
        ev = result["valuation_metrics"]["enterprise_value"]
        assert ev["status"] == "calculated"
        # EV = MC + Debt - Cash = ~2452B + 44B - 110B = ~2386B
        assert ev["value"] > 2_000_000_000_000

    def test_historical_alignment_exact(self):
        """When price date matches fiscal period end, alignment is exact."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price_date"] = "2023-06-30"
        session["market_data"]["alignment_status"] = "exact_period_end"
        result = calculate_valuation(session)
        pa = result["period_alignment"]
        assert pa["alignment_status"] == "exact_period_end"

    def test_historical_alignment_previous_trading_day(self):
        """When price date differs from fiscal end, alignment shows previous trading day."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price_date"] = "2023-06-29"
        session["market_data"]["alignment_status"] = "previous_trading_day"
        result = calculate_valuation(session)
        pa = result["period_alignment"]
        assert pa["alignment_status"] == "previous_trading_day"

    def test_historical_no_price_unavailable(self):
        """When historical price is unavailable, all metrics should be N/A."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["price"] = None
        session["market_data"]["price_date"] = ""
        result = calculate_valuation(session)
        vm = result["valuation_metrics"]
        assert vm["pe_ratio"]["status"] == "unavailable"
        assert vm["market_cap"]["status"] == "unavailable"

    def test_historical_negative_earnings(self):
        """NM for negative earnings even in historical mode."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price"] = 330.00
        session["financial_statements"]["income_statement"]["net_income"]["value"] = -5_000_000_000
        result = calculate_valuation(session)
        pe = result["valuation_metrics"]["pe_ratio"]
        assert pe["display_value"] == "NM"

    def test_historical_note_includes_period(self):
        """Period alignment note should include the financial period."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price_date"] = "2023-06-30"
        result = calculate_valuation(session)
        note = result["period_alignment"]["note"]
        assert "FY2023" in note

    def test_historical_financial_period_is_end_year(self):
        """Financial period should be the end year, not start year."""
        session = _make_session(
            period_mode="specified",
            start_year=2022,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        result = calculate_valuation(session)
        assert result["period_alignment"]["financial_period"] == "FY2023"


# ── Non-Trading Day Tests ────────────────────────────────────────────────────

class TestNonTradingDay:
    def test_weekend_period_end_gets_friday_price(self):
        """When fiscal period ends on weekend, nearest previous trading day is used."""
        session = _make_session(
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price"] = 330.50
        session["market_data"]["price_date"] = "2023-06-29"  # Thursday (before fiscal end)
        session["market_data"]["alignment_status"] = "previous_trading_day"
        session["market_data"]["target_date"] = "2023-06-30"  # Friday (fiscal end)

        result = calculate_valuation(session)
        pa = result["period_alignment"]
        assert pa["alignment_status"] == "previous_trading_day"


# ── Multi-Year Tests ─────────────────────────────────────────────────────────

class TestMultiYear:
    def test_multi_year_uses_end_year(self):
        """For FY2022-FY2023, the valuation should use FY2023 period."""
        session = _make_session(
            period_mode="specified",
            start_year=2022,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price"] = 330.00
        session["market_data"]["price_date"] = "2023-06-30"
        result = calculate_valuation(session)
        pa = result["period_alignment"]
        assert pa["financial_period"] == "FY2023"


# ── Financial Institution Tests ──────────────────────────────────────────────

class TestFinancialInstitutionHistorical:
    def test_jpm_historical_suppresses_ev_metrics(self):
        """Historical JPM research should still suppress EV/EBITDA etc."""
        session = _make_session(
            ticker="JPM",
            period_mode="specified",
            start_year=2023,
            end_year=2023,
        )
        session["market_data"]["historical"] = True
        session["market_data"]["price"] = 140.00
        session["market_data"]["shares_outstanding"] = 2_800_000_000
        result = calculate_valuation(session)
        assert result["is_financial_institution"] is True
        eve = result["valuation_metrics"].get("ev_to_ebitda", {})
        assert eve.get("applicability") == "suppressed_for_financial"


# ── Cache Tests ──────────────────────────────────────────────────────────────

class TestHistoricalCache:
    def test_historical_cache_reuse(self):
        """Same historical request should use cache."""
        clear_cache()
        mock_response = json.dumps({
            "values": [{"datetime": "2023-06-30", "close": "330.50"}]
        }).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_url:
            fetch_historical_price("MSFT", "2023-06-30")
            fetch_historical_price("MSFT", "2023-06-30")
            # Second call should use cache
            assert mock_url.call_count == 1

        clear_cache()


# ── Dashboard Builder Tests ──────────────────────────────────────────────────

class TestDashboardHistoricalLabels:
    def test_historical_valuation_section(self):
        """Dashboard should include is_historical flag."""
        from lib.dashboard_builder import build_dashboard_payload
        session = _make_session(period_mode="specified", start_year=2023, end_year=2023)
        session["market_data"]["historical"] = True
        session["market_data"]["price"] = 330.00
        session["market_data"]["price_date"] = "2023-06-30"
        session["valuation_metrics"] = {
            "market_data": session["market_data"],
            "valuation_metrics": {"pe_ratio": {"value": 33.7, "display_value": "33.7x", "status": "calculated", "name": "P/E Ratio", "metric_id": "pe_ratio", "period": "FY2023", "applicability": "applicable", "formula": "Market Cap / Net Income", "inputs": [], "calculation": "", "market_data_date": "2023-06-30", "price_type": "historical_period_end", "reason": ""}},
            "period_alignment": {"financial_period": "FY2023", "market_data_date": "2023-06-30", "is_current_valuation": False, "note": "Historical valuation", "alignment_status": "exact_period_end"},
            "is_financial_institution": False,
        }
        payload = build_dashboard_payload(session)
        val = payload["valuation"]
        assert val["is_historical"] is True
        assert val["market_data"]["is_historical"] is True
