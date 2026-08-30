"""Tests for financial statement extractor.

All tests use mocked SEC CompanyFacts responses — no live network calls.
"""

import os
import sys
from unittest.mock import patch

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.financial_extractor import (
    extract_financials,
    _is_annual_period,
    _is_quarterly_period,
    _get_fiscal_year,
    _period_label,
)


# ── Mock CompanyFacts data ───────────────────────────────────────────────────
MOCK_MSFT_FACTS = {
    "cik": "0000789019",
    "entityName": "MICROSOFT CORP",
    "facts": {
        "us-gaap": {
            "Revenues": {
                "label": "Revenues",
                "units": {
                    "USD": [
                        {"val": 245122000000, "end": "2025-06-30", "start": "2024-07-01", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 211915000000, "end": "2024-06-30", "start": "2023-07-01", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "RevenueFromContractWithCustomerExcludingAssessedTax": {
                "label": "Revenue",
                "units": {
                    "USD": [
                        {"val": 245122000000, "end": "2025-06-30", "start": "2024-07-01", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                    ]
                },
            },
            "OperatingIncomeLoss": {
                "label": "Operating Income",
                "units": {
                    "USD": [
                        {"val": 109433000000, "end": "2025-06-30", "start": "2024-07-01", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 96638000000, "end": "2024-06-30", "start": "2023-07-01", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "NetIncomeLoss": {
                "label": "Net Income",
                "units": {
                    "USD": [
                        {"val": 88136000000, "end": "2025-06-30", "start": "2024-07-01", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 72361000000, "end": "2024-06-30", "start": "2023-07-01", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "EarningsPerShareDiluted": {
                "label": "Diluted EPS",
                "units": {
                    "USD/shares": [
                        {"val": 11.82, "end": "2025-06-30", "start": "2024-07-01", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 9.68, "end": "2024-06-30", "start": "2023-07-01", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "Assets": {
                "label": "Assets",
                "units": {
                    "USD": [
                        {"val": 414011000000, "end": "2025-06-30", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 364011000000, "end": "2024-06-30", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "Liabilities": {
                "label": "Liabilities",
                "units": {
                    "USD": [
                        {"val": 205567000000, "end": "2025-06-30", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 197733000000, "end": "2024-06-30", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "StockholdersEquity": {
                "label": "Equity",
                "units": {
                    "USD": [
                        {"val": 208444000000, "end": "2025-06-30", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 166278000000, "end": "2024-06-30", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "CashAndCashEquivalentsAtCarryingValue": {
                "label": "Cash",
                "units": {
                    "USD": [
                        {"val": 25854000000, "end": "2025-06-30", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 21272000000, "end": "2024-06-30", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "NetCashProvidedByUsedInOperatingActivities": {
                "label": "Operating Cash Flow",
                "units": {
                    "USD": [
                        {"val": 123360000000, "end": "2025-06-30", "start": "2024-07-01", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 118504000000, "end": "2024-06-30", "start": "2023-07-01", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "PaymentsToAcquirePropertyPlantAndEquipment": {
                "label": "CapEx",
                "units": {
                    "USD": [
                        {"val": -35209000000, "end": "2025-06-30", "start": "2024-07-01", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": -30603000000, "end": "2024-06-30", "start": "2023-07-01", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
            "GrossProfit": {
                "label": "Gross Profit",
                "units": {
                    "USD": [
                        {"val": 171008000000, "end": "2025-06-30", "start": "2024-07-01", "filed": "2025-07-30", "form": "10-K", "accn": "0000950170-25-012345"},
                        {"val": 146054000000, "end": "2024-06-30", "start": "2023-07-01", "filed": "2024-07-30", "form": "10-K", "accn": "0000950170-24-012345"},
                    ]
                },
            },
        }
    },
}

MOCK_EMPTY_FACTS = {
    "cik": "9999999999",
    "entityName": "EMPTY CO",
    "facts": {"us-gaap": {}},
}


# ── Period helper tests ──────────────────────────────────────────────────────
class TestPeriodHelpers:
    def test_annual_period(self):
        assert _is_annual_period({"start": "2024-07-01", "end": "2025-06-30"}) is True

    def test_quarterly_period(self):
        assert _is_quarterly_period({"start": "2025-04-01", "end": "2025-06-30"}) is True

    def test_not_annual_too_short(self):
        assert _is_annual_period({"start": "2025-01-01", "end": "2025-03-31"}) is False

    def test_get_fiscal_year(self):
        assert _get_fiscal_year("2025-06-30") == 2025

    def test_get_fiscal_year_invalid(self):
        assert _get_fiscal_year("not-a-date") is None

    def test_period_label_annual(self):
        assert _period_label("2025-06-30", True) == "FY2025"

    def test_period_label_quarterly(self):
        label = _period_label("2025-06-30", False)
        assert "FY2025" in label


# ── Latest mode extraction (now returns period-keyed dict with top 3 years) ──
class TestLatestExtraction:
    def _get_latest_fact(self, stmt_data, metric):
        """Helper to get the latest period fact from multi-period dict."""
        data = stmt_data.get(metric)
        if data is None:
            return None
        # New format: period-keyed dict
        if isinstance(data, dict) and "period" not in data:
            # Get the latest period
            latest = None
            for period_key, fact in data.items():
                if fact is not None and isinstance(fact, dict):
                    if latest is None or period_key > latest.get("period", ""):
                        latest = fact
            return latest
        # Legacy format: single fact dict
        return data

    def test_msft_revenue(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            rev = self._get_latest_fact(stmts.income_statement, "revenue")
            assert rev is not None
            assert rev["value"] == 245122000000
            assert rev["unit"] == "USD"
            assert rev["xbrl_concept"] in ("RevenueFromContractWithCustomerExcludingAssessedTax", "Revenues")
            assert rev["source"] == "SEC XBRL"
            assert "FY2025" in rev["period"]

    def test_msft_operating_income(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            oi = self._get_latest_fact(stmts.income_statement, "operating_income")
            assert oi is not None
            assert oi["value"] == 109433000000

    def test_msft_net_income(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            ni = self._get_latest_fact(stmts.income_statement, "net_income")
            assert ni is not None
            assert ni["value"] == 88136000000

    def test_msft_eps(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            eps = self._get_latest_fact(stmts.income_statement, "diluted_eps")
            assert eps is not None
            assert eps["value"] == 11.82
            assert eps["unit"] == "USD/shares"

    def test_msft_gross_profit(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            gp = self._get_latest_fact(stmts.income_statement, "gross_profit")
            assert gp is not None
            assert gp["value"] == 171008000000

    def test_msft_total_assets(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            assets = self._get_latest_fact(stmts.balance_sheet, "total_assets")
            assert assets is not None
            assert assets["value"] == 414011000000

    def test_msft_liabilities(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            liab = self._get_latest_fact(stmts.balance_sheet, "total_liabilities")
            assert liab is not None
            assert liab["value"] == 205567000000

    def test_msft_equity(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            eq = self._get_latest_fact(stmts.balance_sheet, "shareholders_equity")
            assert eq is not None
            assert eq["value"] == 208444000000

    def test_msft_cash(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            cash = self._get_latest_fact(stmts.balance_sheet, "cash_and_equivalents")
            assert cash is not None
            assert cash["value"] == 25854000000

    def test_msft_operating_cash_flow(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            ocf = self._get_latest_fact(stmts.cash_flow, "operating_cash_flow")
            assert ocf is not None
            assert ocf["value"] == 123360000000

    def test_msft_capex(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            capex = self._get_latest_fact(stmts.cash_flow, "capital_expenditures")
            assert capex is not None
            assert capex["value"] == -35209000000

    def test_multi_period_format(self):
        """Latest mode now returns period-keyed dict for growth support."""
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            rev = stmts.income_statement.get("revenue")
            assert isinstance(rev, dict)
            assert "FY2025" in rev
            assert "FY2024" in rev
            assert rev["FY2025"]["value"] == 245122000000
            assert rev["FY2024"]["value"] == 211915000000


# ── Specified period extraction ──────────────────────────────────────────────
class TestSpecifiedExtraction:
    def test_multi_year_periods(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials(
                "0000789019", "MICROSOFT CORP", "MSFT",
                "specified", 2024, 2025,
            )
            assert "FY2025" in stmts.periods
            assert "FY2024" in stmts.periods

    def test_multi_year_revenue(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials(
                "0000789019", "MICROSOFT CORP", "MSFT",
                "specified", 2024, 2025,
            )
            rev = stmts.income_statement.get("revenue")
            assert isinstance(rev, dict)
            assert "FY2025" in rev
            assert "FY2024" in rev
            assert rev["FY2025"]["value"] == 245122000000
            assert rev["FY2024"]["value"] == 211915000000

    def test_single_year(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials(
                "0000789019", "MICROSOFT CORP", "MSFT",
                "specified", 2025, 2025,
            )
            assert "FY2025" in stmts.periods
            rev = stmts.income_statement.get("revenue")
            assert "FY2025" in rev
            assert rev["FY2025"]["value"] == 245122000000


# ── Edge cases ────────────────────────────────────────────────────────────────
class TestEdgeCases:
    def test_empty_company_facts(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_EMPTY_FACTS):
            stmts = extract_financials("9999999999", "EMPTY CO", "EMPTY", "latest")
            assert stmts.income_statement.get("revenue") is None
            assert stmts.balance_sheet.get("total_assets") is None

    def test_evidence_metadata(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            rev_data = stmts.income_statement["revenue"]
            # Multi-period format: get the latest period fact
            rev = rev_data.get("FY2025") if isinstance(rev_data, dict) and "period" not in rev_data else rev_data
            assert rev is not None
            assert "accession_number" in rev
            assert "filing_date" in rev
            assert "xbrl_concept" in rev
            assert rev["verification_status"] == "primary_source"

    def test_to_dict(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            d = stmts.to_dict()
            assert "company" in d
            assert "periods" in d
            assert "income_statement" in d
            assert "balance_sheet" in d
            assert "cash_flow" in d
            assert "metadata" in d

    def test_metadata_counts(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            meta = stmts.metadata
            assert meta["metrics_extracted"] > 0
            assert meta["total_metrics_attempted"] > meta["metrics_extracted"]

    def test_none_for_missing_metric(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            div = stmts.cash_flow.get("dividends_paid")
            # Multi-period: returns dict of {period: None} or None
            if div is not None:
                # All values should be None for missing metrics
                assert all(v is None for v in div.values()) if isinstance(div, dict) else div is None
            else:
                assert div is None

    def test_company_metadata(self):
        with patch("lib.financial_extractor.get_company_facts", return_value=MOCK_MSFT_FACTS):
            stmts = extract_financials("0000789019", "MICROSOFT CORP", "MSFT", "latest")
            assert stmts.company["ticker"] == "MSFT"
            assert stmts.company["cik"] == "0000789019"
            assert stmts.company["name"] == "MICROSOFT CORP"
