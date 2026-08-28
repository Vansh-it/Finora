"""Research session service.

Manages research sessions with JSON-file persistence.  When a user grants
permission for a research plan, this module creates a session and returns
a unique ID. Sessions are owned by a user_id.

Session statuses progress through real states:
  researching → resolving_company → company_resolved →
  fetching_filings → filings_found → ready_for_extraction
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from lib.persistence import save_research_sessions, load_research_sessions


# ── Status constants ──────────────────────────────────────────────────────────
STATUS_RESEARCHING = "researching"
STATUS_RESOLVING_COMPANY = "resolving_company"
STATUS_COMPANY_RESOLVED = "company_resolved"
STATUS_FETCHING_FILINGS = "fetching_filings"
STATUS_FILINGS_FOUND = "filings_found"
STATUS_READY_FOR_EXTRACTION = "ready_for_extraction"
STATUS_FETCHING_XBRL = "fetching_xbrl"
STATUS_EXTRACTING_FINANCIALS = "extracting_financials"
STATUS_VALIDATING_FINANCIALS = "validating_financials"
STATUS_FINANCIALS_EXTRACTED = "financials_extracted"
STATUS_READY_FOR_CALCULATION = "ready_for_calculation"
STATUS_CALCULATING_METRICS = "calculating_metrics"
STATUS_VALIDATING_METRICS = "validating_metrics"
STATUS_METRICS_CALCULATED = "metrics_calculated"
STATUS_READY_FOR_ANALYSIS = "ready_for_analysis"
STATUS_DISCOVERING_SOURCES = "discovering_sources"
STATUS_FILTERING_SOURCES = "filtering_sources"
STATUS_VALIDATING_SOURCES = "validating_sources"
STATUS_SOURCES_DISCOVERED = "sources_discovered"
STATUS_READY_FOR_READING = "ready_for_reading"
STATUS_READING_SOURCES = "reading_sources"
STATUS_EXTRACTING_SOURCE_FACTS = "extracting_source_facts"
STATUS_CROSS_CHECKING_SOURCES = "cross_checking_sources"
STATUS_VERIFICATION_COMPLETE = "verification_complete"
STATUS_READY_FOR_DASHBOARD = "ready_for_dashboard"
STATUS_GENERATING_ANALYSIS = "generating_analysis"
STATUS_VALIDATING_ANALYSIS = "validating_analysis"
STATUS_ANALYSIS_COMPLETE = "analysis_complete"
STATUS_FETCHING_MARKET_DATA = "fetching_market_data"
STATUS_CALCULATING_VALUATION = "calculating_valuation"
STATUS_VALIDATING_VALUATION = "validating_valuation"
STATUS_VALUATION_COMPLETE = "valuation_complete"
STATUS_CANCELLED = "cancelled"
STATUS_ERROR = "error"

_ACTIVE_STATUSES = {
    STATUS_RESEARCHING,
    STATUS_RESOLVING_COMPANY,
    STATUS_COMPANY_RESOLVED,
    STATUS_FETCHING_FILINGS,
    STATUS_FILINGS_FOUND,
    STATUS_READY_FOR_EXTRACTION,
    STATUS_FETCHING_XBRL,
    STATUS_EXTRACTING_FINANCIALS,
    STATUS_VALIDATING_FINANCIALS,
    STATUS_FINANCIALS_EXTRACTED,
    STATUS_READY_FOR_CALCULATION,
    STATUS_CALCULATING_METRICS,
    STATUS_VALIDATING_METRICS,
    STATUS_METRICS_CALCULATED,
    STATUS_READY_FOR_ANALYSIS,
    STATUS_DISCOVERING_SOURCES,
    STATUS_FILTERING_SOURCES,
    STATUS_VALIDATING_SOURCES,
    STATUS_SOURCES_DISCOVERED,
    STATUS_READY_FOR_READING,
    STATUS_READING_SOURCES,
    STATUS_EXTRACTING_SOURCE_FACTS,
    STATUS_CROSS_CHECKING_SOURCES,
    STATUS_VERIFICATION_COMPLETE,
    STATUS_READY_FOR_DASHBOARD,
    STATUS_GENERATING_ANALYSIS,
    STATUS_VALIDATING_ANALYSIS,
    STATUS_ANALYSIS_COMPLETE,
    STATUS_FETCHING_MARKET_DATA,
    STATUS_CALCULATING_VALUATION,
    STATUS_VALIDATING_VALUATION,
    STATUS_VALUATION_COMPLETE,
}

_COMPLETED_STATUSES = {
    STATUS_READY_FOR_DASHBOARD,
    STATUS_ANALYSIS_COMPLETE,
    STATUS_VALUATION_COMPLETE,
}


# ── In-memory session store (synced to disk) ─────────────────────────────────
_sessions: dict[str, "ResearchSession"] = {}
_loaded = False
_last_load_time: float = 0.0

# Reload disk state at most every 0.5 seconds to stay in sync with
# external writers (Astro API routes) without excessive I/O.
_RELOAD_INTERVAL = 0.5


def _ensure_loaded() -> None:
    """Load persisted sessions into memory, re-syncing from disk.

    The previous implementation loaded once and never re-read, which
    caused a split-brain: Astro sessions written to disk were invisible
    to Flask's in-memory cache.  Now we re-read from disk periodically
    so sessions created by either process are always visible.
    """
    global _loaded, _last_load_time
    import time as _time
    now = _time.time()

    if _loaded and (now - _last_load_time) < _RELOAD_INTERVAL:
        return

    _last_load_time = now
    _loaded = True

    raw = load_research_sessions()
    # Merge: disk is source of truth for sessions we don't have in memory
    for sid, sdata in raw.items():
        if not isinstance(sdata, dict):
            continue
        if sid in _sessions:
            # Session already in memory — update mutable fields from disk
            # so status/data changes from other processes are visible.
            session = _sessions[sid]
            disk_status = sdata.get("status", session.status)
            if disk_status != session.status:
                session.status = disk_status
            for field in (
                "company_meta", "document_registry", "financial_statements",
                "calculated_metrics", "source_registry", "verification_results",
                "executive_summary", "market_data", "valuation_metrics", "error",
            ):
                disk_val = sdata.get(field)
                if disk_val is not None:
                    setattr(session, field, disk_val)
        else:
            _sessions[sid] = ResearchSession(
                session_id=sdata.get("session_id", sid),
                company=sdata.get("company", ""),
                start_year=sdata.get("start_year"),
                end_year=sdata.get("end_year"),
                period_mode=sdata.get("period_mode", "latest"),
                objective=sdata.get("objective", ""),
                status=sdata.get("status", STATUS_RESEARCHING),
                created_at=sdata.get("created_at", ""),
                user_id=sdata.get("user_id", ""),
                company_meta=sdata.get("company_meta"),
                document_registry=sdata.get("document_registry"),
                financial_statements=sdata.get("financial_statements"),
                calculated_metrics=sdata.get("calculated_metrics"),
                source_registry=sdata.get("source_registry"),
                verification_results=sdata.get("verification_results"),
                executive_summary=sdata.get("executive_summary"),
                market_data=sdata.get("market_data"),
                valuation_metrics=sdata.get("valuation_metrics"),
                error=sdata.get("error"),
            )


def _persist() -> None:
    """Save all research sessions to disk."""
    raw = {}
    for sid, session in _sessions.items():
        raw[sid] = session.to_dict()
    save_research_sessions(raw)


@dataclass
class ResearchSession:
    """A single research session created after the user grants permission."""

    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    company: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    period_mode: str = "latest"
    objective: str = ""
    status: str = STATUS_RESEARCHING
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    # Ownership
    user_id: str = ""

    # Company metadata (populated after resolution)
    company_meta: Optional[dict] = None

    # Document registry (populated after filing retrieval)
    document_registry: Optional[dict] = None

    # Financial statements (populated after extraction)
    financial_statements: Optional[dict] = None

    # Calculated metrics (populated after calculation)
    calculated_metrics: Optional[dict] = None

    # Source registry (populated after source discovery)
    source_registry: Optional[dict] = None

    # Verification results (populated after cross-source verification)
    verification_results: Optional[dict] = None

    # Executive summary (populated after analysis generation)
    executive_summary: Optional[dict] = None

    # Market data (populated after market data retrieval)
    market_data: Optional[dict] = None

    # Valuation metrics (populated after valuation calculation)
    valuation_metrics: Optional[dict] = None

    # Error info
    error: Optional[str] = None

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {
            "session_id": self.session_id,
            "company": self.company,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "period_mode": self.period_mode,
            "objective": self.objective,
            "status": self.status,
            "created_at": self.created_at,
            "user_id": self.user_id,
        }
        if self.company_meta:
            result["company_meta"] = self.company_meta
        if self.document_registry:
            result["document_registry"] = self.document_registry
        if self.financial_statements:
            result["financial_statements"] = self.financial_statements
        if self.calculated_metrics:
            result["calculated_metrics"] = self.calculated_metrics
        if self.source_registry:
            result["source_registry"] = self.source_registry
        if self.verification_results:
            result["verification_results"] = self.verification_results
        if self.executive_summary:
            result["executive_summary"] = self.executive_summary
        if self.market_data:
            result["market_data"] = self.market_data
        if self.valuation_metrics:
            result["valuation_metrics"] = self.valuation_metrics
        if self.error:
            result["error"] = self.error
        return result

    def update_status(self, new_status: str) -> None:
        """Update session status with validation."""
        self.status = new_status

    def set_error(self, error_msg: str) -> None:
        """Set error status with message."""
        self.status = STATUS_ERROR
        self.error = error_msg

    def is_completed(self) -> bool:
        """Check if session reached a successful completion state."""
        return self.status in _COMPLETED_STATUSES


# ── Public API ───────────────────────────────────────────────────────────────
def grant_permission(plan: dict[str, Any], user_id: str = "") -> ResearchSession:
    """Grant permission and create a research session from a plan dict.

    Parameters
    ----------
    plan : dict
        Must contain ``"company"`` (non-empty string).
        May contain ``"start_year"``, ``"end_year"``, ``"period_mode"``, ``"objective"``.
    user_id : str
        The authenticated user's ID for ownership tracking.

    Returns
    -------
    ResearchSession
        The newly created session with status ``"researching"``.

    Raises
    ------
    ValueError
        If company is missing or empty.
    """
    _ensure_loaded()
    company = plan.get("company")
    if not isinstance(company, str) or not company.strip():
        raise ValueError("Plan must include a non-empty 'company' field")
    company = company.strip()

    start_year = plan.get("start_year")
    end_year = plan.get("end_year")
    if start_year is not None:
        start_year = int(start_year)
    if end_year is not None:
        end_year = int(end_year)

    period_mode = plan.get("period_mode", "latest")
    if period_mode not in ("specified", "latest"):
        period_mode = "latest"

    objective = str(plan.get("objective", "")).strip()

    session = ResearchSession(
        company=company,
        start_year=start_year,
        end_year=end_year,
        period_mode=period_mode,
        objective=objective,
        user_id=user_id,
    )
    _sessions[session.session_id] = session
    _persist()
    return session


def get_session(session_id: str) -> Optional[ResearchSession]:
    """Look up a session by ID.  Returns ``None`` if not found."""
    _ensure_loaded()
    return _sessions.get(session_id)


def get_user_sessions(user_id: str) -> list[ResearchSession]:
    """Get all sessions belonging to a user."""
    _ensure_loaded()
    return [s for s in _sessions.values() if s.user_id == user_id]


def cancel_session(session_id: str) -> bool:
    """Cancel an active session.  Returns ``True`` if found and cancelled."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.status = STATUS_CANCELLED
    _persist()
    return True


def update_session_status(session_id: str, status: str) -> bool:
    """Update session status. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.update_status(status)
    _persist()
    return True


def set_session_company_meta(session_id: str, meta: dict) -> bool:
    """Store resolved company metadata. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.company_meta = meta
    _persist()
    return True


def set_session_document_registry(session_id: str, registry: dict) -> bool:
    """Store document registry. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.document_registry = registry
    _persist()
    return True


def set_session_financial_statements(session_id: str, statements: dict) -> bool:
    """Store extracted financial statements. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.financial_statements = statements
    _persist()
    return True


def set_session_calculated_metrics(session_id: str, metrics: dict) -> bool:
    """Store calculated metrics. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.calculated_metrics = metrics
    _persist()
    return True


def set_session_source_registry(session_id: str, registry: dict) -> bool:
    """Store unified source registry. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.source_registry = registry
    _persist()
    return True


def set_session_verification_results(session_id: str, results: dict) -> bool:
    """Store cross-source verification results. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.verification_results = results
    _persist()
    return True


def set_session_executive_summary(session_id: str, summary: dict) -> bool:
    """Store executive summary. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.executive_summary = summary
    _persist()
    return True


def set_session_market_data(session_id: str, market_data: dict) -> bool:
    """Store market data. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.market_data = market_data
    _persist()
    return True


def set_session_valuation_metrics(session_id: str, valuation: dict) -> bool:
    """Store valuation metrics. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.valuation_metrics = valuation
    _persist()
    return True


def set_session_error(session_id: str, error_msg: str) -> bool:
    """Set error on session. Returns True if session found."""
    _ensure_loaded()
    session = _sessions.get(session_id)
    if session is None:
        return False
    session.set_error(error_msg)
    _persist()
    return True


def get_active_sessions_for_company(company: str) -> list[ResearchSession]:
    """Return all active (non-cancelled) sessions for a given company."""
    _ensure_loaded()
    return [
        s
        for s in _sessions.values()
        if s.company.lower() == company.lower() and s.status in _ACTIVE_STATUSES
    ]


def clear_all_sessions() -> None:
    """Drop every session — useful for tests."""
    global _loaded
    _sessions.clear()
    _loaded = False
    from lib.persistence import clear_all_persistence
    clear_all_persistence()
