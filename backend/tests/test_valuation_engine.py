"""Tests for Twelve Data client and valuation engine."""

import os
import sys
import json
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.twelve_data_client import get_market_snapshot, fetch_quote, clear_cache
from lib.valuation_engine import calculate_valuation, _is_financial_institution


# ── Fixtures ─────────────────────────────────────────────────────────────────

def _make_session(
    ticker="MSFT",
    period_mode="latest",
    financial_stmts=None,
    calculated_metrics=None,
    market_data=None,
):
    """Build a minimal session dict for testing."""
    fs = financial_stmts or {
        "periods": ["FY2026"],
        "income_statement": {
            "revenue": {"value": 331_839_000_000, "period": "FY2026"},
            "net_income": {"value": 133_749_000_000, "period": "FY2026"},
            "operating_income": {"value": 155_237_000_000, "period": "FY2026"},
            "diluted_eps": {"value": 17.95, "period": "FY2026"},
        },
        "balance_sheet": {
            "total_assets": {"value": 758_376_000_000, "period": "FY2026"},
            "shareholders_equity": {"value": 442_387_000_000, "period": "FY2026"},
            "cash_and_equivalents": {"value": 78_440_000_000, "period": "FY2026"},
            "short_term_investments": {"value": 70_000_000_000, "period": "FY2026"},
            "long_term_debt": {"value": 42_000_000_000, "period": "FY2026"},
            "short_term_debt": {"value": 0, "period": "FY2026"},
        },
        "cash_flow": {
            "operating_cash_flow": {"value": 182_935_000_000, "period": "FY2026"},
            "capital_expenditures": {"value": -115_948_000_000, "period": "FY2026"},
        },
        "additional": {},
    }

    cm = calculated_metrics or {
        "periods": ["FY2026"],
        "annual_metrics": {
            "FY2026": {
                "free_cash_flow": {"value": 66_987_000_000, "period": "FY2026"},
                "ebitda": {"value": 190_000_000_000, "period": "FY2026"},
                "net_debt": {"value": -36_440_000_000, "period": "FY2026"},
                "gross_margin": {"value": 67.9, "period": "FY2026"},
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
        "price": 420.55,
        "price_date": "2025-07-25",
        "previous_close": 418.20,
        "percent_change": 0.56,
        "shares_outstanding": 7_430_000_000,
        "market_cap": None,
        "source": "Twelve Data",
    }

    return {
        "session_id": "test123",
        "company": "Microsoft Corporation",
        "period_mode": period_mode,
        "start_year": None,
        "end_year": None,
        "company_meta": {"name": "Microsoft Corporation", "ticker": ticker},
        "financial_statements": fs,
        "calculated_metrics": cm,
        "market_data": md,
    }


# ── Twelve Data Client Tests ────────────────────────────────────────────────

class TestTwelveDataClient:
    def test_market_snapshot_success(self):
        """Test successful market snapshot with mocked API."""
        clear_cache()
        mock_response = json.dumps({
            "symbol": "MSFT",
            "name": "Microsoft Corporation",
            "exchange": "NASDAQ",
            "currency": "USD",
            "close": "420.55",
            "previous_close": "418.20",
            "percent_change": "0.56",
            "timestamp": 1721913600,
        }).encode()

        mock_resp = MagicMock()
        mock_resp.read.return_value = mock_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = get_market_snapshot("MSFT")

        assert result["ticker"] == "MSFT"
        assert result["name"] == "Microsoft Corporation"
        assert result["price"] == 420.55
        assert result["previous_close"] == 418.20
        # Timestamp 1721913600 is 2024-07-25
        assert result["price_date"] == "2024-07-25"
        assert result["source"] == "Twelve Data"
        clear_cache()

    def test_market_snapshot_error(self):
        """Test graceful failure when API returns error."""
        clear_cache()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "code": 400,
            "message": "Invalid API KEY",
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            result = get_market_snapshot("FAKE")

        assert result.get("error")
        assert result["price"] is None
        clear_cache()

    def test_market_snapshot_network_error(self):
        """Test graceful failure on network error."""
        clear_cache()
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("timeout")):
            result = get_market_snapshot("MSFT")

        assert result.get("error")
        assert result["price"] is None
        clear_cache()

    def test_cache_behavior(self):
        """Test that cached results are reused."""
        clear_cache()
        mock_resp = MagicMock()
        mock_resp.read.return_value = json.dumps({
            "symbol": "MSFT", "name": "Microsoft", "close": "420.00",
            "previous_close": "418.00", "percent_change": "0.48", "timestamp": 1721913600,
        }).encode()
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp) as mock_url:
            get_market_snapshot("MSFT")
            get_market_snapshot("MSFT")
            # Second call should use cache — only 1 API call
            assert mock_url.call_count == 1

        clear_cache()


# ── Financial Institution Detection Tests ────────────────────────────────────

class TestFinancialInstitution:
    def test_jpmorgan_detected(self):
        session = _make_session(ticker="JPM")
        assert _is_financial_institution(session) is True

    def test_goldman_detected(self):
        session = _make_session(ticker="GS")
        assert _is_financial_institution(session) is True

    def test_microsoft_not_financial(self):
        session = _make_session(ticker="MSFT")
        assert _is_financial_institution(session) is False

    def test_apple_not_financial(self):
        session = _make_session(ticker="AAPL")
        assert _is_financial_institution(session) is False


# ── Valuation Engine Tests ───────────────────────────────────────────────────

class TestValuationEngine:
    def test_basic_valuation(self):
        """Test basic valuation with MSFT-like data."""
        session = _make_session()
        result = calculate_valuation(session)

        assert "market_data" in result
        assert "valuation_metrics" in result
        assert "period_alignment" in result

        vm = result["valuation_metrics"]
        assert "pe_ratio" in vm
        assert "price_to_sales" in vm
        assert "price_to_book" in vm
        assert "ev_to_revenue" in vm
        assert "ev_to_ebitda" in vm
        assert "enterprise_value" in vm
        assert "market_cap" in vm

    def test_pe_ratio_calculation(self):
        """Verify P/E = Market Cap / Net Income."""
        session = _make_session()
        result = calculate_valuation(session)
        pe = result["valuation_metrics"]["pe_ratio"]

        # Market cap = price * shares = 420.55 * 7.43B = ~3124.7B
        # P/E = 3124.7B / 133.75B = ~23.4x
        assert pe["status"] == "calculated"
        assert pe["value"] is not None
        assert pe["value"] > 15
        assert pe["value"] < 30
        assert "x" in pe["display_value"]

    def test_price_to_sales_calculation(self):
        """Verify P/S = Market Cap / Revenue."""
        session = _make_session()
        result = calculate_valuation(session)
        ps = result["valuation_metrics"]["price_to_sales"]
        assert ps["status"] == "calculated"
        assert ps["value"] is not None
        assert ps["value"] > 5
        assert ps["value"] < 15

    def test_price_to_book_calculation(self):
        """Verify P/B = Market Cap / Equity."""
        session = _make_session()
        result = calculate_valuation(session)
        pb = result["valuation_metrics"]["price_to_book"]
        assert pb["status"] == "calculated"
        assert pb["value"] is not None
        assert pb["value"] > 5

    def test_ev_to_revenue(self):
        """Verify EV/Revenue."""
        session = _make_session()
        result = calculate_valuation(session)
        evr = result["valuation_metrics"]["ev_to_revenue"]
        assert evr["status"] == "calculated"
        assert evr["value"] is not None

    def test_ev_to_ebitda(self):
        """Verify EV/EBITDA."""
        session = _make_session()
        result = calculate_valuation(session)
        eve = result["valuation_metrics"]["ev_to_ebitda"]
        assert eve["status"] == "calculated"
        assert eve["value"] is not None
        assert eve["value"] > 10

    def test_earnings_yield(self):
        """Verify Earnings Yield = Net Income / Market Cap * 100."""
        session = _make_session()
        result = calculate_valuation(session)
        ey = result["valuation_metrics"]["earnings_yield"]
        assert ey["status"] == "calculated"
        assert ey["value"] is not None
        assert ey["value"] > 0
        assert "%" in ey["display_value"]

    def test_fcf_yield(self):
        """Verify FCF Yield = FCF / Market Cap * 100."""
        session = _make_session()
        result = calculate_valuation(session)
        fy = result["valuation_metrics"]["fcf_yield"]
        assert fy["status"] == "calculated"
        assert fy["value"] is not None
        assert fy["value"] > 0

    def test_negative_earnings(self):
        """P/E should be NM when net income <= 0."""
        session = _make_session()
        session["financial_statements"]["income_statement"]["net_income"]["value"] = -5_000_000_000
        result = calculate_valuation(session)
        pe = result["valuation_metrics"]["pe_ratio"]
        assert pe["display_value"] == "NM"

    def test_negative_ebitda(self):
        """EV/EBITDA should be NM when EBITDA <= 0."""
        session = _make_session()
        session["calculated_metrics"]["annual_metrics"]["FY2026"]["ebitda"]["value"] = -10_000_000_000
        result = calculate_valuation(session)
        eve = result["valuation_metrics"]["ev_to_ebitda"]
        assert eve["display_value"] == "NM"

    def test_negative_equity(self):
        """P/B should be NM when equity <= 0."""
        session = _make_session()
        session["financial_statements"]["balance_sheet"]["shareholders_equity"]["value"] = -10_000_000_000
        result = calculate_valuation(session)
        pb = result["valuation_metrics"]["price_to_book"]
        assert pb["display_value"] == "NM"

    def test_missing_market_data(self):
        """All valuation should be N/A when price is missing."""
        session = _make_session()
        session["market_data"]["price"] = None
        result = calculate_valuation(session)
        vm = result["valuation_metrics"]
        assert vm["pe_ratio"]["status"] == "unavailable"
        assert vm["market_cap"]["status"] == "unavailable"

    def test_financial_institution_suppression(self):
        """Financial institution should be flagged."""
        session = _make_session(ticker="JPM")
        result = calculate_valuation(session)
        assert result["is_financial_institution"] is True

    def test_period_alignment_metadata(self):
        """Verify period alignment is stored."""
        session = _make_session()
        result = calculate_valuation(session)
        pa = result["period_alignment"]
        assert pa["financial_period"] == "FY2026"
        assert "FY2026" in pa["note"]

    def test_enterprise_value_calculation(self):
        """Verify EV = Market Cap + Debt - Cash."""
        session = _make_session()
        result = calculate_valuation(session)
        ev = result["valuation_metrics"]["enterprise_value"]
        assert ev["status"] == "calculated"
        assert ev["value"] is not None
        # Market cap ~3125B + Debt 42B - Cash 148.44B = ~3018.56B
        assert ev["value"] > 2_500_000_000_000

    def test_ev_to_ebit_negative(self):
        """EV/EBIT should be NM when operating income <= 0."""
        session = _make_session()
        session["financial_statements"]["income_statement"]["operating_income"]["value"] = -1_000_000_000
        result = calculate_valuation(session)
        eve = result["valuation_metrics"]["ev_to_ebit"]
        assert eve["display_value"] == "NM"

    def test_no_fcf(self):
        """FCF Yield should be unavailable when FCF missing."""
        session = _make_session()
        session["calculated_metrics"]["annual_metrics"]["FY2026"]["free_cash_flow"] = None
        result = calculate_valuation(session)
        fy = result["valuation_metrics"]["fcf_yield"]
        assert fy["status"] == "unavailable"

    def test_net_debt_to_ev(self):
        """Net Debt / EV should be calculated."""
        session = _make_session()
        result = calculate_valuation(session)
        ndev = result["valuation_metrics"]["net_debt_to_ev"]
        assert ndev["status"] == "calculated"

    def test_ev_to_fcf(self):
        """EV/FCF should be calculated."""
        session = _make_session()
        result = calculate_valuation(session)
        evf = result["valuation_metrics"]["ev_to_fcf"]
        assert evf["status"] == "calculated"
        assert evf["value"] > 0

    def test_source_evidence_in_inputs(self):
        """All inputs should have source info."""
        session = _make_session()
        result = calculate_valuation(session)
        pe = result["valuation_metrics"]["pe_ratio"]
        for inp in pe["inputs"]:
            assert "source" in inp
            assert inp["source"] != ""

    def test_negative_fcf_yield(self):
        """FCF Yield should be NM when FCF <= 0."""
        session = _make_session()
        session["calculated_metrics"]["annual_metrics"]["FY2026"]["free_cash_flow"]["value"] = -5_000_000_000
        result = calculate_valuation(session)
        fy = result["valuation_metrics"]["fcf_yield"]
        assert fy["display_value"] == "NM"

    def test_market_data_in_result(self):
        """Market data should be included in output."""
        session = _make_session()
        result = calculate_valuation(session)
        md = result["market_data"]
        assert md["price"] == 420.55
        assert md["ticker"] == "MSFT"

    def test_multiple_periods(self):
        """Should work with multiple periods."""
        session = _make_session()
        session["financial_statements"]["periods"] = ["FY2025", "FY2026"]
        result = calculate_valuation(session)
        assert result["period_alignment"]["financial_period"] == "FY2026"
