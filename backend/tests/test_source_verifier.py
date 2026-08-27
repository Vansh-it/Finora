"""Tests for cross-source verification engine."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.source_verifier import (
    verify_sources,
    _compare_values,
    _normalize_external_value,
    _build_sec_lookup,
    EXACT_MATCH,
    WITHIN_TOLERANCE,
    MISMATCH,
    NOT_COMPARABLE,
    MISSING_EXTERNAL,
    MISSING_SEC,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────
def _sec_statements():
    """Return a mock SEC financial statements dict."""
    return {
        "income_statement": {
            "revenue": {
                "value": 331_839_000_000,
                "unit": "USD",
                "period": "FY2026",
                "period_end": "2026-06-30",
            },
            "net_income": {
                "value": 133_749_000_000,
                "unit": "USD",
                "period": "FY2026",
                "period_end": "2026-06-30",
            },
            "diluted_eps": {
                "value": 17.95,
                "unit": "USD/shares",
                "period": "FY2026",
                "period_end": "2026-06-30",
            },
        },
        "balance_sheet": {
            "total_assets": {
                "value": 758_376_000_000,
                "unit": "USD",
                "period": "FY2026",
                "period_end": "2026-06-30",
            },
        },
        "cash_flow": {},
    }


# ── Value Comparison Tests ───────────────────────────────────────────────────
class TestCompareValues:
    def test_exact_match(self):
        result = _compare_values(100.0, 100.0, "revenue")
        assert result["verification_status"] == EXACT_MATCH
        assert result["difference"] == 0

    def test_within_tolerance_small(self):
        result = _compare_values(100_000_000_000, 99_999_000_000, "revenue")
        assert result["verification_status"] == WITHIN_TOLERANCE

    def test_within_tolerance_rounding(self):
        # 331.8B vs 331,839,000,000 — should normalize
        result = _compare_values(331_839_000_000, 331.8, "revenue")
        assert result["verification_status"] == WITHIN_TOLERANCE

    def test_material_mismatch(self):
        result = _compare_values(100_000_000_000, 80_000_000_000, "revenue")
        assert result["verification_status"] == MISMATCH
        assert result["difference_pct"] > 10

    def test_eps_comparison(self):
        result = _compare_values(17.95, 17.90, "diluted_eps")
        assert result["verification_status"] == WITHIN_TOLERANCE

    def test_eps_mismatch(self):
        result = _compare_values(17.95, 15.00, "diluted_eps")
        assert result["verification_status"] == MISMATCH

    def test_both_missing(self):
        result = _compare_values(None, None, "revenue")
        assert result["verification_status"] == NOT_COMPARABLE

    def test_sec_missing(self):
        result = _compare_values(None, 100.0, "revenue")
        assert result["verification_status"] == MISSING_SEC

    def test_external_missing(self):
        result = _compare_values(100.0, None, "revenue")
        assert result["verification_status"] == MISSING_EXTERNAL


# ── Normalization Tests ──────────────────────────────────────────────────────
class TestNormalization:
    def test_normalize_millions_to_raw(self):
        result = _normalize_external_value(331839, 331_839_000_000, "revenue")
        assert result == 331_839_000_000

    def test_normalize_already_raw(self):
        result = _normalize_external_value(331_839_000_000, 331_839_000_000, "revenue")
        assert result == 331_839_000_000

    def test_normalize_millions_to_raw(self):
        result = _normalize_external_value(331839, 331_839_000_000, "revenue")
        assert result == 331_839_000_000

    def test_normalize_no_change_similar(self):
        result = _normalize_external_value(100.0, 105.0, "diluted_eps")
        assert result == 100.0


# ── SEC Lookup Tests ─────────────────────────────────────────────────────────
class TestSecLookup:
    def test_build_lookup(self):
        lookup = _build_sec_lookup(_sec_statements())
        assert "revenue" in lookup
        assert "FY2026" in lookup["revenue"]
        assert lookup["revenue"]["FY2026"]["value"] == 331_839_000_000

    def test_lookup_preserves_period_type(self):
        lookup = _build_sec_lookup(_sec_statements())
        assert lookup["diluted_eps"]["FY2026"]["period_type"] == "annual"


# ── Main Verification Tests ──────────────────────────────────────────────────
class TestVerifySources:
    def test_exact_match_revenue(self):
        ext_facts = [{
            "metric_id": "revenue",
            "value": 331_839_000_000,
            "unit": "USD",
            "period": "FY2026",
            "period_type": "annual",
            "source_provider": "Microsoft IR",
        }]

        result = verify_sources(_sec_statements(), ext_facts, [], "Microsoft", "MSFT")
        assert result["summary"]["exact_matches"] == 1
        assert result["summary"]["mismatches"] == 0

    def test_rounded_match(self):
        ext_facts = [{
            "metric_id": "revenue",
            "value": 331.8,  # In billions
            "unit": "USD",
            "period": "FY2026",
            "period_type": "annual",
            "source_provider": "Microsoft IR",
        }]

        result = verify_sources(_sec_statements(), ext_facts, [], "Microsoft", "MSFT")
        total_match = result["summary"]["exact_matches"] + result["summary"]["within_tolerance"]
        assert total_match >= 1

    def test_mismatch_detected(self):
        ext_facts = [{
            "metric_id": "revenue",
            "value": 200_000_000_000,  # Wrong value
            "unit": "USD",
            "period": "FY2026",
            "period_type": "annual",
            "source_provider": "Bad Source",
        }]

        result = verify_sources(_sec_statements(), ext_facts, [], "Microsoft", "MSFT")
        assert result["summary"]["mismatches"] == 1

    def test_different_period_no_sec_match(self):
        """Quarterly external fact vs annual SEC — no period match, so missing_sec."""
        ext_facts = [{
            "metric_id": "revenue",
            "value": 100_000_000,
            "unit": "USD",
            "period": "Q3-FY2026",
            "period_type": "quarterly",
            "source_provider": "Source",
        }]

        result = verify_sources(_sec_statements(), ext_facts, [], "Microsoft", "MSFT")
        # No SEC value for Q3-FY2026 (SEC only has FY2026), so missing_sec
        assert result["summary"]["missing_sec"] == 1

    def test_missing_external(self):
        ext_facts = []  # No external facts

        result = verify_sources(_sec_statements(), ext_facts, [], "Microsoft", "MSFT")
        # No comparisons if no external facts
        assert result["summary"]["total_compared"] == 0

    def test_management_commentary_preserved(self):
        commentary = [{
            "topic": "revenue_drivers",
            "summary": "Cloud grew 22% YoY.",
            "sentiment": "positive",
            "importance": "high",
        }]

        result = verify_sources(_sec_statements(), [], commentary, "Microsoft", "MSFT")
        assert len(result["management_commentary"]) == 1
        assert result["management_commentary"][0]["topic"] == "revenue_drivers"

    def test_multiple_metrics(self):
        ext_facts = [
            {"metric_id": "revenue", "value": 331_839_000_000, "period": "FY2026", "period_type": "annual", "source_provider": "IR"},
            {"metric_id": "net_income", "value": 133_749_000_000, "period": "FY2026", "period_type": "annual", "source_provider": "IR"},
            {"metric_id": "diluted_eps", "value": 17.95, "period": "FY2026", "period_type": "annual", "source_provider": "IR"},
        ]

        result = verify_sources(_sec_statements(), ext_facts, [], "Microsoft", "MSFT")
        assert result["summary"]["total_compared"] == 3
        assert result["summary"]["exact_matches"] == 3

    def test_empty_statements(self):
        ext_facts = [{"metric_id": "revenue", "value": 100, "period": "FY2026", "period_type": "annual", "source_provider": "IR"}]

        result = verify_sources({}, ext_facts, [], "Test", "TST")
        assert result["summary"]["missing_sec"] == 1

    def test_primary_source_preserved(self):
        result = verify_sources(_sec_statements(), [], [], "Microsoft", "MSFT")
        assert result["primary_source"] == "SEC XBRL"
