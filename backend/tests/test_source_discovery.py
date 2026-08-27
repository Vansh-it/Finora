"""Tests for source discovery service."""

from __future__ import annotations

import os
import sys
from unittest.mock import patch, MagicMock

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.source_discovery import (
    discover_sources,
    _get_domain,
    _is_excluded_domain,
    _is_excluded_url,
    _determine_trust_tier,
    _classify_source_type,
    _normalize_url,
    _url_fingerprint,
    _build_search_queries,
    _infer_provider,
    TRUST_TIER_1,
    TRUST_TIER_2,
    TRUST_TIER_3,
    TRUST_TIER_EXCLUDE,
)


# ── Helper: Mock Tavily response ─────────────────────────────────────────────
def _mock_tavily_result(title, url, score=0.9):
    return {"title": title, "url": url, "content": "...", "score": score}


def _mock_tavily_search(results):
    """Return a function that mocks tavily_search."""
    def mock_search(query, **kwargs):
        return {"results": results, "query": query}
    return mock_search


def _mock_sec_registry():
    """Return a minimal SEC document registry."""
    return {
        "documents": [
            {
                "document_id": "sec_001",
                "form": "10-K",
                "filing_date": "2025-07-29",
                "accession_number": "0000950170-25-000001",
                "source_url": "https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20250630.htm",
            }
        ]
    }


# ── Domain Analysis Tests ───────────────────────────────────────────────────
class TestDomainAnalysis:
    def test_get_domain_basic(self):
        assert _get_domain("https://www.microsoft.com/investor") == "microsoft.com"

    def test_get_domain_no_www(self):
        assert _get_domain("https://sec.gov/Archives/test") == "sec.gov"

    def test_excluded_linkedin(self):
        assert _is_excluded_domain("linkedin.com") is True

    def test_excluded_reddit(self):
        assert _is_excluded_domain("reddit.com") is True

    def test_excluded_medium(self):
        assert _is_excluded_domain("medium.com") is True

    def test_excluded_subdomain(self):
        assert _is_excluded_domain("blog.medium.com") is True

    def test_not_excluded_microsoft(self):
        assert _is_excluded_domain("microsoft.com") is False

    def test_not_excluded_sec(self):
        assert _is_excluded_domain("sec.gov") is False

    def test_excluded_url_linkedin_post(self):
        assert _is_excluded_url("https://linkedin.com/posts/user-123") is True

    def test_excluded_url_reddit_post(self):
        assert _is_excluded_url("https://reddit.com/r/wallstreetbets") is True

    def test_not_excluded_investor_page(self):
        assert _is_excluded_url("https://investor.microsoft.com") is False


# ── Trust Tier Tests ─────────────────────────────────────────────────────────
class TestTrustTier:
    def test_sec_is_tier1(self):
        tier = _determine_trust_tier("sec.gov", "https://sec.gov/test", "Test", "Microsoft")
        assert tier == TRUST_TIER_1

    def test_official_ir_is_tier1(self):
        tier = _determine_trust_tier(
            "microsoft.com",
            "https://investor.microsoft.com",
            "Investor Relations",
            "Microsoft Corporation",
        )
        assert tier == TRUST_TIER_1

    def test_linkedin_is_excluded(self):
        tier = _determine_trust_tier("linkedin.com", "https://linkedin.com/posts/123", "Post", "Microsoft")
        assert tier == TRUST_TIER_EXCLUDE

    def test_reddit_is_excluded(self):
        tier = _determine_trust_tier("reddit.com", "https://reddit.com/r/stocks", "Post", "Microsoft")
        assert tier == TRUST_TIER_EXCLUDE

    def test_medium_is_excluded(self):
        tier = _determine_trust_tier("medium.com", "https://medium.com/@user", "Post", "Microsoft")
        assert tier == TRUST_TIER_EXCLUDE

    def test_macrotrends_is_tier2(self):
        tier = _determine_trust_tier(
            "macrotrends.net",
            "https://macrotrends.net/stocks/charts/MSFT",
            "MSFT Revenue",
            "Microsoft",
        )
        assert tier == TRUST_TIER_2

    def test_unknown_site_is_tier3(self):
        tier = _determine_trust_tier(
            "random-blog.com",
            "https://random-blog.com/article",
            "My thoughts on MSFT",
            "Microsoft",
        )
        assert tier == TRUST_TIER_3

    def test_url_pattern_investor_rel(self):
        tier = _determine_trust_tier(
            "apple.com",
            "https://www.apple.com/investor-relations/",
            "Investor Relations",
            "Apple Inc.",
        )
        assert tier == TRUST_TIER_1


# ── Source Type Classification Tests ─────────────────────────────────────────
class TestSourceTypeClassification:
    def test_annual_report(self):
        assert _classify_source_type("2025 Annual Report", "https://example.com") == "annual_report"

    def test_quarterly_earnings(self):
        assert _classify_source_type("Q3 2025 Earnings Release", "https://example.com") == "quarterly_earnings"

    def test_investor_presentation(self):
        assert _classify_source_type("Investor Day Presentation", "https://example.com") == "investor_presentation"

    def test_press_release(self):
        assert _classify_source_type("Press Release: Q4 Results", "https://example.com") == "press_release"

    def test_financial_statements(self):
        assert _classify_source_type("Balance Sheet Data", "https://example.com") == "financial_statements"

    def test_general_financial(self):
        assert _classify_source_type("Microsoft Overview", "https://example.com") == "general_financial"


# ── URL Normalization Tests ──────────────────────────────────────────────────
class TestUrlNormalization:
    def test_normalize_trailing_slash(self):
        assert _normalize_url("https://example.com/path/").endswith("/path")

    def test_normalize_tracking_params(self):
        result = _normalize_url("https://example.com/page?utm_source=google&id=123")
        assert "utm_source" not in result
        assert "id=123" in result

    def test_fingerprint_strips_www(self):
        fp1 = _url_fingerprint("https://www.example.com/path")
        fp2 = _url_fingerprint("https://example.com/path")
        assert fp1 == fp2


# ── Query Generation Tests ───────────────────────────────────────────────────
class TestQueryGeneration:
    def test_latest_queries(self):
        queries = _build_search_queries("Microsoft Corporation", "MSFT", "latest", None, None)
        assert len(queries) == 2
        assert any("annual report" in q.lower() for q in queries)
        assert any("quarterly" in q.lower() for q in queries)

    def test_specified_queries(self):
        queries = _build_search_queries("Microsoft Corporation", "MSFT", "specified", 2023, 2025)
        assert len(queries) == 2
        assert any("2023" in q for q in queries)
        assert any("2025" in q for q in queries)

    def test_single_year_queries(self):
        queries = _build_search_queries("Apple Inc.", "AAPL", "specified", 2025, 2025)
        assert any("2025" in q for q in queries)


# ── Provider Inference Tests ─────────────────────────────────────────────────
class TestProviderInference:
    def test_sec_provider(self):
        assert _infer_provider("sec.gov", "Test") == "SEC EDGAR"

    def test_company_provider(self):
        provider = _infer_provider("microsoft.com", "Test")
        assert "Microsoft" in provider


# ── Main Discovery Tests ─────────────────────────────────────────────────────
class TestDiscoverSources:
    @patch("lib.source_discovery.tavily_search")
    def test_discovery_with_sec_and_tavily(self, mock_tavily):
        """Should combine SEC and Tavily sources."""
        mock_tavily.return_value = {
            "results": [
                _mock_tavily_result(
                    "Microsoft 2025 Annual Report",
                    "https://www.microsoft.com/investor/reports/ar25/index.html",
                ),
                _mock_tavily_result(
                    "MSFT Stock Analysis",
                    "https://www.linkedin.com/posts/user-123",
                ),
            ],
            "query": "test",
        }

        result = discover_sources(
            company_name="Microsoft Corporation",
            ticker="MSFT",
            period_mode="latest",
            sec_registry=_mock_sec_registry(),
        )

        assert "sources" in result
        assert result["company"]["name"] == "Microsoft Corporation"
        assert result["company"]["ticker"] == "MSFT"

        # Should have SEC source + accepted Tavily source (LinkedIn excluded)
        sec_sources = [s for s in result["sources"] if s["authority"] == "regulatory"]
        company_sources = [s for s in result["sources"] if s["authority"] == "company_official"]
        assert len(sec_sources) >= 1
        # LinkedIn should be excluded
        all_urls = [s["url"] for s in result["sources"]]
        assert not any("linkedin.com" in u for u in all_urls)

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_filters_reddit(self, mock_tavily):
        """Reddit results should be excluded."""
        mock_tavily.return_value = {
            "results": [
                _mock_tavily_result(
                    "What do you think about MSFT?",
                    "https://reddit.com/r/wallstreetbets/thread123",
                ),
            ],
            "query": "test",
        }

        result = discover_sources(
            company_name="Microsoft Corporation",
            ticker="MSFT",
            period_mode="latest",
            sec_registry=_mock_sec_registry(),
        )

        all_urls = [s["url"] for s in result["sources"]]
        assert not any("reddit.com" in u for u in all_urls)

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_filters_blogs(self, mock_tavily):
        """Blog/SEO results should be excluded."""
        mock_tavily.return_value = {
            "results": [
                _mock_tavily_result(
                    "My MSFT investment thesis",
                    "https://random-blog.com/msft-analysis",
                ),
            ],
            "query": "test",
        }

        result = discover_sources(
            company_name="Microsoft Corporation",
            ticker="MSFT",
            period_mode="latest",
            sec_registry=_mock_sec_registry(),
        )

        # Only SEC source should remain
        all_urls = [s["url"] for s in result["sources"]]
        assert not any("random-blog.com" in u for u in all_urls)

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_deduplication(self, mock_tavily):
        """SEC and Tavily should not duplicate the same URL."""
        mock_tavily.return_value = {
            "results": [
                _mock_tavily_result(
                    "SEC Filing",
                    "https://www.sec.gov/Archives/edgar/data/789019/000119312526323660/msft-20250630.htm",
                ),
            ],
            "query": "test",
        }

        result = discover_sources(
            company_name="Microsoft Corporation",
            ticker="MSFT",
            period_mode="latest",
            sec_registry=_mock_sec_registry(),
        )

        # Should not have duplicate SEC URL
        sec_urls = [s["url"] for s in result["sources"] if "sec.gov" in s["url"]]
        assert len(set(sec_urls)) == len(sec_urls)

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_tavily_failure_graceful(self, mock_tavily):
        """Tavily failure should not destroy SEC-based operation."""
        mock_tavily.side_effect = RuntimeError("Tavily API error")

        result = discover_sources(
            company_name="Microsoft Corporation",
            ticker="MSFT",
            period_mode="latest",
            sec_registry=_mock_sec_registry(),
        )

        # Should still return SEC sources
        assert "sources" in result
        assert result["company"]["name"] == "Microsoft Corporation"

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_no_sec_registry(self, mock_tavily):
        """Should work with no SEC registry."""
        mock_tavily.return_value = {"results": [], "query": "test"}

        result = discover_sources(
            company_name="Apple Inc.",
            ticker="AAPL",
            period_mode="latest",
        )

        assert result["company"]["ticker"] == "AAPL"
        assert result["metadata"]["tavily_searches"] == 2

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_specified_period(self, mock_tavily):
        """Should use period-specific queries."""
        mock_tavily.return_value = {"results": [], "query": "test"}

        result = discover_sources(
            company_name="NVIDIA Corporation",
            ticker="NVDA",
            period_mode="specified",
            start_year=2023,
            end_year=2025,
        )

        assert result["period"]["mode"] == "specified"
        assert result["period"]["start_year"] == 2023
        assert result["period"]["end_year"] == 2025

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_metadata(self, mock_tavily):
        """Should return correct metadata."""
        mock_tavily.return_value = {
            "results": [
                _mock_tavily_result("Annual Report", "https://investor.microsoft.com"),
            ],
            "query": "test",
        }

        result = discover_sources(
            company_name="Microsoft Corporation",
            ticker="MSFT",
            period_mode="latest",
            sec_registry=_mock_sec_registry(),
        )

        meta = result["metadata"]
        assert meta["total_sources"] >= 1
        assert meta["sec_sources"] >= 1
        assert meta["tavily_searches"] == 2

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_official_ir_accepted(self, mock_tavily):
        """Official IR pages should be accepted."""
        mock_tavily.return_value = {
            "results": [
                _mock_tavily_result(
                    "Investor Relations - Microsoft",
                    "https://www.microsoft.com/en-us/investor/",
                ),
            ],
            "query": "test",
        }

        result = discover_sources(
            company_name="Microsoft Corporation",
            ticker="MSFT",
            period_mode="latest",
        )

        ir_sources = [s for s in result["sources"] if "investor" in s["url"].lower()]
        assert len(ir_sources) >= 1

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_search_count(self, mock_tavily):
        """Should track Tavily search count in metadata."""
        mock_tavily.return_value = {"results": [], "query": "test"}

        result = discover_sources(
            company_name="Test Corp",
            ticker="TEST",
            period_mode="latest",
        )

        assert result["metadata"]["tavily_searches"] == 2

    @patch("lib.source_discovery.tavily_search")
    def test_discovery_earnings_release_accepted(self, mock_tavily):
        """Official earnings releases should be accepted."""
        mock_tavily.return_value = {
            "results": [
                _mock_tavily_result(
                    "Q3 2025 Earnings Release - Apple",
                    "https://investor.apple.com/earnings",
                ),
            ],
            "query": "test",
        }

        result = discover_sources(
            company_name="Apple Inc.",
            ticker="AAPL",
            period_mode="latest",
        )

        earnings_sources = [s for s in result["sources"]
                           if s["source_type"] in ("quarterly_earnings", "annual_report", "investor_presentation")]
        assert len(earnings_sources) >= 1
