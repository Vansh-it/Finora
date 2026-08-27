"""Unit tests for the research session service.

All tests run offline — no LLM calls, no web requests.
10 tests covering: valid plans, missing company, malformed request,
successful session creation, unique UUID creation, permission cancelled,
duplicate clicks, and session lookup.
"""

from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
import sys
import os

# Ensure backend/ is on the path so lib.* imports resolve
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from lib.research_session import (
    ResearchSession,
    grant_permission,
    get_session,
    cancel_session,
    update_session_status,
    set_session_company_meta,
    set_session_document_registry,
    set_session_source_registry,
    set_session_verification_results,
    set_session_executive_summary,
    set_session_error,
    get_active_sessions_for_company,
    clear_all_sessions,
)


# ── Fixtures ─────────────────────────────────────────────────────────────────
@pytest.fixture(autouse=True)
def _clean_sessions():
    """Clear all sessions before and after each test."""
    clear_all_sessions()
    yield
    clear_all_sessions()


# ═════════════════════════════════════════════════════════════════════════════
# Group 1: Successful session creation (tests 1-4)
# ═════════════════════════════════════════════════════════════════════════════


class TestSessionCreation:
    """Tests 1-4: Creating sessions from valid plans."""

    def test_01_valid_plan_creates_session(self):
        """A valid plan with company creates a session."""
        plan = {
            "company": "Microsoft",
            "start_year": 2024,
            "end_year": 2025,
            "objective": "Financial Research & Metric Calculation",
        }
        session = grant_permission(plan)
        assert session.status == "researching"
        assert session.company == "Microsoft"
        assert session.start_year == 2024
        assert session.end_year == 2025
        assert session.objective == "Financial Research & Metric Calculation"

    def test_02_session_has_uuid(self):
        """Each session gets a unique hex UUID as session_id."""
        session = grant_permission({"company": "Apple"})
        assert isinstance(session.session_id, str)
        assert len(session.session_id) == 32  # uuid4().hex
        # Verify it's valid hex
        int(session.session_id, 16)

    def test_03_session_has_created_at(self):
        """Session created_at is an ISO timestamp."""
        session = grant_permission({"company": "Tesla"})
        assert session.created_at is not None
        # ISO format contains T separator
        assert "T" in session.created_at

    def test_04_to_dict_returns_expected_keys(self):
        """to_dict() returns all required keys."""
        session = grant_permission({
            "company": "NVIDIA",
            "start_year": 2023,
            "end_year": 2024,
            "objective": "Revenue analysis",
        })
        d = session.to_dict()
        assert d["session_id"] == session.session_id
        assert d["company"] == "NVIDIA"
        assert d["start_year"] == 2023
        assert d["end_year"] == 2024
        assert d["objective"] == "Revenue analysis"
        assert d["status"] == "researching"
        assert "created_at" in d


# ═════════════════════════════════════════════════════════════════════════════
# Group 2: Validation & errors (tests 5-6)
# ═════════════════════════════════════════════════════════════════════════════


class TestValidation:
    """Tests 5-6: Missing or empty company raises ValueError."""

    def test_05_empty_company_raises(self):
        """Empty string company → ValueError."""
        with pytest.raises(ValueError, match="non-empty 'company'"):
            grant_permission({"company": ""})

    def test_06_none_company_raises(self):
        """None company → ValueError."""
        with pytest.raises(ValueError, match="non-empty 'company'"):
            grant_permission({"company": None})


# ═════════════════════════════════════════════════════════════════════════════
# Group 3: Unique UUIDs (test 7)
# ═════════════════════════════════════════════════════════════════════════════


class TestUniqueUUID:
    """Test 7: Two consecutive sessions get different IDs."""

    def test_07_unique_uuids(self):
        """Two sessions for the same company get different session_ids."""
        s1 = grant_permission({"company": "Microsoft"})
        s2 = grant_permission({"company": "Microsoft"})
        assert s1.session_id != s2.session_id


# ═════════════════════════════════════════════════════════════════════════════
# Group 4: Permission cancellation (test 8)
# ═════════════════════════════════════════════════════════════════════════════


class TestCancellation:
    """Test 8: Cancelling a session."""

    def test_08_cancel_session(self):
        """Cancelling an active session sets status to 'cancelled'."""
        session = grant_permission({"company": "Apple"})
        assert cancel_session(session.session_id) is True
        fetched = get_session(session.session_id)
        assert fetched.status == "cancelled"


# ═════════════════════════════════════════════════════════════════════════════
# Group 5: Duplicate clicks (test 9)
# ═════════════════════════════════════════════════════════════════════════════


class TestDuplicateClicks:
    """Test 9: Multiple grants for the same company create separate sessions."""

    def test_09_duplicate_clicks_create_separate_sessions(self):
        """Clicking 'Grant Permission' twice creates two active sessions."""
        s1 = grant_permission({"company": "Google"})
        s2 = grant_permission({"company": "Google"})
        active = get_active_sessions_for_company("Google")
        assert len(active) == 2
        assert s1.session_id != s2.session_id


# ═════════════════════════════════════════════════════════════════════════════
# Group 6: Session lookup (test 10)
# ═════════════════════════════════════════════════════════════════════════════


class TestSessionLookup:
    """Test 10: Looking up a session that doesn't exist."""

    def test_10_get_nonexistent_session(self):
        """Looking up a random UUID returns None."""
        result = get_session("does-not-exist")
        assert result is None


# ═════════════════════════════════════════════════════════════════════════════
# Group 7: New session features (tests 11-18)
# ═════════════════════════════════════════════════════════════════════════════


class TestNewSessionFeatures:
    """Tests 11-18: period_mode, status progression, company meta, registry, errors."""

    def test_11_period_mode_defaults_to_latest(self):
        session = grant_permission({"company": "Microsoft"})
        assert session.period_mode == "latest"

    def test_12_period_mode_specified(self):
        session = grant_permission({"company": "Apple", "period_mode": "specified"})
        assert session.period_mode == "specified"

    def test_13_period_mode_invalid_falls_back(self):
        session = grant_permission({"company": "Tesla", "period_mode": "invalid"})
        assert session.period_mode == "latest"

    def test_14_update_session_status(self):
        session = grant_permission({"company": "NVIDIA"})
        assert update_session_status(session.session_id, "resolving_company") is True
        fetched = get_session(session.session_id)
        assert fetched.status == "resolving_company"

    def test_15_update_nonexistent_session(self):
        assert update_session_status("no-such-id", "resolving_company") is False

    def test_16_set_company_meta(self):
        session = grant_permission({"company": "MSFT"})
        meta = {"name": "Microsoft Corporation", "ticker": "MSFT", "cik": "0000789019"}
        assert set_session_company_meta(session.session_id, meta) is True
        fetched = get_session(session.session_id)
        assert fetched.company_meta == meta

    def test_17_set_document_registry(self):
        session = grant_permission({"company": "AAPL"})
        registry = {"documents": [{"form": "10-K"}]}
        assert set_session_document_registry(session.session_id, registry) is True
        fetched = get_session(session.session_id)
        assert fetched.document_registry == registry

    def test_18_set_session_error(self):
        session = grant_permission({"company": "XYZ"})
        assert set_session_error(session.session_id, "Company not found") is True
        fetched = get_session(session.session_id)
        assert fetched.status == "error"
        assert fetched.error == "Company not found"

    def test_19_set_source_registry(self):
        session = grant_permission({"company": "MSFT"})
        registry = {
            "company": {"name": "Microsoft", "ticker": "MSFT"},
            "sources": [{"source_id": "sec_001", "trust_tier": 1}],
            "metadata": {"total_sources": 1},
        }
        assert set_session_source_registry(session.session_id, registry) is True
        fetched = get_session(session.session_id)
        assert fetched.source_registry == registry
        assert "source_registry" in fetched.to_dict()

    def test_20_source_registry_none_by_default(self):
        session = grant_permission({"company": "TEST"})
        assert session.source_registry is None
        result = session.to_dict()
        assert "source_registry" not in result

    def test_21_source_registry_on_nonexistent_session(self):
        assert set_session_source_registry("fake_id", {}) is False

    def test_22_source_discovery_statuses(self):
        session = grant_permission({"company": "TEST"})
        for status in ["discovering_sources", "filtering_sources",
                       "validating_sources", "sources_discovered",
                       "ready_for_reading"]:
            update_session_status(session.session_id, status)
            fetched = get_session(session.session_id)
            assert fetched.status == status

    def test_23_set_verification_results(self):
        session = grant_permission({"company": "MSFT"})
        results = {
            "verifications": [{"metric_id": "revenue", "verification_status": "exact_match"}],
            "summary": {"total_compared": 1, "exact_matches": 1},
        }
        assert set_session_verification_results(session.session_id, results) is True
        fetched = get_session(session.session_id)
        assert fetched.verification_results == results
        assert "verification_results" in fetched.to_dict()

    def test_24_verification_results_none_by_default(self):
        session = grant_permission({"company": "TEST"})
        assert session.verification_results is None
        result = session.to_dict()
        assert "verification_results" not in result

    def test_25_verification_on_nonexistent_session(self):
        assert set_session_verification_results("fake_id", {}) is False

    def test_26_verification_statuses(self):
        session = grant_permission({"company": "TEST"})
        for status in ["reading_sources", "extracting_source_facts",
                       "cross_checking_sources", "verification_complete",
                       "ready_for_dashboard"]:
            update_session_status(session.session_id, status)
            fetched = get_session(session.session_id)
            assert fetched.status == status

    def test_27_set_executive_summary(self):
        session = grant_permission({"company": "MSFT"})
        summary = {
            "executive_overview": "Microsoft delivered strong results.",
            "highlights": [{"title": "Revenue", "text": "Grew 16%.", "importance": "high"}],
            "growth_analysis": "Revenue grew.",
            "profitability_analysis": "Margins expanded.",
            "cash_flow_analysis": "FCF strong.",
            "balance_sheet_analysis": "Healthy.",
            "watch_items": [],
            "management_commentary_summary": "",
            "data_quality_note": "SEC XBRL primary.",
        }
        assert set_session_executive_summary(session.session_id, summary) is True
        fetched = get_session(session.session_id)
        assert fetched.executive_summary == summary
        assert "executive_summary" in fetched.to_dict()

    def test_28_executive_summary_none_by_default(self):
        session = grant_permission({"company": "TEST"})
        assert session.executive_summary is None
        result = session.to_dict()
        assert "executive_summary" not in result

    def test_29_executive_summary_on_nonexistent_session(self):
        assert set_session_executive_summary("fake_id", {}) is False

    def test_30_analysis_statuses(self):
        session = grant_permission({"company": "TEST"})
        for status in ["generating_analysis", "validating_analysis", "analysis_complete"]:
            update_session_status(session.session_id, status)
            fetched = get_session(session.session_id)
            assert fetched.status == status
