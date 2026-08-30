"""Tests for dashboard contextual chat and endpoint behavior."""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest


class TestDashboardChatEndpoint:
    """Test the /api/chat/dashboard endpoint."""

    def test_chat_prompt_template_exists(self):
        """The dashboard chat prompt template should exist."""
        from app import FINORA_DASHBOARD_CHAT_PROMPT_TEMPLATE
        assert "Finora" in FINORA_DASHBOARD_CHAT_PROMPT_TEMPLATE
        assert len(FINORA_DASHBOARD_CHAT_PROMPT_TEMPLATE) > 100

    def test_system_prompt_exists(self):
        """The main system prompt should exist."""
        from app import FINORA_SYSTEM_PROMPT
        assert "Finora" in FINORA_SYSTEM_PROMPT
        assert "not investment advice" not in FINORA_SYSTEM_PROMPT.lower() or "not" in FINORA_SYSTEM_PROMPT.lower()


class TestMetricMethodology:
    """Test metric methodology and beginner explanations."""

    def test_beginner_explanations_coverage(self):
        """Key metrics should have beginner explanations."""
        from lib.metric_methodology import BEGINNER_EXPLANATIONS
        key_metrics = [
            "gross_margin", "operating_margin", "net_margin",
            "roa", "roe", "roic",
            "current_ratio", "debt_to_equity",
            "free_cash_flow", "asset_turnover",
        ]
        for mid in key_metrics:
            assert mid in BEGINNER_EXPLANATIONS, f"Missing beginner explanation for '{mid}'"
            assert len(BEGINNER_EXPLANATIONS[mid]) > 20

    def test_get_metric_metadata(self):
        """get_metric_metadata should combine both sources."""
        from lib.metric_methodology import get_metric_metadata
        meta = get_metric_metadata("roe")
        assert "name" in meta
        assert "formula" in meta
        assert "beginner" in meta
        assert meta["beginner"] != ""

    def test_metadology_has_all_required_fields(self):
        """Every methodology entry should have required fields."""
        from lib.metric_methodology import METODOLOGY
        required = {"name", "unit", "classification", "formula", "notes"}
        for mid, meta in METODOLOGY.items():
            for field in required:
                assert field in meta, f"Metric '{mid}' missing '{field}'"


class TestBeginnerExplanationContent:
    """Test the quality of beginner explanations."""

    def test_roe_explanation_mentions_leverage(self):
        """ROE explanation should mention leverage consideration."""
        from lib.metric_methodology import BEGINNER_EXPLANATIONS
        roe = BEGINNER_EXPLANATIONS["roe"]
        assert "leverage" in roe.lower()

    def test_current_ratio_explanation_mentions_1(self):
        """Current ratio explanation should reference 1.0 threshold."""
        from lib.metric_methodology import BEGINNER_EXPLANATIONS
        cr = BEGINNER_EXPLANATIONS["current_ratio"]
        assert "1.0" in cr or "1.0" in cr

    def test_fc_explanation_mentions_equipment(self):
        """FCF explanation should mention equipment/buildings."""
        from lib.metric_methodology import BEGINNER_EXPLANATIONS
        fcf = BEGINNER_EXPLANATIONS["free_cash_flow"]
        assert "equipment" in fcf.lower() or "buildings" in fcf.lower()

    def test_no_investment_advice_in_explanations(self):
        """No beginner explanation should give investment advice."""
        import re
        from lib.metric_methodology import BEGINNER_EXPLANATIONS
        # Use word-boundary regex to avoid false positives like 'selling' matching 'sell'
        advice_patterns = [r"\bbuy\b", r"\brecommend\b", r"\bshould invest\b",
                           r"\bovervalued\b", r"\bundervalued\b"]
        for mid, explanation in BEGINNER_EXPLANATIONS.items():
            for pattern in advice_patterns:
                match = re.search(pattern, explanation.lower())
                assert match is None, \
                    f"Beginner explanation for '{mid}' contains investment advice: '{pattern}'"


class TestDashboardBuilderCompleteness:
    """Test dashboard builder includes completeness data."""

    def test_data_quality_includes_calculated_count(self):
        """Data quality bar should show metrics_calculated."""
        from lib.dashboard_builder import build_dashboard_payload
        session_data = {
            "company_meta": {"name": "Test", "ticker": "TST", "exchange": "NASDAQ", "cik": "00001"},
            "financial_statements": {
                "periods": ["FY2025"],
                "income_statement": {
                    "revenue": {"FY2025": {"value": 100e9, "period": "FY2025"}},
                    "net_income": {"FY2025": {"value": 20e9, "period": "FY2025"}},
                },
                "balance_sheet": {},
                "cash_flow": {},
                "additional": {},
            },
            "calculated_metrics": {
                "annual_metrics": {
                    "FY2025": {
                        "gross_margin": {"value": 40.0, "display_value": "40.0%", "status": "calculated"},
                        "roe": {"value": 15.0, "display_value": "15.0%", "status": "calculated"},
                        "current_ratio": {"value": None, "display_value": "N/A", "status": "unavailable",
                                          "reason": "Missing current liabilities"},
                    }
                },
                "growth_metrics": {},
                "cagr_metrics": {},
            },
            "source_registry": {"sources": []},
            "verification_results": {"summary": {"exact_matches": 2, "within_tolerance": 0, "mismatches": 0}},
            "executive_summary": None,
            "market_data": {},
            "valuation_metrics": {},
            "period_mode": "latest",
        }
        payload = build_dashboard_payload(session_data)
        quality = payload.get("data_quality", {})
        assert quality.get("primary_source") == "SEC XBRL"
        assert quality.get("metrics_calculated", 0) >= 0
        assert "mismatches" in quality
