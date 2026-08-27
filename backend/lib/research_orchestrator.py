"""Research orchestrator.

Receives a validated intent dict (from the intent classifier) and produces
a structured research plan.  This phase does NOT perform any web search,
Tavily, Firecrawl calls, or financial metric calculations — it only
builds the plan and requests user permission.

Output is always validated JSON.  Never returns markdown.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


# ── Source catalog ────────────────────────────────────────────────────────────
# Maps objective keywords → list of required data sources.
_SOURCE_MAP: dict[str, list[str]] = {
    "financial": [
        "Annual Report",
        "Quarterly Reports",
        "Earnings Releases",
    ],
    "revenue": [
        "Annual Report",
        "Quarterly Reports",
        "10-K Filing",
    ],
    "stock": [
        "10-K Filing",
        "Earnings Releases",
        "SEC EDGAR Filings",
    ],
    "growth": [
        "Annual Report",
        "Quarterly Reports",
        "Industry Analyst Reports",
    ],
    "overview": [
        "Annual Report",
        "Company Website",
        "Press Releases",
    ],
}

_DEFAULT_SOURCES: list[str] = [
    "Annual Report",
    "Quarterly Reports",
    "Earnings Releases",
]


def _pick_sources(objective: str) -> list[str]:
    """Select required sources based on keywords in the objective."""
    lower = objective.lower()
    for keyword, sources in _SOURCE_MAP.items():
        if keyword in lower:
            return list(sources)  # return a copy
    return list(_DEFAULT_SOURCES)


# ── Period normalisation ─────────────────────────────────────────────────────
def _format_period(
    start_year: Optional[int],
    end_year: Optional[int],
    period_mode: str = "latest",
) -> str:
    """Normalise start/end years into a human-readable period string.

    Examples:
        (2024, 2025, "specified")  → "FY2024–FY2025"
        (2023, None, "specified")  → "FY2023"
        (None, 2025, "specified")  → "FY2025"
        (None, None, "latest")    → "Latest available financial reporting data"
        (None, None, "specified") → "Unspecified Period"
    """
    if start_year and end_year:
        if start_year == end_year:
            return f"FY{start_year}"
        return f"FY{start_year}–FY{end_year}"
    if start_year:
        return f"FY{start_year}"
    if end_year:
        return f"FY{end_year}"
    if period_mode == "latest":
        return "Latest available financial reporting data"
    return "Unspecified Period"


def _objective_title(objective: str) -> str:
    """Turn a freeform objective into a title-cased plan title."""
    if not objective or not objective.strip():
        return "General Research"
    return objective.strip().title()


# ── Data class ───────────────────────────────────────────────────────────────
@dataclass
class ResearchPlan:
    status: str = "awaiting_permission"
    company: str = ""
    period: str = "Unspecified Period"
    period_mode: str = "latest"
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    objective: str = "General Research"
    required_sources: list[str] = field(default_factory=list)
    next_action: str = "request_permission"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "company": self.company,
            "period": self.period,
            "period_mode": self.period_mode,
            "start_year": self.start_year,
            "end_year": self.end_year,
            "objective": self.objective,
            "required_sources": self.required_sources,
            "next_action": self.next_action,
        }


# ── Core orchestrator ────────────────────────────────────────────────────────
def create_research_plan(intent: dict[str, Any]) -> ResearchPlan:
    """Build a research plan from a classified intent dict.

    Parameters
    ----------
    intent : dict
        Must contain ``"company"`` (non-empty string).
        May contain ``"period_mode"`` ("specified" or "latest"),
        ``"start_year"``, ``"end_year"``, ``"objective"``.

    Returns
    -------
    ResearchPlan
        A validated plan with status ``awaiting_permission``.

    Raises
    ------
    ValueError
        If company is missing or empty.
    """
    company = intent.get("company")
    if not isinstance(company, str) or not company.strip():
        raise ValueError("Intent must include a non-empty 'company' field")
    company = company.strip()

    period_mode = intent.get("period_mode", "latest")
    if period_mode not in ("specified", "latest"):
        period_mode = "latest"

    start_year = intent.get("start_year")
    end_year = intent.get("end_year")
    if start_year is not None:
        start_year = int(start_year)
    if end_year is not None:
        end_year = int(end_year)

    objective = str(intent.get("objective", "")).strip()

    return ResearchPlan(
        company=company,
        period=_format_period(start_year, end_year, period_mode),
        period_mode=period_mode,
        start_year=start_year,
        end_year=end_year,
        objective=_objective_title(objective),
        required_sources=_pick_sources(objective),
    )
