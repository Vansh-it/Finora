"""Tests for dashboard data builder."""

from __future__ import annotations

import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.dashboard_builder import (
    build_dashboard_payload,
    _fmt_billions,
    _fmt_pct,
    _fmt_ratio,
    _fmt_eps,
    _extract_value,
)


# ── Fixture ──────────────────────────────────────────────────────────────────
def _make_session(
    financial_stmts=None,
    calculated_metrics=None,
    source_registry=None,
    verification_results=None,
    company_meta=None,
    period_mode="latest",
):
    return {
        "session_id": "test123",
        "company": "Microsoft Corporation",
        "period_mode": period_mode,
        "start_year": None,
        "end_year": None,
        "company_meta": company_meta or {"name": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"},
        "financial_statements": financial_stmts or {},
        "calculated_metrics": calculated_metrics or {},
        "source_registry": source_registry or {},
        "verification_results": verification_results or {},
    }


def _sec_statements():
    return {
        "periods": ["FY2025", "FY2026"],
        "income_statement": {
            "revenue": {
                "FY2025": {"value": 250_000_000_000, "period": "FY2025"},
                "FY2026": {"value": 331_839_000_000, "period": "FY2026"},
            },
            "net_income": {
                "FY2025": {"value": 100_000_000_000, "period": "FY2025"},
                "FY2026": {"value": 133_749_000_000, "period": "FY2026"},
            },
            "operating_income": {
                "FY2025": {"value": 120_000_000_000, "period": "FY2025"},
                "FY2026": {"value": 155_237_000_000, "period": "FY2026"},
            },
            "diluted_eps": {
                "FY2025": {"value": 13.50, "period": "FY2025"},
                "FY2026": {"value": 17.95, "period": "FY2026"},
            },
        },
        "balance_sheet": {
            "total_assets": {
                "FY2025": {"value": 600_000_000_000, "period": "FY2025"},
                "FY2026": {"value": 758_376_000_000, "period": "FY2026"},
            },
            "shareholders_equity": {
                "FY2025": {"value": 350_000_000_000, "period": "FY2025"},
                "FY2026": {"value": 442_387_000_000, "period": "FY2026"},
            },
        },
        "cash_flow": {
            "operating_cash_flow": {
                "FY2025": {"value": 150_000_000_000, "period": "FY2025"},
                "FY2026": {"value": 182_935_000_000, "period": "FY2026"},
            },
            "free_cash_flow": {
                "FY2025": {"value": 70_000_000_000, "period": "FY2025"},
                "FY2026": {"value": 66_987_000_000, "period": "FY2026"},
            },
        },
        "additional": {},
    }


def _calc_metrics():
    """Period-first layout matching what financial_calculator.calculate_metrics produces."""
    return {
        "periods": ["FY2025", "FY2026"],
        "annual_metrics": {
            "FY2026": {
                "gross_margin": {"value": 69.2, "period": "FY2026"},
                "operating_margin": {"value": 46.8, "period": "FY2026"},
                "net_margin": {"value": 40.3, "period": "FY2026"},
                "roe": {"value": 30.2, "period": "FY2026"},
                "roic": {"value": 26.6, "period": "FY2026"},
                "current_ratio": {"value": 1.23, "period": "FY2026"},
                "net_debt": {"value": -36_500_000_000, "period": "FY2026"},
                "free_cash_flow": {"value": 66_987_000_000, "period": "FY2026"},
                "ebitda": {"value": 190_000_000_000, "period": "FY2026"},
            },
        },
        "growth_metrics": {},
        "cagr_metrics": {},
        "metadata": {},
    }


# ── Formatting Tests ─────────────────────────────────────────────────────────
class TestFormatting:
    def test_fmt_billions_large(self):
        assert _fmt_billions(331_839_000_000) == "$332B"

    def test_fmt_billions_small(self):
        assert _fmt_billions(5_500_000_000) == "$5.5B"

    def test_fmt_billions_none(self):
        assert _fmt_billions(None) == "\u2014"

    def test_fmt_pct(self):
        assert _fmt_pct(46.8) == "46.8%"

    def test_fmt_pct_none(self):
        assert _fmt_pct(None) == "\u2014"

    def test_fmt_ratio(self):
        assert _fmt_ratio(1.23) == "1.23x"

    def test_fmt_eps(self):
        assert _fmt_eps(17.95) == "$17.95"

    def test_extract_value_dict(self):
        assert _extract_value({"value": 100}) == 100

    def test_extract_value_none(self):
        assert _extract_value(None) is None


# ── Payload Tests ────────────────────────────────────────────────────────────
class TestDashboardPayload:
    def test_basic_payload_structure(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        assert "company" in payload
        assert "kpis" in payload
        assert "income_statement" in payload
        assert "balance_sheet" in payload
        assert "cash_flow" in payload
        assert "growth" in payload
        assert "profitability" in payload
        assert "sources" in payload
        assert "data_quality" in payload
        assert "valuation" in payload

    def test_company_header(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        assert payload["company"]["name"] == "Microsoft Corporation"
        assert payload["company"]["ticker"] == "MSFT"
        assert payload["company"]["logoInitials"] == "MC"

    def test_kpi_count(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        assert len(payload["kpis"]) == 6  # revenue, net income, op income, eps, fcf, gross margin

    def test_kpi_values(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        rev_kpi = next(k for k in payload["kpis"] if k["id"] == "revenue")
        assert "$332B" in rev_kpi["value"]

    def test_income_statement_periods(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        assert len(payload["income_statement"]["columns"]) == 3  # "Line item" + 2 periods
        assert "FY2025" in payload["income_statement"]["columns"]
        assert "FY2026" in payload["income_statement"]["columns"]

    def test_income_statement_rows(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        rows = payload["income_statement"]["rows"]
        labels = [r["label"] for r in rows]
        assert "Revenue" in labels
        assert "Net Income" in labels

    def test_profitability_from_metrics(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        metrics = [p["metric"] for p in payload["profitability"]]
        assert "Gross Margin" in metrics
        assert "Operating Margin" in metrics
        assert "Net Margin" in metrics

    def test_profitability_values(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        gm = next(p for p in payload["profitability"] if p["metric"] == "Gross Margin")
        assert "69.2" in gm["value"]

    def test_period_label_latest(self):
        session = _make_session(_sec_statements(), _calc_metrics(), period_mode="latest")
        payload = build_dashboard_payload(session)

        assert "Latest" in payload["company"]["period"]

    def test_period_label_specified(self):
        session = _make_session(_sec_statements(), _calc_metrics(), period_mode="specified")
        session["start_year"] = 2025
        session["end_year"] = 2026
        payload = build_dashboard_payload(session)

        assert "2025" in payload["company"]["period"]

    def test_sources_from_registry(self):
        registry = {
            "sources": [
                {"source_id": "sec_001", "title": "10-K", "provider": "SEC", "source_type": "10-K", "url": "https://sec.gov", "trust_tier": 1, "authority": "regulatory"},
                {"source_id": "ir_001", "title": "Annual Report", "provider": "Microsoft IR", "source_type": "annual_report", "url": "https://investor.ms.com", "trust_tier": 1, "authority": "company_official"},
            ]
        }
        session = _make_session(_sec_statements(), _calc_metrics(), source_registry=registry)
        payload = build_dashboard_payload(session)

        assert len(payload["sources"]) == 2

    def test_empty_session(self):
        session = _make_session()
        payload = build_dashboard_payload(session)

        assert payload["company"]["name"] == "Microsoft Corporation"
        assert len(payload["kpis"]) == 6
        # Empty session has row labels but no data values
        assert len(payload["income_statement"]["rows"]) == 8  # label names present, values all —

    def test_data_quality(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        dq = payload["data_quality"]
        assert dq["primary_source"] == "SEC XBRL"
        assert dq["metrics_calculated"] >= 0

    def test_dupont_data(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        # DuPont should be None since we don't have dupont metric in fixture
        assert payload["dupont"] is None

    def test_leverage_section(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        # Leverage should have some items from calculated metrics
        assert isinstance(payload["leverage"], list)

    def test_capital_allocation_section(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        assert isinstance(payload["capital_allocation"], list)

    def test_valuation_section(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)

        assert "valuation" in payload
        val = payload["valuation"]
        assert "market_data" in val
        assert "metrics" in val
        assert "period_alignment" in val

    def test_management_commentary(self):
        session = _make_session(_sec_statements(), _calc_metrics())
        payload = build_dashboard_payload(session)
        assert isinstance(payload["management_commentary"], list)
