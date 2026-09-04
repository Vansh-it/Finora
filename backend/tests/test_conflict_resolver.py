"""Tests for conflict resolution engine."""

import pytest
from lib.conflict_resolver import (
    compare_values, resolve_metric, build_cross_check_report,
    EXACT_MATCH, WITHIN_TOLERANCE, MATERIAL_MISMATCH, NOT_COMPARABLE,
)


class TestCompareValues:
    def test_exact_match(self):
        result = compare_values(100.0, 100.0)
        assert result["status"] == EXACT_MATCH
        assert result["difference_pct"] == 0.0

    def test_within_tolerance(self):
        """Values within 5% should be WITHIN_TOLERANCE."""
        result = compare_values(100.0, 103.0)
        assert result["status"] == WITHIN_TOLERANCE
        assert result["difference_pct"] < 5.0

    def test_material_mismatch(self):
        """Values differing >5% should be MATERIAL_MISMATCH."""
        result = compare_values(100.0, 120.0)
        assert result["status"] == MATERIAL_MISMATCH
        assert result["difference_pct"] > 5.0

    def test_both_none(self):
        result = compare_values(None, None)
        assert result["status"] == NOT_COMPARABLE

    def test_one_none(self):
        result = compare_values(100.0, None)
        assert result["status"] == NOT_COMPARABLE

    def test_one_zero(self):
        result = compare_values(0.0, 100.0)
        assert result["status"] == MATERIAL_MISMATCH

    def test_both_zero(self):
        result = compare_values(0.0, 0.0)
        assert result["status"] == EXACT_MATCH

    def test_small_values(self):
        result = compare_values(0.01, 0.01)
        assert result["status"] == EXACT_MATCH

    def test_large_values(self):
        result = compare_values(1e12, 1e12 * 1.01)
        assert result["status"] == WITHIN_TOLERANCE

    def test_negative_values(self):
        result = compare_values(-100.0, -100.0)
        assert result["status"] == EXACT_MATCH


class TestResolveMetric:
    def test_sec_wins(self):
        result = resolve_metric(100.0, 102.0, metric_name="revenue")
        assert result["resolved_value"] == 100.0
        assert result["source"] == "SEC"
        assert result["classification"] == "reported"
        assert result["cross_check"]["status"] == WITHIN_TOLERANCE

    def test_fmp_enrichment(self):
        result = resolve_metric(None, 100.0, metric_name="market_cap")
        assert result["resolved_value"] == 100.0
        assert result["source"] == "FMP"
        assert result["classification"] == "normalized_external"

    def test_bq_fallback(self):
        result = resolve_metric(None, None, bq_val=100.0, metric_name="some_metric")
        assert result["resolved_value"] == 100.0
        assert result["source"] == "BQ"

    def test_all_none(self):
        result = resolve_metric(None, None, metric_name="missing")
        assert result["resolved_value"] is None
        assert result["source"] is None

    def test_cross_check_with_bq(self):
        result = resolve_metric(100.0, None, bq_val=105.0, metric_name="revenue")
        assert result["resolved_value"] == 100.0
        assert result["cross_check"] is not None
        assert result["cross_check"]["status"] == WITHIN_TOLERANCE


class TestBuildCrossCheckReport:
    def test_report_structure(self):
        metrics = {
            "revenue": {"source": "SEC", "cross_check": {"status": EXACT_MATCH}},
            "market_cap": {"source": "FMP", "cross_check": {"status": WITHIN_TOLERANCE}},
        }
        report = build_cross_check_report(metrics)
        assert report["total_metrics"] == 2
        assert report["exact_matches"] == 1
        assert report["within_tolerance"] == 1

    def test_empty_metrics(self):
        report = build_cross_check_report({})
        assert report["total_metrics"] == 0

    def test_mismatch_counted(self):
        metrics = {
            "revenue": {"source": "SEC", "cross_check": {"status": MATERIAL_MISMATCH}},
        }
        report = build_cross_check_report(metrics)
        assert report["material_mismatches"] == 1
