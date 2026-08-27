"""Tests for SEC XBRL period-end resolution."""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.valuation_engine import resolve_financial_period_end, calculate_valuation


# ── resolve_financial_period_end tests ────────────────────────────────────────

class TestPeriodResolution:
    def test_msft_from_income_statement(self):
        """MSFT FY2023 resolved from income statement period_end."""
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

    def test_aapl_from_balance_sheet(self):
        """AAPL FY2023 resolved from balance sheet period_end."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {},
            "balance_sheet": {
                "total_assets": {"value": 352_755_000_000, "period": "FY2023", "period_end": "2023-09-30"},
            },
            "cash_flow": {}, "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2023")
        assert result["period_end"] == "2023-09-30"
        assert result["source"] == "SEC_XBRL"

    def test_nvda_from_cash_flow(self):
        """NVDA FY2024 resolved from cash flow period_end."""
        stmts = {
            "periods": ["FY2024"],
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {
                "operating_cash_flow": {"value": 60_000_000_000, "period": "FY2024", "period_end": "2024-01-28"},
            },
            "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2024")
        assert result["period_end"] == "2024-01-28"
        assert result["source"] == "SEC_XBRL"

    def test_period_keyed_dict_format(self):
        """Works with period-keyed dict format (specified mode)."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {
                "revenue": {
                    "FY2023": {"value": 211_915_000_000, "period": "FY2023", "period_end": "2023-06-30"},
                },
            },
            "balance_sheet": {}, "cash_flow": {}, "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2023")
        assert result["period_end"] == "2023-06-30"
        assert result["source"] == "SEC_XBRL"

    def test_no_period_end_metadata(self):
        """Unavailable when no period_end in any fact."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {
                "revenue": {"value": 100, "period": "FY2023"},
            },
            "balance_sheet": {}, "cash_flow": {}, "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2023")
        assert result["status"] == "unavailable"
        assert result["period_end"] is None
        assert "fiscal period-end" in result["reason"].lower()

    def test_empty_statements(self):
        """Unavailable when statements are empty."""
        result = resolve_financial_period_end({}, "FY2023")
        assert result["status"] == "unavailable"
        assert result["period_end"] is None

    def test_period_not_found(self):
        """Unavailable when target period doesn't exist in data."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {
                "revenue": {"value": 100, "period": "FY2023", "period_end": "2023-06-30"},
            },
            "balance_sheet": {}, "cash_flow": {}, "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2024")
        assert result["status"] == "unavailable"

    def test_multiple_metrics_same_period(self):
        """First matching metric wins (all have same period_end for same period)."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {
                "revenue": {"value": 100, "period": "FY2023", "period_end": "2023-06-30"},
                "net_income": {"value": 50, "period": "FY2023", "period_end": "2023-06-30"},
            },
            "balance_sheet": {}, "cash_flow": {}, "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2023")
        assert result["period_end"] == "2023-06-30"

    def test_additional_facts_checked(self):
        """Also checks additional facts for period_end."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "additional": {
                "diluted_shares": {"value": 7_430_000_000, "period": "FY2023", "period_end": "2023-06-30"},
            },
        }
        result = resolve_financial_period_end(stmts, "FY2023")
        assert result["period_end"] == "2023-06-30"
        assert result["source"] == "SEC_XBRL"

    def test_calendar_year_company(self):
        """Calendar year company (Dec 31) resolved from SEC data."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {
                "revenue": {"value": 383_285_000_000, "period": "FY2023", "period_end": "2023-12-31"},
            },
            "balance_sheet": {}, "cash_flow": {}, "additional": {},
        }
        result = resolve_financial_period_end(stmts, "FY2023")
        assert result["period_end"] == "2023-12-31"
        assert result["source"] == "SEC_XBRL"


# ── Valuation with resolved period end ───────────────────────────────────────

class TestValuationWithResolvedPeriod:
    def test_historical_uses_resolved_period_end(self):
        """Historical valuation uses period_end from SEC XBRL, not hardcoded."""
        stmts = {
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
        cm = {
            "periods": ["FY2023"],
            "annual_metrics": {"FY2023": {
                "free_cash_flow": {"value": 59_500_000_000, "period": "FY2023"},
                "ebitda": {"value": 108_000_000_000, "period": "FY2023"},
                "net_debt": {"value": -66_700_000_000, "period": "FY2023"},
            }},
            "growth_metrics": {}, "cagr_metrics": {}, "metadata": {},
        }
        session = {
            "company": "Microsoft Corporation",
            "period_mode": "specified",
            "start_year": 2022, "end_year": 2023,
            "company_meta": {"name": "Microsoft Corporation", "ticker": "MSFT"},
            "financial_statements": stmts,
            "calculated_metrics": cm,
            "market_data": {
                "ticker": "MSFT", "price": 330.00, "price_date": "2023-06-29",
                "source": "Twelve Data", "historical": True,
                "alignment_status": "previous_trading_day", "target_date": "2023-06-30",
            },
        }
        result = calculate_valuation(session)
        pa = result["period_alignment"]
        assert pa["financial_period_end"] == "2023-06-30"
        assert pa["period_end_source"] == "SEC_XBRL"

    def test_unavailable_period_end_marks_metrics_unavailable(self):
        """When period_end cannot be resolved, all metrics become unavailable."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {
                "revenue": {"value": 100, "period": "FY2023"},
            },
            "balance_sheet": {}, "cash_flow": {}, "additional": {},
        }
        cm = {
            "periods": ["FY2023"],
            "annual_metrics": {"FY2023": {
                "free_cash_flow": {"value": 50, "period": "FY2023"},
                "ebitda": {"value": 80, "period": "FY2023"},
            }},
            "growth_metrics": {}, "cagr_metrics": {}, "metadata": {},
        }
        session = {
            "company": "Test Corp",
            "period_mode": "specified",
            "start_year": 2022, "end_year": 2023,
            "company_meta": {"name": "Test Corp", "ticker": "TST"},
            "financial_statements": stmts,
            "calculated_metrics": cm,
            "market_data": {
                "ticker": "TST", "price": 50.00, "price_date": "2023-06-29",
                "source": "Twelve Data", "historical": True,
            },
        }
        result = calculate_valuation(session)
        pa = result["period_alignment"]
        assert pa["alignment_status"] == "unavailable"
        # All calculated metrics should be unavailable (share_price is 'reported')
        for key, m in result["valuation_metrics"].items():
            if m.get("status") == "reported":
                continue  # share_price is reported, not calculated
            assert m["status"] == "unavailable", f"{key} should be unavailable"

    def test_latest_mode_unchanged(self):
        """Latest mode still works without period_end resolution."""
        stmts = {
            "periods": ["FY2023"],
            "income_statement": {
                "revenue": {"value": 211_915_000_000, "period": "FY2023"},
                "net_income": {"value": 72_738_000_000, "period": "FY2023"},
            },
            "balance_sheet": {
                "total_assets": {"value": 484_267_000_000, "period": "FY2023"},
                "shareholders_equity": {"value": 206_209_000_000, "period": "FY2023"},
                "cash_and_equivalents": {"value": 34_700_000_000, "period": "FY2023"},
                "short_term_investments": {"value": 76_000_000_000, "period": "FY2023"},
                "long_term_debt": {"value": 44_000_000_000, "period": "FY2023"},
                "short_term_debt": {"value": 0, "period": "FY2023"},
            },
            "cash_flow": {"operating_cash_flow": {"value": 87_000_000_000, "period": "FY2023"}},
            "additional": {"diluted_shares": {"value": 7_430_000_000, "period": "FY2023"}},
        }
        cm = {
            "periods": ["FY2023"],
            "annual_metrics": {"FY2023": {
                "free_cash_flow": {"value": 59_500_000_000, "period": "FY2023"},
                "ebitda": {"value": 108_000_000_000, "period": "FY2023"},
            }},
            "growth_metrics": {}, "cagr_metrics": {}, "metadata": {},
        }
        session = {
            "company": "Microsoft Corporation",
            "period_mode": "latest",
            "company_meta": {"name": "Microsoft Corporation", "ticker": "MSFT"},
            "financial_statements": stmts,
            "calculated_metrics": cm,
            "market_data": {
                "ticker": "MSFT", "price": 491.71, "price_date": "2026-08-25",
                "source": "Twelve Data",
            },
        }
        result = calculate_valuation(session)
        assert result["period_alignment"]["is_current_valuation"] is True
        pe = result["valuation_metrics"]["pe_ratio"]
        assert pe["status"] == "calculated"
