"""Tests for XBRL concept mapper."""

import os
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.xbrl_mapper import (
    INCOME_STATEMENT_CONCEPTS,
    BALANCE_SHEET_CONCEPTS,
    CASH_FLOW_CONCEPTS,
    ADDITIONAL_CONCEPTS,
    get_concepts_for_metric,
    get_all_xbrl_concepts,
    get_metric_unit,
    get_income_statement_metrics,
    get_balance_sheet_metrics,
    get_cash_flow_metrics,
    get_additional_metrics,
)


class TestConceptAliases:
    def test_revenue_has_aliases(self):
        aliases = get_concepts_for_metric("revenue")
        assert "Revenues" in aliases
        assert "RevenueFromContractWithCustomerExcludingAssessedTax" in aliases

    def test_operating_income_has_aliases(self):
        aliases = get_concepts_for_metric("operating_income")
        assert "OperatingIncomeLoss" in aliases

    def test_net_income_has_aliases(self):
        aliases = get_concepts_for_metric("net_income")
        assert "NetIncomeLoss" in aliases

    def test_cash_and_equivalents(self):
        aliases = get_concepts_for_metric("cash_and_equivalents")
        assert "CashAndCashEquivalentsAtCarryingValue" in aliases

    def test_total_assets(self):
        aliases = get_concepts_for_metric("total_assets")
        assert "Assets" in aliases

    def test_operating_cash_flow(self):
        aliases = get_concepts_for_metric("operating_cash_flow")
        assert "NetCashProvidedByUsedInOperatingActivities" in aliases

    def test_diluted_eps(self):
        aliases = get_concepts_for_metric("diluted_eps")
        assert "EarningsPerShareDiluted" in aliases

    def test_unknown_metric_returns_empty(self):
        aliases = get_concepts_for_metric("nonexistent_metric")
        assert aliases == []


class TestAllConcepts:
    def test_get_all_xbrl_concepts(self):
        all_concepts = get_all_xbrl_concepts()
        assert "Revenues" in all_concepts
        assert "Assets" in all_concepts
        assert "NetIncomeLoss" in all_concepts
        assert len(all_concepts) > 40  # should have many concepts


class TestMetricUnits:
    def test_revenue_is_usd(self):
        assert get_metric_unit("revenue") == "USD"

    def test_diluted_eps_is_per_share(self):
        assert get_metric_unit("diluted_eps") == "USD/shares"

    def test_shares_outstanding(self):
        assert get_metric_unit("shares_outstanding") == "shares"

    def test_cash_flow_is_usd(self):
        assert get_metric_unit("operating_cash_flow") == "USD"


class TestMetricLists:
    def test_income_statement_metrics(self):
        metrics = get_income_statement_metrics()
        assert "revenue" in metrics
        assert "net_income" in metrics
        assert "gross_profit" in metrics

    def test_balance_sheet_metrics(self):
        metrics = get_balance_sheet_metrics()
        assert "total_assets" in metrics
        assert "shareholders_equity" in metrics

    def test_cash_flow_metrics(self):
        metrics = get_cash_flow_metrics()
        assert "operating_cash_flow" in metrics
        assert "capital_expenditures" in metrics

    def test_additional_metrics(self):
        metrics = get_additional_metrics()
        assert "shares_outstanding" in metrics
