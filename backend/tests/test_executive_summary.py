"""Tests for executive summary generation service."""

from __future__ import annotations

import json
import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.executive_summary import (
    _build_analysis_context,
    _parse_json,
    _validate_summary,
    _build_data_quality_note,
    generate_executive_summary,
)


# ── Fixture ──────────────────────────────────────────────────────────────────
def _make_session(
    financial_stmts=None,
    calculated_metrics=None,
    verification_results=None,
    source_registry=None,
):
    return {
        "session_id": "test123",
        "company": "Microsoft Corporation",
        "period_mode": "latest",
        "start_year": None,
        "end_year": None,
        "company_meta": {"name": "Microsoft Corporation", "ticker": "MSFT"},
        "financial_statements": financial_stmts or {
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
            },
            "cash_flow": {
                "operating_cash_flow": {"value": 182_935_000_000, "period": "FY2026"},
            },
            "additional": {},
        },
        "calculated_metrics": calculated_metrics or {
            "periods": ["FY2026"],
            "annual_metrics": {
                "FY2026": {
                    "gross_margin": {"value": 67.9, "period": "FY2026"},
                    "operating_margin": {"value": 46.8, "period": "FY2026"},
                    "net_margin": {"value": 40.3, "period": "FY2026"},
                    "roe": {"value": 30.2, "period": "FY2026"},
                    "roic": {"value": 27.1, "period": "FY2026"},
                    "current_ratio": {"value": 1.23, "period": "FY2026"},
                    "free_cash_flow": {"value": 67_000_000_000, "period": "FY2026"},
                },
            },
            "growth_metrics": {},
            "cagr_metrics": {},
            "metadata": {},
        },
        "source_registry": source_registry or {},
        "verification_results": verification_results or {},
    }


# ── JSON Parsing Tests ───────────────────────────────────────────────────────
class TestJsonParsing:
    def test_parse_valid_json(self):
        text = '{"key": "value"}'
        result = _parse_json(text)
        assert result == {"key": "value"}

    def test_parse_code_block(self):
        text = '```json\n{"key": "value"}\n```'
        result = _parse_json(text)
        assert result == {"key": "value"}

    def test_parse_with_surrounding_text(self):
        text = 'Here is the result:\n{"key": "value"}\nDone.'
        result = _parse_json(text)
        assert result == {"key": "value"}

    def test_parse_empty(self):
        assert _parse_json("") is None
        assert _parse_json("no json") is None

    def test_parse_invalid_json(self):
        assert _parse_json("{invalid") is None


# ── Context Builder Tests ────────────────────────────────────────────────────
class TestContextBuilder:
    def test_builds_context(self):
        session = _make_session()
        ctx = _build_analysis_context(session)

        assert ctx["company"]["name"] == "Microsoft Corporation"
        assert ctx["company"]["ticker"] == "MSFT"
        assert ctx["period"]["latest_period"] == "FY2026"
        assert "revenue" in ctx["financial_snapshot"]
        assert ctx["financial_snapshot"]["revenue"] == 331_839_000_000

    def test_includes_ratios(self):
        session = _make_session()
        ctx = _build_analysis_context(session)

        assert "gross_margin" in ctx["ratios"]
        assert ctx["ratios"]["gross_margin"] == 67.9

    def test_includes_commentary(self):
        verification = {
            "management_commentary": [
                {"topic": "revenue_drivers", "summary": "Cloud grew 22%.", "sentiment": "positive", "importance": "high"},
            ],
        }
        session = _make_session(verification_results=verification)
        ctx = _build_analysis_context(session)

        assert len(ctx["management_commentary"]) == 1

    def test_includes_verification(self):
        verification = {
            "summary": {"exact_matches": 5, "within_tolerance": 0, "mismatches": 0},
        }
        session = _make_session(verification_results=verification)
        ctx = _build_analysis_context(session)

        assert ctx["verification"]["cross_verified"] == 5
        assert ctx["verification"]["mismatches"] == 0


# ── Data Quality Note Tests ──────────────────────────────────────────────────
class TestDataQualityNote:
    def test_basic_note(self):
        ctx = {"verification": {"cross_verified": 5, "mismatches": 0, "source_count": 3}}
        note = _build_data_quality_note(ctx)
        assert "SEC XBRL" in note
        assert "5 metrics" in note
        assert "3 authoritative sources" in note
        assert "No material mismatches" in note

    def test_with_mismatches(self):
        ctx = {"verification": {"cross_verified": 2, "mismatches": 1, "source_count": 1}}
        note = _build_data_quality_note(ctx)
        assert "1 material mismatch" in note
        assert "SEC value retained" in note

    def test_no_verification(self):
        ctx = {"verification": {"cross_verified": 0, "mismatches": 0, "source_count": 0}}
        note = _build_data_quality_note(ctx)
        assert "SEC XBRL" in note


# ── Validation Tests ─────────────────────────────────────────────────────────
class TestValidation:
    def test_valid_summary_passes(self):
        summary = {
            "executive_overview": "Test overview.",
            "highlights": [{"title": "Revenue", "text": "Grew 16%.", "importance": "high"}],
            "growth_analysis": "Growth was strong.",
            "profitability_analysis": "Margins expanded.",
            "cash_flow_analysis": "FCF was strong.",
            "balance_sheet_analysis": "Healthy balance sheet.",
            "watch_items": [{"title": "CapEx", "reason": "Increasing.", "severity": "low"}],
            "management_commentary_summary": "",
            "data_quality_note": "SEC XBRL primary.",
        }
        result = _validate_summary(summary, {})
        assert result["executive_overview"] == "Test overview."
        assert len(result["highlights"]) == 1

    def test_missing_fields_get_defaults(self):
        summary = {"executive_overview": "Test"}
        result = _validate_summary(summary, {})
        assert result["highlights"] == []
        assert result["watch_items"] == []
        assert result["growth_analysis"] == ""

    def test_invalid_highlights_filtered(self):
        summary = {
            "executive_overview": "Test",
            "highlights": [{"bad": "data"}, {"title": "OK", "text": "Good", "importance": "high"}],
            "watch_items": [],
        }
        result = _validate_summary(summary, {})
        assert len(result["highlights"]) == 1

    def test_string_fields_coerced(self):
        summary = {
            "executive_overview": 123,
            "highlights": [],
            "watch_items": [],
        }
        result = _validate_summary(summary, {})
        assert isinstance(result["executive_overview"], str)


# ── Generation Tests ─────────────────────────────────────────────────────────
class TestGeneration:
    @patch("lib.executive_summary.generate_text")
    def test_successful_generation(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "executive_overview": "Microsoft delivered strong results with $331.8B revenue.",
            "highlights": [{"title": "Revenue Growth", "text": "Revenue grew strongly.", "importance": "high"}],
            "growth_analysis": "Revenue growth remained robust.",
            "profitability_analysis": "Operating margin was 46.8%.",
            "cash_flow_analysis": "Free cash flow was $67.0B.",
            "balance_sheet_analysis": "Balance sheet remains healthy.",
            "watch_items": [{"title": "CapEx", "reason": "Elevated spending.", "severity": "low"}],
            "management_commentary_summary": "",
            "data_quality_note": "SEC XBRL primary.",
        })

        session = _make_session()
        result = generate_executive_summary(session)

        assert "executive_overview" in result
        assert "$331.8B" in result["executive_overview"] or "331" in result["executive_overview"]
        assert len(result["highlights"]) == 1
        assert result["_metadata"]["company"]["name"] == "Microsoft Corporation"

    @patch("lib.executive_summary.generate_text")
    def test_malformed_json_retries(self, mock_llm):
        mock_llm.return_value = "This is not JSON at all"

        session = _make_session()
        with pytest.raises(RuntimeError, match="invalid JSON"):
            generate_executive_summary(session)

    @patch("lib.executive_summary.generate_text")
    def test_llm_failure(self, mock_llm):
        mock_llm.side_effect = RuntimeError("LLM timeout")

        session = _make_session()
        with pytest.raises(RuntimeError, match="LLM generation failed"):
            generate_executive_summary(session)

    @patch("lib.executive_summary.generate_text")
    def test_data_quality_note_overridden(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "executive_overview": "Test.",
            "highlights": [],
            "growth_analysis": "",
            "profitability_analysis": "",
            "cash_flow_analysis": "",
            "balance_sheet_analysis": "",
            "watch_items": [],
            "management_commentary_summary": "",
            "data_quality_note": "This should be overridden.",
        })

        session = _make_session(verification_results={"summary": {"exact_matches": 3, "within_tolerance": 0, "mismatches": 0}})
        result = generate_executive_summary(session)

        assert "This should be overridden" not in result["data_quality_note"]
        assert "SEC XBRL" in result["data_quality_note"]

    @patch("lib.executive_summary.generate_text")
    def test_metadata_included(self, mock_llm):
        mock_llm.return_value = json.dumps({
            "executive_overview": "Test.",
            "highlights": [],
            "growth_analysis": "",
            "profitability_analysis": "",
            "cash_flow_analysis": "",
            "balance_sheet_analysis": "",
            "watch_items": [],
            "management_commentary_summary": "",
            "data_quality_note": "",
        })

        session = _make_session()
        result = generate_executive_summary(session)

        assert "_metadata" in result
        assert result["_metadata"]["company"]["ticker"] == "MSFT"
        assert result["_metadata"]["period"]["latest_period"] == "FY2026"
