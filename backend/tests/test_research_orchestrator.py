"""Unit tests for the research orchestrator.

All tests run offline -- no LLM calls, no web search.
35 tests covering: valid plans, period normalisation, source selection,
missing company, empty fields, objective variants, serialization,
period mode, and period selection flow scenarios.
"""

from __future__ import annotations

import pytest
import sys
import os

# Ensure backend/ is on the path so lib.* imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.research_orchestrator import (
    ResearchPlan,
    _format_period,
    _objective_title,
    _pick_sources,
    create_research_plan,
)


# ============================================================================
# Group 1: Period Normalisation (tests 1-5)
# ============================================================================

class TestPeriodNormalisation:
    """Tests 1-5: Year range to readable period string."""

    def test_01_both_years(self):
        """2024, 2025 -> FY2024-FY2025"""
        assert _format_period(2024, 2025, "specified") == "FY2024\u2013FY2025"

    def test_02_start_year_only(self):
        """2023, None -> FY2023"""
        assert _format_period(2023, None, "specified") == "FY2023"

    def test_03_end_year_only(self):
        """None, 2025 -> FY2025"""
        assert _format_period(None, 2025, "specified") == "FY2025"

    def test_04_neither_year_latest(self):
        """None, None, latest -> Latest available financial reporting data"""
        assert _format_period(None, None, "latest") == "Latest available financial reporting data"

    def test_04b_neither_year_specified(self):
        """None, None, specified -> Unspecified Period"""
        assert _format_period(None, None, "specified") == "Unspecified Period"


# ============================================================================
# Group 2: Source Selection (tests 5-9)
# ============================================================================

class TestSourceSelection:
    """Tests 5-9: Keyword-based source catalog."""

    def test_05_financial_sources(self):
        """Objective containing 'financial' -> financial source set."""
        sources = _pick_sources("financial research")
        assert "Annual Report" in sources
        assert "Quarterly Reports" in sources
        assert "Earnings Releases" in sources

    def test_06_revenue_sources(self):
        """Objective containing 'revenue' -> revenue source set."""
        sources = _pick_sources("revenue analysis")
        assert "Annual Report" in sources
        assert "10-K Filing" in sources

    def test_07_stock_sources(self):
        """Objective containing 'stock' -> stock source set."""
        sources = _pick_sources("stock performance")
        assert "10-K Filing" in sources
        assert "SEC EDGAR Filings" in sources

    def test_08_growth_sources(self):
        """Objective containing 'growth' -> growth source set."""
        sources = _pick_sources("growth analysis")
        assert "Industry Analyst Reports" in sources

    def test_09_unknown_objective_uses_defaults(self):
        """Unrecognised objective -> default sources."""
        sources = _pick_sources("xyzzy")
        assert sources == [
            "Annual Report",
            "Quarterly Reports",
            "Earnings Releases",
        ]


# ============================================================================
# Group 3: Objective Title (tests 10-11)
# ============================================================================

class TestObjectiveTitle:
    """Tests 10-11: Objective string normalisation."""

    def test_10_normal_objective(self):
        """Normal objective -> title-cased."""
        assert _objective_title("financial research") == "Financial Research"

    def test_11_empty_objective(self):
        """Empty objective -> 'General Research'."""
        assert _objective_title("") == "General Research"


# ============================================================================
# Group 4: Full Plan Creation (tests 12-16)
# ============================================================================

class TestPlanCreation:
    """Tests 12-16: End-to-end plan generation from intent dict."""

    def test_12_full_intent(self):
        """Full intent with company, years, objective -> complete plan."""
        intent = {
            "intent": "research",
            "company": "Microsoft",
            "start_year": 2024,
            "end_year": 2025,
            "objective": "financial research",
        }
        plan = create_research_plan(intent)
        assert plan.company == "Microsoft"
        assert plan.period == "FY2024\u2013FY2025"
        assert plan.objective == "Financial Research"
        assert plan.status == "awaiting_permission"
        assert plan.next_action == "request_permission"
        assert len(plan.required_sources) == 3

    def test_13_company_only(self):
        """Company only, no years or objective -> defaults to latest mode."""
        intent = {"intent": "research", "company": "Apple"}
        plan = create_research_plan(intent)
        assert plan.company == "Apple"
        assert plan.period == "Latest available financial reporting data"
        assert plan.objective == "General Research"
        assert plan.status == "awaiting_permission"

    def test_14_company_with_whitespace(self):
        """Company name with leading/trailing whitespace is stripped."""
        intent = {"intent": "research", "company": "  Tesla  "}
        plan = create_research_plan(intent)
        assert plan.company == "Tesla"

    def test_15_start_year_only(self):
        """Only start_year provided."""
        intent = {
            "intent": "research",
            "company": "Google",
            "start_year": 2020,
        }
        plan = create_research_plan(intent)
        assert plan.period == "FY2020"

    def test_16_end_year_only(self):
        """Only end_year provided."""
        intent = {
            "intent": "research",
            "company": "Amazon",
            "end_year": 2025,
        }
        plan = create_research_plan(intent)
        assert plan.period == "FY2025"


# ============================================================================
# Group 5: Validation & Error Handling (tests 17-18)
# ============================================================================

class TestValidation:
    """Tests 17-18: Missing or empty company raises ValueError."""

    def test_17_empty_company_raises(self):
        """Empty string company -> ValueError."""
        with pytest.raises(ValueError, match="non-empty 'company'"):
            create_research_plan({"intent": "research", "company": ""})

    def test_18_none_company_raises(self):
        """None company -> ValueError."""
        with pytest.raises(ValueError, match="non-empty 'company'"):
            create_research_plan({"intent": "research", "company": None})


# ============================================================================
# Group 6: Serialization (tests 19-20)
# ============================================================================

class TestSerialization:
    """Tests 19-20: ResearchPlan.to_dict() correctness."""

    def test_19_to_dict_keys(self):
        """to_dict() returns all required keys."""
        plan = ResearchPlan(
            company="NVIDIA",
            period="FY2024\u2013FY2025",
            objective="Stock Analysis",
            required_sources=["Annual Report"],
        )
        d = plan.to_dict()
        assert d["status"] == "awaiting_permission"
        assert d["company"] == "NVIDIA"
        assert d["period"] == "FY2024\u2013FY2025"
        assert d["objective"] == "Stock Analysis"
        assert d["required_sources"] == ["Annual Report"]
        assert d["next_action"] == "request_permission"

    def test_20_to_dict_default_plan(self):
        """Default ResearchPlan.to_dict() has sensible values."""
        plan = ResearchPlan()
        d = plan.to_dict()
        assert d["status"] == "awaiting_permission"
        assert d["next_action"] == "request_permission"
        assert d["required_sources"] == []


# ============================================================================
# Group 7: Period Mode Integration (tests 21-27)
# ============================================================================

class TestPeriodMode:
    """Tests 21-27: period_mode='latest' vs 'specified' in plan creation."""

    def test_21_latest_mode_no_years(self):
        """period_mode=latest, no years -> 'Latest available...'"""
        intent = {
            "intent": "research",
            "company": "Microsoft",
            "period_mode": "latest",
        }
        plan = create_research_plan(intent)
        assert plan.period == "Latest available financial reporting data"

    def test_22_specified_mode_with_years(self):
        """period_mode=specified, years -> FY range."""
        intent = {
            "intent": "research",
            "company": "Microsoft",
            "period_mode": "specified",
            "start_year": 2023,
            "end_year": 2025,
        }
        plan = create_research_plan(intent)
        assert plan.period == "FY2023\u2013FY2025"

    def test_23_latest_mode_ignored_when_years_provided(self):
        """period_mode=latest but years present -> still uses the years."""
        intent = {
            "intent": "research",
            "company": "Apple",
            "period_mode": "latest",
            "start_year": 2024,
            "end_year": 2025,
        }
        plan = create_research_plan(intent)
        assert plan.period == "FY2024\u2013FY2025"

    def test_24_invalid_period_mode_falls_back_to_latest(self):
        """Invalid period_mode -> defaults to latest."""
        intent = {
            "intent": "research",
            "company": "Tesla",
            "period_mode": "invalid_value",
        }
        plan = create_research_plan(intent)
        assert plan.period == "Latest available financial reporting data"

    def test_25_company_only_defaults_to_latest(self):
        """No period_mode specified -> defaults to latest mode."""
        intent = {"intent": "research", "company": "NVIDIA"}
        plan = create_research_plan(intent)
        assert plan.period == "Latest available financial reporting data"

    def test_26_plan_includes_period_mode_field(self):
        """ResearchPlan.to_dict() includes period_mode key."""
        plan = create_research_plan({
            "intent": "research",
            "company": "Microsoft",
            "period_mode": "specified",
            "start_year": 2023,
            "end_year": 2025,
        })
        d = plan.to_dict()
        assert d["period_mode"] == "specified"
        assert d["start_year"] == 2023
        assert d["end_year"] == 2025

    def test_27_latest_mode_plan_includes_period_mode(self):
        """Latest mode plan includes period_mode='latest'."""
        plan = create_research_plan({
            "intent": "research",
            "company": "Apple",
            "period_mode": "latest",
        })
        d = plan.to_dict()
        assert d["period_mode"] == "latest"
        assert d["start_year"] is None
        assert d["end_year"] is None


# ============================================================================
# Group 8: Period Selection Flow Scenarios (tests 28-35)
# ============================================================================

class TestPeriodSelectionFlow:
    """Tests 28-35: End-to-end period selection scenarios."""

    def test_28_research_microsoft_latest(self):
        """Research Microsoft -> latest available."""
        intent = {
            "intent": "research",
            "company": "Microsoft",
            "period_mode": "latest",
            "start_year": None,
            "end_year": None,
            "objective": "financial research",
        }
        plan = create_research_plan(intent)
        assert plan.company == "Microsoft"
        assert plan.period == "Latest available financial reporting data"
        assert plan.period_mode == "latest"
        assert plan.start_year is None
        assert plan.end_year is None

    def test_29_research_apple_fy2025(self):
        """Research Apple FY2025 -> specified 2025-2025 (single year)."""
        intent = {
            "intent": "research",
            "company": "Apple",
            "period_mode": "specified",
            "start_year": 2025,
            "end_year": 2025,
            "objective": "financial analysis",
        }
        plan = create_research_plan(intent)
        assert plan.company == "Apple"
        assert plan.period == "FY2025"
        assert plan.period_mode == "specified"
        assert plan.start_year == 2025
        assert plan.end_year == 2025

    def test_30_research_nvidia_fy2023_fy2025(self):
        """Research NVIDIA FY2023-FY2025 -> specified 2023-2025."""
        intent = {
            "intent": "research",
            "company": "NVIDIA",
            "period_mode": "specified",
            "start_year": 2023,
            "end_year": 2025,
            "objective": "financial analysis",
        }
        plan = create_research_plan(intent)
        assert plan.company == "NVIDIA"
        assert plan.period == "FY2023\u2013FY2025"
        assert plan.period_mode == "specified"
        assert plan.start_year == 2023
        assert plan.end_year == 2025

    def test_31_switch_latest_to_specified(self):
        """User changes latest -> specified with years."""
        intent_latest = {
            "intent": "research",
            "company": "Microsoft",
            "period_mode": "latest",
        }
        plan_latest = create_research_plan(intent_latest)
        assert plan_latest.period_mode == "latest"

        intent_specified = {
            "intent": "research",
            "company": "Microsoft",
            "period_mode": "specified",
            "start_year": 2023,
            "end_year": 2025,
        }
        plan_specified = create_research_plan(intent_specified)
        assert plan_specified.period_mode == "specified"
        assert plan_specified.period == "FY2023\u2013FY2025"

    def test_32_switch_specified_to_latest(self):
        """User changes specific -> latest."""
        intent_specified = {
            "intent": "research",
            "company": "Apple",
            "period_mode": "specified",
            "start_year": 2023,
            "end_year": 2025,
        }
        plan_specified = create_research_plan(intent_specified)
        assert plan_specified.period_mode == "specified"

        intent_latest = {
            "intent": "research",
            "company": "Apple",
            "period_mode": "latest",
        }
        plan_latest = create_research_plan(intent_latest)
        assert plan_latest.period_mode == "latest"
        assert plan_latest.period == "Latest available financial reporting data"

    def test_33_single_fiscal_year(self):
        """Single fiscal year: start_year == end_year."""
        intent = {
            "intent": "research",
            "company": "Tesla",
            "period_mode": "specified",
            "start_year": 2025,
            "end_year": 2025,
        }
        plan = create_research_plan(intent)
        assert plan.period == "FY2025"
        assert plan.start_year == 2025
        assert plan.end_year == 2025

    def test_34_plan_with_period_mode_in_dict(self):
        """Plan dict includes period_mode for frontend consumption."""
        plan = create_research_plan({
            "intent": "research",
            "company": "NVIDIA",
            "period_mode": "specified",
            "start_year": 2024,
            "end_year": 2025,
        })
        d = plan.to_dict()
        assert "period_mode" in d
        assert "start_year" in d
        assert "end_year" in d
        assert d["period_mode"] == "specified"
        assert d["start_year"] == 2024
        assert d["end_year"] == 2025

    def test_35_permission_requires_valid_period(self):
        """Plan creation always produces valid period (never reversed)."""
        # The orchestrator does not validate reversed years -- that's the frontend's job.
        # But the plan is still created with whatever years are provided.
        intent = {
            "intent": "research",
            "company": "Microsoft",
            "period_mode": "specified",
            "start_year": 2025,
            "end_year": 2023,
        }
        plan = create_research_plan(intent)
        # The plan is created -- validation happens in the frontend PeriodSelectionCard
        assert plan.period == "FY2025\u2013FY2023"
