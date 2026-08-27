"""Tests for filing retriever."""

import json
import os
from unittest.mock import patch, MagicMock

import pytest
import sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.filing_retriever import (
    retrieve_filings,
    _select_latest,
    _select_specified,
    _parse_date,
    _extract_report_year,
)


# ── Mock SEC submissions data for Microsoft ───────────────────────────────────
MOCK_MSFT_SUBMISSIONS = {
    "filings": {
        "recent": {
            "form": [
                "10-K", "10-Q", "10-Q", "10-Q",
                "10-K", "10-Q", "10-Q", "10-Q",
                "10-K", "10-Q", "10-Q", "10-Q",
            ],
            "filingDate": [
                "2025-07-30", "2025-04-29", "2025-01-29", "2024-10-29",
                "2024-07-30", "2024-04-29", "2024-01-29", "2023-10-29",
                "2023-07-28", "2023-04-29", "2023-01-29", "2022-10-29",
            ],
            "accessionNumber": [
                "0000950170-25-012345", "0000950170-25-012346", "0000950170-25-012347", "0000950170-24-012348",
                "0000950170-24-012349", "0000950170-24-012350", "0000950170-24-012351", "0000950170-23-012352",
                "0000950170-23-012353", "0000950170-23-012354", "0000950170-23-012355", "0000950170-22-012356",
            ],
            "primaryDocument": [
                "msft-20250630.htm", "msft-20250331.htm", "msft-20241231.htm", "msft-20240930.htm",
                "msft-20240630.htm", "msft-20240331.htm", "msft-20231231.htm", "msft-20230930.htm",
                "msft-20230630.htm", "msft-20230331.htm", "msft-20221231.htm", "msft-20220930.htm",
            ],
            "reportPeriodOfCurrentDocument": [
                "2025-06-30", "2025-03-31", "2024-12-31", "2024-09-30",
                "2024-06-30", "2024-03-31", "2023-12-31", "2023-09-30",
                "2023-06-30", "2023-03-31", "2022-12-31", "2022-09-30",
            ],
        }
    }
}


def _mock_submissions_response(data=None):
    """Create a mock urllib response for submissions."""
    mock_response = MagicMock()
    mock_response.read.return_value = json.dumps(data or MOCK_MSFT_SUBMISSIONS).encode()
    mock_response.__enter__ = MagicMock(return_value=mock_response)
    mock_response.__exit__ = MagicMock(return_value=False)
    return mock_response


# ── Helper tests ──────────────────────────────────────────────────────────────
class TestHelpers:
    def test_parse_date_standard(self):
        dt = _parse_date("2024-07-30")
        assert dt is not None
        assert dt.year == 2024
        assert dt.month == 7
        assert dt.day == 30

    def test_parse_date_compact(self):
        dt = _parse_date("20240730")
        assert dt is not None
        assert dt.year == 2024

    def test_parse_date_invalid(self):
        dt = _parse_date("not-a-date")
        assert dt is None

    def test_extract_report_year(self):
        filing = {"reportPeriodOfCurrentDocument": "2024-06-30"}
        assert _extract_report_year(filing) == 2024

    def test_extract_report_year_fallback_to_filing_date(self):
        filing = {"filingDate": "2024-07-30"}
        assert _extract_report_year(filing) == 2024


# ── Latest mode tests ─────────────────────────────────────────────────────────
class TestLatestMode:
    def test_latest_selects_most_recent_10k(self):
        filings = [
            {"form": "10-K", "filing_date": "2024-07-30", "reportPeriodOfCurrentDocument": "2024-06-30"},
            {"form": "10-K", "filing_date": "2023-07-28", "reportPeriodOfCurrentDocument": "2023-06-30"},
        ]
        result = _select_latest(filings)
        assert len(result) == 1
        assert result[0]["filing_date"] == "2024-07-30"

    def test_latest_selects_10k_and_newer_10q(self):
        filings = [
            {"form": "10-K", "filing_date": "2024-07-30", "reportPeriodOfCurrentDocument": "2024-06-30"},
            {"form": "10-Q", "filing_date": "2025-01-29", "reportPeriodOfCurrentDocument": "2024-12-31"},
            {"form": "10-Q", "filing_date": "2024-10-29", "reportPeriodOfCurrentDocument": "2024-09-30"},
        ]
        result = _select_latest(filings)
        assert len(result) == 2
        assert result[0]["form"] == "10-K"
        assert result[1]["form"] == "10-Q"
        assert result[1]["filing_date"] == "2025-01-29"

    def test_latest_skips_older_10q(self):
        filings = [
            {"form": "10-K", "filing_date": "2024-07-30", "reportPeriodOfCurrentDocument": "2024-06-30"},
            {"form": "10-Q", "filing_date": "2024-04-29", "reportPeriodOfCurrentDocument": "2024-03-31"},
        ]
        result = _select_latest(filings)
        assert len(result) == 1
        assert result[0]["form"] == "10-K"

    def test_latest_only_10k_no_10q(self):
        filings = [
            {"form": "10-K", "filing_date": "2024-07-30", "reportPeriodOfCurrentDocument": "2024-06-30"},
        ]
        result = _select_latest(filings)
        assert len(result) == 1


# ── Specified mode tests ──────────────────────────────────────────────────────
class TestSpecifiedMode:
    def test_single_fiscal_year(self):
        filings = [
            {"form": "10-K", "filing_date": "2024-07-30", "reportPeriodOfCurrentDocument": "2024-06-30"},
            {"form": "10-Q", "filing_date": "2024-04-29", "reportPeriodOfCurrentDocument": "2024-03-31"},
            {"form": "10-Q", "filing_date": "2024-01-29", "reportPeriodOfCurrentDocument": "2023-12-31"},
            {"form": "10-K", "filing_date": "2023-07-28", "reportPeriodOfCurrentDocument": "2023-06-30"},
        ]
        result = _select_specified(filings, 2024, 2024)
        # Should include 10-K for FY2024 (report period 2024) and 10-Qs in range
        assert len(result) >= 1
        forms = [f["form"] for f in result]
        assert "10-K" in forms

    def test_multi_year_range(self):
        filings = [
            {"form": "10-K", "filing_date": "2025-07-30", "reportPeriodOfCurrentDocument": "2025-06-30"},
            {"form": "10-K", "filing_date": "2024-07-30", "reportPeriodOfCurrentDocument": "2024-06-30"},
            {"form": "10-K", "filing_date": "2023-07-28", "reportPeriodOfCurrentDocument": "2023-06-30"},
            {"form": "10-K", "filing_date": "2022-07-29", "reportPeriodOfCurrentDocument": "2022-06-30"},
        ]
        result = _select_specified(filings, 2023, 2025)
        assert len(result) == 3
        years = sorted([f.get("reportPeriodOfCurrentDocument", "")[:4] for f in result])
        assert "2023" in years
        assert "2024" in years
        assert "2025" in years

    def test_no_filings_in_range(self):
        filings = [
            {"form": "10-K", "filing_date": "2020-07-30", "reportPeriodOfCurrentDocument": "2020-06-30"},
        ]
        result = _select_specified(filings, 2023, 2025)
        assert len(result) == 0


# ── Full retrieval integration tests ──────────────────────────────────────────
class TestRetrieveFilings:
    def test_latest_msft(self):
        with patch("lib.filing_retriever.get_company_submissions", return_value=MOCK_MSFT_SUBMISSIONS):
            registry = retrieve_filings(
                cik="0000789019",
                company_name="Microsoft Corporation",
                ticker="MSFT",
                period_mode="latest",
            )
            assert registry.company["name"] == "Microsoft Corporation"
            assert registry.company["ticker"] == "MSFT"
            assert registry.company["cik"] == "0000789019"
            assert registry.period["mode"] == "latest"
            assert len(registry.documents) >= 1
            assert registry.documents[0].form == "10-K"
            assert registry.documents[0].source == "SEC EDGAR"

    def test_specified_fy2024(self):
        with patch("lib.filing_retriever.get_company_submissions", return_value=MOCK_MSFT_SUBMISSIONS):
            registry = retrieve_filings(
                cik="0000789019",
                company_name="Microsoft Corporation",
                ticker="MSFT",
                period_mode="specified",
                start_year=2024,
                end_year=2024,
            )
            assert registry.period["start_year"] == 2024
            assert registry.period["end_year"] == 2024
            assert len(registry.documents) >= 1

    def test_specified_multi_year(self):
        with patch("lib.filing_retriever.get_company_submissions", return_value=MOCK_MSFT_SUBMISSIONS):
            registry = retrieve_filings(
                cik="0000789019",
                company_name="Microsoft Corporation",
                ticker="MSFT",
                period_mode="specified",
                start_year=2023,
                end_year=2025,
            )
            assert registry.period["start_year"] == 2023
            assert registry.period["end_year"] == 2025
            assert len(registry.documents) >= 2

    def test_no_filings_raises(self):
        empty_data = {"filings": {"recent": {"form": [], "filingDate": [], "accessionNumber": [], "primaryDocument": [], "reportPeriodOfCurrentDocument": []}}}
        with patch("lib.filing_retriever.get_company_submissions", return_value=empty_data):
            with pytest.raises(ValueError, match="No 10-K or 10-Q"):
                retrieve_filings(
                    cik="9999999999",
                    company_name="No Company",
                    ticker="NONE",
                    period_mode="latest",
                )

    def test_document_registry_to_dict(self):
        with patch("lib.filing_retriever.get_company_submissions", return_value=MOCK_MSFT_SUBMISSIONS):
            registry = retrieve_filings(
                cik="0000789019",
                company_name="Microsoft Corporation",
                ticker="MSFT",
                period_mode="latest",
            )
            d = registry.to_dict()
            assert "company" in d
            assert "period" in d
            assert "documents" in d
            assert d["company"]["ticker"] == "MSFT"
            assert isinstance(d["documents"], list)

    def test_document_has_source_url(self):
        with patch("lib.filing_retriever.get_company_submissions", return_value=MOCK_MSFT_SUBMISSIONS):
            registry = retrieve_filings(
                cik="0000789019",
                company_name="Microsoft Corporation",
                ticker="MSFT",
                period_mode="latest",
            )
            assert registry.documents[0].source_url.startswith("https://www.sec.gov/Archives/edgar/data/")

    def test_document_has_accession_number(self):
        with patch("lib.filing_retriever.get_company_submissions", return_value=MOCK_MSFT_SUBMISSIONS):
            registry = retrieve_filings(
                cik="0000789019",
                company_name="Microsoft Corporation",
                ticker="MSFT",
                period_mode="latest",
            )
            assert registry.documents[0].accession_number != ""
