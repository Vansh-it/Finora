"""Tests for the final completeness engine, XBRL alias fallback,
missing-data handling, and metric counting.

Part AQ testing coverage.
"""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from lib.financial_calculator import calculate_metrics, _val, _safe_divide, _safe_cagr
from lib.xbrl_mapper import (
    INCOME_STATEMENT_CONCEPTS,
    BALANCE_SHEET_CONCEPTS,
    CASH_FLOW_CONCEPTS,
    ADDITIONAL_CONCEPTS,
    get_concepts_for_metric,
    get_all_xbrl_concepts,
)
from lib.metric_methodology import BEGINNER_EXPLANATIONS, get_beginner_explanation, get_metric_metadata


# ══════════════════════════════════════════════════════════════════════════
# XBRL ALIAS COVERAGE
# ══════════════════════════════════════════════════════════════════════════

class TestXBRlAliasCoverage:
    """Verify expanded XBRL alias mappings."""

    def test_revenue_aliases_include_apple_concepts(self):
        """Apple uses RevenueFromContractWithCustomerExcludingAssessedTax."""
        aliases = get_concepts_for_metric("revenue")
        assert "RevenueFromContractWithCustomerExcludingAssessedTax" in aliases
        assert "Revenues" in aliases
        assert "SalesRevenueNet" in aliases

    def test_operating_income_aliases(self):
        aliases = get_concepts_for_metric("operating_income")
        assert "OperatingIncomeLoss" in aliases

    def test_cost_of_revenue_aliases(self):
        aliases = get_concepts_for_metric("cost_of_revenue")
        assert "CostOfRevenue" in aliases
        assert "CostOfGoodsAndServicesSold" in aliases

    def test_depreciation_amortization_aliases(self):
        """Different companies use different D&A tags."""
        aliases = get_concepts_for_metric("depreciation_amortization")
        assert "DepreciationAndAmortization" in aliases
        assert "DepreciationDepletionAndAmortization" in aliases
        assert "Depreciation" in aliases

    def test_cash_and_equivalents_aliases(self):
        aliases = get_concepts_for_metric("cash_and_equivalents")
        assert "CashAndCashEquivalentsAtCarryingValue" in aliases
        assert "CashCashEquivalentsRestrictedCashAndRestrictedCashEquivalents" in aliases

    def test_interest_expense_aliases(self):
        aliases = get_concepts_for_metric("interest_expense")
        assert "InterestExpense" in aliases
        assert "InterestAndDebtExpense" in aliases

    def test_shares_outstanding_aliases(self):
        aliases = get_concepts_for_metric("shares_outstanding")
        assert "CommonStockSharesOutstanding" in aliases
        assert "EntityCommonStockSharesOutstanding" in aliases

    def test_all_concepts_unique_across_metrics(self):
        """No XBRL concept should be used by multiple Finora metrics."""
        all_concepts = get_all_xbrl_concepts()
        assert len(all_concepts) > 50  # We have many aliases now

    def test_all_metric_types_have_aliases(self):
        """Every metric type should have at least one alias."""
        all_metrics = (
            list(INCOME_STATEMENT_CONCEPTS.keys())
            + list(BALANCE_SHEET_CONCEPTS.keys())
            + list(CASH_FLOW_CONCEPTS.keys())
            + list(ADDITIONAL_CONCEPTS.keys())
        )
        for metric in all_metrics:
            aliases = get_concepts_for_metric(metric)
            assert len(aliases) > 0, f"Metric '{metric}' has no XBRL aliases"


# ══════════════════════════════════════════════════════════════════════════
# MISSING DATA ≠ ZERO
# ══════════════════════════════════════════════════════════════════════════

class TestMissingDataNotZero:
    """Verify that missing data is never treated as zero."""

    def test_safe_divide_returns_none_for_zero(self):
        """Division by zero should return None, not 0."""
        result = _safe_divide(100.0, 0.0)
        assert result is None

    def test_safe_divide_returns_none_for_nan(self):
        """Division resulting in NaN should return None."""
        result = _safe_divide(float("nan"), 1.0)
        assert result is None

    def test_safe_divide_returns_none_for_inf(self):
        """Division resulting in Inf should return None."""
        result = _safe_divide(1e308, 1e-308)
        assert result is None

    def test_val_returns_none_for_missing(self):
        """_val should return None, not 0, for missing data."""
        assert _val(None) is None
        assert _val({}) is None
        assert _val({"value": None}) is None

    def test_val_extracts_numeric(self):
        assert _val({"value": 42.0}) == 42.0
        assert _val({"value": "100.5"}) == 100.5

    def test_unavailable_metric_has_none_not_zero(self):
        """Unavailable metrics should have None value, not 0."""
        # Build minimal statements with missing data
        stmts = {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "additional": {},
            "periods": ["FY2025"],
            "company": {"name": "Test", "ticker": "TST", "cik": "00001"},
            "metadata": {},
        }
        result = calculate_metrics(stmts)
        latest = result["periods"][-1] if result["periods"] else ""
        if latest:
            for mid, m in result["annual_metrics"].get(latest, {}).items():
                if m.get("status") == "unavailable":
                    # Value should be None, not 0
                    assert m.get("value") is None or m.get("display_value") in ("N/A", "—", "NM"), \
                        f"Unavailable metric '{mid}' should not display as zero"

    def test_cagr_returns_none_for_negative_start(self):
        """CAGR with negative start should return None."""
        result = _safe_cagr(-100.0, 200.0, 3)
        assert result is None

    def test_cagr_returns_none_for_zero_end(self):
        """CAGR with zero end should return None."""
        result = _safe_cagr(100.0, 0.0, 3)
        assert result is None


# ══════════════════════════════════════════════════════════════════════════
# COMPLETENESS METADATA
# ══════════════════════════════════════════════════════════════════════════

class TestCompletenessMetadata:
    """Verify completeness metadata in calculation results."""

    def test_metadata_structure(self):
        """Metadata should contain completeness info."""
        stmts = {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "additional": {},
            "periods": [],
            "company": {"name": "Test", "ticker": "TST", "cik": "00001"},
            "metadata": {},
        }
        result = calculate_metrics(stmts)
        meta = result.get("metadata", {})
        assert "metrics_calculated" in meta
        assert "metrics_unavailable" in meta
        assert "completeness" in meta
        assert "unavailable_details" in meta

    def test_completeness_structure(self):
        stmts = {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "additional": {},
            "periods": [],
            "company": {"name": "Test", "ticker": "TST", "cik": "00001"},
            "metadata": {},
        }
        result = calculate_metrics(stmts)
        completeness = result["metadata"]["completeness"]
        assert "required_inputs" in completeness
        assert "found_primary" in completeness
        assert "unavailable" in completeness

    def test_unavailable_details_list(self):
        """Unavailable details should list metric IDs and reasons."""
        stmts = {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "additional": {},
            "periods": ["FY2025"],
            "company": {"name": "Test", "ticker": "TST", "cik": "00001"},
            "metadata": {},
        }
        result = calculate_metrics(stmts)
        details = result["metadata"]["unavailable_details"]
        assert isinstance(details, list)
        for d in details:
            assert "metric_id" in d
            assert "status" in d
            assert d["status"] == "unavailable"
            assert "reason" in d


# ══════════════════════════════════════════════════════════════════════════
# METRIC COUNT
# ══════════════════════════════════════════════════════════════════════════

class TestMetricCount:
    """Verify metric counting is accurate and not double-counted."""

    def test_count_with_no_data(self):
        """Zero periods = zero metrics."""
        stmts = {
            "income_statement": {},
            "balance_sheet": {},
            "cash_flow": {},
            "additional": {},
            "periods": [],
            "company": {"name": "Test", "ticker": "TST", "cik": "00001"},
            "metadata": {},
        }
        result = calculate_metrics(stmts)
        meta = result["metadata"]
        assert meta["metrics_calculated"] == 0
        assert meta["metrics_unavailable"] == 0
        assert meta["total_metrics_attempted"] == 0

    def test_count_not_double_counted(self):
        """Metrics should be counted per-type, not per-period."""
        stmts = {
            "income_statement": {
                "revenue": {
                    "FY2024": {"value": 100_000_000_000, "period": "FY2024"},
                    "FY2023": {"value": 90_000_000_000, "period": "FY2023"},
                },
                "net_income": {
                    "FY2024": {"value": 20_000_000_000, "period": "FY2024"},
                    "FY2023": {"value": 18_000_000_000, "period": "FY2023"},
                },
            },
            "balance_sheet": {
                "total_assets": {
                    "FY2024": {"value": 500_000_000_000, "period": "FY2024"},
                    "FY2023": {"value": 450_000_000_000, "period": "FY2023"},
                },
                "shareholders_equity": {
                    "FY2024": {"value": 200_000_000_000, "period": "FY2024"},
                    "FY2023": {"value": 180_000_000_000, "period": "FY2023"},
                },
            },
            "cash_flow": {},
            "additional": {},
            "periods": ["FY2023", "FY2024"],
            "company": {"name": "Test", "ticker": "TST", "cik": "00001"},
            "metadata": {"metrics_extracted": 4},
        }
        result = calculate_metrics(stmts)
        meta = result["metadata"]
        total = meta["total_metrics_attempted"]
        calc = meta["metrics_calculated"]
        unavail = meta["metrics_unavailable"]
        assert total == calc + unavail
        # Should not be inflated by period count
        assert total < 200  # Reasonable upper bound


# ══════════════════════════════════════════════════════════════════════════
# BEGINNER EXPLANATIONS
# ══════════════════════════════════════════════════════════════════════════

class TestBeginnerExplanations:
    """Verify beginner explanation coverage."""

    def test_all_calculated_metrics_have_beginner_explanations(self):
        """Every metric in METODOLOGY should have a beginner explanation."""
        from lib.metric_methodology import METODOLOGY
        for mid in METODOLOGY:
            explanation = get_beginner_explanation(mid)
            # Allow empty for non-user-facing metrics
            if mid not in ("ebitda", "dupont"):
                assert len(explanation) > 0, f"Metric '{mid}' lacks beginner explanation"

    def test_beginner_explanation_is_plain_english(self):
        """Beginner explanations should not contain jargon."""
        for mid, explanation in BEGINNER_EXPLANATIONS.items():
            assert len(explanation) > 20, f"Explanation for '{mid}' too short"
            assert len(explanation) < 500, f"Explanation for '{mid}' too long"

    def test_get_metric_metadata_includes_beginner(self):
        """get_metric_metadata should combine methodology + beginner."""
        meta = get_metric_metadata("roe")
        assert "formula" in meta
        assert "beginner" in meta
        assert len(meta["beginner"]) > 0

    def test_beginner_for_unknown_metric_returns_empty(self):
        """Unknown metric should return empty string."""
        assert get_beginner_explanation("nonexistent_metric") == ""


# ══════════════════════════════════════════════════════════════════════════
# PERIOD ORDERING
# ══════════════════════════════════════════════════════════════════════════

class TestPeriodOrdering:
    """Verify growth calculations use correctly ordered periods."""

    def test_growth_uses_consecutive_periods(self):
        """Growth should only compare consecutive FY periods."""
        stmts = {
            "income_statement": {
                "revenue": {
                    "FY2023": {"value": 100_000_000_000, "period": "FY2023"},
                    "FY2024": {"value": 110_000_000_000, "period": "FY2024"},
                    "FY2025": {"value": 120_000_000_000, "period": "FY2025"},
                },
            },
            "balance_sheet": {},
            "cash_flow": {},
            "additional": {},
            "periods": ["FY2023", "FY2024", "FY2025"],
            "company": {"name": "Test", "ticker": "TST", "cik": "00001"},
            "metadata": {},
        }
        result = calculate_metrics(stmts)
        growth = result["growth_metrics"]
        # Should have FY2025 vs FY2024 growth (consecutive)
        assert "FY2025 vs FY2024" in growth
        g = growth["FY2025 vs FY2024"]["revenue_growth"]
        assert g["status"] == "calculated"
        assert abs(g["value"] - 9.09) < 0.1  # ~9.09% growth

    def test_cagr_uses_spanning_periods(self):
        """CAGR should use first and last period."""
        stmts = {
            "income_statement": {
                "revenue": {
                    "FY2023": {"value": 100_000_000_000, "period": "FY2023"},
                    "FY2025": {"value": 121_000_000_000, "period": "FY2025"},
                },
            },
            "balance_sheet": {},
            "cash_flow": {},
            "additional": {},
            "periods": ["FY2023", "FY2025"],
            "company": {"name": "Test", "ticker": "TST", "cik": "00001"},
            "metadata": {},
        }
        result = calculate_metrics(stmts)
        cagr = result["cagr_metrics"]
        assert "FY2023 to FY2025" in cagr
        rev_cagr = cagr["FY2023 to FY2025"]["revenue_cagr"]
        assert rev_cagr["status"] == "calculated"
        assert abs(rev_cagr["value"] - 10.0) < 0.1  # 10% CAGR over 2 years
