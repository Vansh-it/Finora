"""Financial statement extractor.

Takes SEC CompanyFacts XBRL data and produces normalized financial
statements with evidence for every value. No LLM usage — purely
deterministic extraction from structured SEC data.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from lib.sec_client import get_company_facts
from lib.xbrl_mapper import (
    INCOME_STATEMENT_CONCEPTS,
    BALANCE_SHEET_CONCEPTS,
    CASH_FLOW_CONCEPTS,
    ADDITIONAL_CONCEPTS,
    get_metric_unit,
)


# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class FinancialFact:
    """A single extracted financial fact with full evidence."""
    value: Optional[float] = None
    unit: str = ""
    period: str = ""
    period_start: str = ""
    period_end: str = ""
    form: str = ""
    filing_date: str = ""
    accession_number: str = ""
    xbrl_concept: str = ""
    source: str = "SEC XBRL"
    source_url: str = ""
    verification_status: str = "primary_source"

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        if self.value is not None:
            result["value"] = self.value
        result["unit"] = self.unit
        result["period"] = self.period
        if self.period_start:
            result["period_start"] = self.period_start
        if self.period_end:
            result["period_end"] = self.period_end
        result["form"] = self.form
        result["filing_date"] = self.filing_date
        result["accession_number"] = self.accession_number
        result["xbrl_concept"] = self.xbrl_concept
        result["source"] = self.source
        if self.source_url:
            result["source_url"] = self.source_url
        result["verification_status"] = self.verification_status
        return result


@dataclass
class FinancialStatements:
    """Complete normalized financial statements for a company."""
    company: dict = field(default_factory=dict)
    periods: list[str] = field(default_factory=list)
    income_statement: dict = field(default_factory=dict)
    balance_sheet: dict = field(default_factory=dict)
    cash_flow: dict = field(default_factory=dict)
    additional: dict = field(default_factory=dict)
    metadata: dict = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "periods": self.periods,
            "income_statement": self.income_statement,
            "balance_sheet": self.balance_sheet,
            "cash_flow": self.cash_flow,
            "additional": self.additional,
            "metadata": self.metadata,
        }


# ── Period helpers ────────────────────────────────────────────────────────────
def _is_annual_period(fact: dict) -> bool:
    """Check if a fact represents an annual (12-month) period."""
    start = fact.get("start", "")
    end = fact.get("end", "")
    if not start or not end:
        # Instant facts (no start) are balance sheet — treat as annual
        return True
    try:
        dt_start = datetime.strptime(start, "%Y-%m-%d")
        dt_end = datetime.strptime(end, "%Y-%m-%d")
        days = (dt_end - dt_start).days
        return days >= 300  # ~10+ months
    except (ValueError, TypeError):
        return True


def _is_quarterly_period(fact: dict) -> bool:
    """Check if a fact represents a quarterly (3-month) period."""
    start = fact.get("start", "")
    end = fact.get("end", "")
    if not start or not end:
        return False
    try:
        dt_start = datetime.strptime(start, "%Y-%m-%d")
        dt_end = datetime.strptime(end, "%Y-%m-%d")
        days = (dt_end - dt_start).days
        return 80 <= days <= 100
    except (ValueError, TypeError):
        return False


def _get_fiscal_year(end_date: str) -> Optional[int]:
    """Extract fiscal year from a period end date."""
    try:
        dt = datetime.strptime(end_date, "%Y-%m-%d")
        return dt.year
    except (ValueError, TypeError):
        return None


def _period_label(end_date: str, is_annual: bool) -> str:
    """Generate a period label like 'FY2024' or 'Q3-FY2024'."""
    year = _get_fiscal_year(end_date)
    if year is None:
        return ""
    if is_annual:
        return f"FY{year}"
    try:
        dt = datetime.strptime(end_date, "%Y-%m-%d")
        quarter = (dt.month - 1) // 3 + 1
        return f"Q{quarter}-FY{year}"
    except (ValueError, TypeError):
        return f"FY{year}"


# ── Core extraction ──────────────────────────────────────────────────────────
def _get_unit_facts(units: dict, unit_preference: str) -> list[dict]:
    """Get facts for the preferred unit, with fallbacks."""
    # Try exact match first
    facts = units.get(unit_preference, [])
    if facts:
        return facts
    # Fallbacks for different unit formats
    if unit_preference == "USD/shares":
        return units.get("USD/shares", []) or units.get("shares", []) or units.get("USD", [])
    if unit_preference == "shares":
        return units.get("shares", []) or units.get("USD/shares", []) or units.get("pure", [])
    if unit_preference == "USD":
        return units.get("USD", []) or units.get("USD/shares", [])
    return []


def _select_best_fact_for_year(
    concept_data: dict,
    concept: str,
    unit_preference: str,
    target_year: int,
) -> Optional[dict]:
    """Select the best fact for a specific fiscal year."""
    units = concept_data.get("units", {})
    unit_facts = _get_unit_facts(units, unit_preference)

    candidates: list[dict] = []
    for uf in unit_facts:
        end = uf.get("end", "")
        year = _get_fiscal_year(end)
        if year != target_year:
            continue

        candidates.append({
            "value": uf.get("val"),
            "end": end,
            "start": uf.get("start", ""),
            "filed": uf.get("filed", ""),
            "form": uf.get("form", ""),
            "accession": uf.get("accn", ""),
            "is_annual": _is_annual_period(uf),
            "concept": concept,
        })

    if not candidates:
        return None

    # Prefer annual > 10-K/10-Q > most recent filing > most recent end
    _FORM_PRIORITY = {"10-K": 0, "10-K/A": 0, "10-Q": 1, "10-Q/A": 1}
    def sort_key(c: dict) -> tuple:
        is_ann = 1 if c["is_annual"] else 0
        form_rank = _FORM_PRIORITY.get(c.get("form", ""), 2)
        return (-is_ann, form_rank, c.get("filed", ""), c.get("end", ""))

    candidates.sort(key=sort_key)
    return candidates[0]


def _extract_metric_for_years(
    company_facts: dict,
    concept_aliases: list[str],
    metric_name: str,
    target_years: list[int],
) -> dict[str, Optional[dict]]:
    """Extract a metric for multiple fiscal years.

    Returns a dict mapping period label → fact dict (or None).
    """
    facts_dict = company_facts.get("facts", {})
    us_gaap = facts_dict.get("us-gaap", {})

    unit_preference = "USD"
    if "eps" in metric_name:
        unit_preference = "USD/shares"
    elif "shares" in metric_name:
        unit_preference = "shares"

    results: dict[str, Optional[dict]] = {}

    for year in target_years:
        found = False
        for concept in concept_aliases:
            concept_data = us_gaap.get(concept)
            if concept_data is None:
                continue

            best = _select_best_fact_for_year(concept_data, concept, unit_preference, year)
            if best is None or best["value"] is None:
                continue

            end = best["end"]
            start = best.get("start", "")
            is_annual = best["is_annual"]
            period = _period_label(end, is_annual)

            cik = company_facts.get("cik", "")
            accession = best.get("accession", "")
            acc_clean = accession.replace("-", "")
            source_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/"

            fact = FinancialFact(
                value=best["value"],
                unit=get_metric_unit(metric_name),
                period=period,
                period_start=start,
                period_end=end,
                form=best.get("form", ""),
                filing_date=best.get("filed", ""),
                accession_number=accession,
                xbrl_concept=concept,
                source="SEC XBRL",
                source_url=source_url,
                verification_status="primary_source",
            )
            results[period] = fact.to_dict()
            found = True
            break

        if not found:
            # Try to label the year even if no data
            period = f"FY{year}"
            results[period] = None

    return results


def _extract_metric_latest(
    company_facts: dict,
    concept_aliases: list[str],
    metric_name: str,
) -> Optional[dict]:
    """Extract the latest available value for a metric."""
    facts_dict = company_facts.get("facts", {})
    us_gaap = facts_dict.get("us-gaap", {})

    unit_preference = "USD"
    if "eps" in metric_name:
        unit_preference = "USD/shares"
    elif "shares" in metric_name:
        unit_preference = "shares"

    all_candidates: list[dict] = []

    for concept in concept_aliases:
        concept_data = us_gaap.get(concept)
        if concept_data is None:
            continue

        units = concept_data.get("units", {})
        unit_facts = _get_unit_facts(units, unit_preference)

        for uf in unit_facts:
            end = uf.get("end", "")
            all_candidates.append({
                "value": uf.get("val"),
                "end": end,
                "start": uf.get("start", ""),
                "filed": uf.get("filed", ""),
                "form": uf.get("form", ""),
                "accession": uf.get("accn", ""),
                "is_annual": _is_annual_period(uf),
                "concept": concept,
            })

    if not all_candidates:
        return None

    # Prefer annual > 10-K/10-Q > most recent filing > most recent end
    # Uses reverse=True with negated form_rank so that 10-K (rank 0 → -0) > 10-Q (rank 1 → -1) > 8-K/other (rank 2 → -2).
    _FORM_PRIORITY = {"10-K": 0, "10-K/A": 0, "10-Q": 1, "10-Q/A": 1}
    def sort_key(c: dict) -> tuple:
        is_ann = 1 if c["is_annual"] else 0
        form_rank = _FORM_PRIORITY.get(c.get("form", ""), 2)
        return (is_ann, -form_rank, c.get("filed", ""), c.get("end", ""))

    all_candidates.sort(key=sort_key, reverse=True)
    best = all_candidates[0]

    end = best["end"]
    start = best.get("start", "")
    is_annual = best["is_annual"]
    period = _period_label(end, is_annual)

    cik = company_facts.get("cik", "")
    accession = best.get("accession", "")
    acc_clean = accession.replace("-", "")
    source_url = f"https://www.sec.gov/Archives/edgar/data/{cik}/{acc_clean}/"

    return FinancialFact(
        value=best["value"],
        unit=get_metric_unit(metric_name),
        period=period,
        period_start=start,
        period_end=end,
        form=best.get("form", ""),
        filing_date=best.get("filed", ""),
        accession_number=accession,
        xbrl_concept=best["concept"],
        source="SEC XBRL",
        source_url=source_url,
        verification_status="primary_source",
    ).to_dict()


def _detect_latest_annual_years(
    company_facts: dict,
    concepts_map: dict[str, list[str]],
    n_years: int = 3,
) -> list[int]:
    """Detect the N most recent annual fiscal years from CompanyFacts.

    Scans a sample of key concepts to find which fiscal years have
    annual 10-K data available. Returns sorted list of recent years.
    """
    us_gaap = company_facts.get("facts", {}).get("us-gaap", {})
    year_counts: dict[int, int] = {}

    # Sample a few key concepts to detect available years
    sample_concepts = [
        "RevenueFromContractWithCustomerExcludingAssessedTax",
        "Revenues",
        "NetIncomeLoss",
        "Assets",
        "StockholdersEquity",
        "CashAndCashEquivalentsAtCarryingValue",
    ]

    for concept in sample_concepts:
        concept_data = us_gaap.get(concept)
        if concept_data is None:
            continue
        units = concept_data.get("units", {})
        for unit_facts in units.values():
            for uf in unit_facts:
                end = uf.get("end", "")
                form = uf.get("form", "")
                if not end:
                    continue
                # Only count 10-K annual facts
                if form not in ("10-K", "10-K/A"):
                    continue
                year = _get_fiscal_year(end)
                if year is None:
                    continue
                # Verify it's actually annual (> 300 days)
                start = uf.get("start", "")
                if start:
                    try:
                        dt_s = datetime.strptime(start, "%Y-%m-%d")
                        dt_e = datetime.strptime(end, "%Y-%m-%d")
                        if (dt_e - dt_s).days < 300:
                            continue
                    except (ValueError, TypeError):
                        pass
                year_counts[year] = year_counts.get(year, 0) + 1

    if not year_counts:
        return []

    # Sort by year descending, pick top N
    sorted_years = sorted(year_counts.keys(), reverse=True)
    return sorted_years[:n_years]


def _extract_all_metrics(
    company_facts: dict,
    concepts_map: dict[str, list[str]],
    target_years: Optional[list[int]] = None,
) -> dict[str, Any]:
    """Extract all metrics for a statement type.

    For specified mode (target_years given): returns {metric: {period: fact_dict}}
    For latest mode: returns {metric: {period: fact_dict}} with top 3 annual periods.
    """
    results: dict[str, Any] = {}

    # In latest mode, detect the most recent annual years for growth support
    if target_years is None:
        target_years = _detect_latest_annual_years(company_facts, concepts_map, n_years=3)

    for metric, aliases in concepts_map.items():
        if target_years:
            results[metric] = _extract_metric_for_years(
                company_facts, aliases, metric, target_years
            )
        else:
            # Fallback: extract only latest
            results[metric] = _extract_metric_latest(
                company_facts, aliases, metric
            )

    return results


# ── Main extraction function ─────────────────────────────────────────────────
def extract_financials(
    cik: str,
    company_name: str = "",
    ticker: str = "",
    period_mode: str = "latest",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> FinancialStatements:
    """Extract normalized financial statements from SEC CompanyFacts.

    Parameters
    ----------
    cik : str
        10-digit SEC CIK.
    company_name : str
        Official company name.
    ticker : str
        Stock ticker.
    period_mode : str
        "latest" or "specified".
    start_year : int | None
        Start fiscal year.
    end_year : int | None
        End fiscal year.

    Returns
    -------
    FinancialStatements
        Normalized financial data with evidence.
    """
    company_facts = get_company_facts(cik)

    # Determine target years
    target_years: Optional[list[int]] = None
    if period_mode == "specified" and start_year is not None and end_year is not None:
        target_years = list(range(start_year, end_year + 1))

    # Extract all statement types
    income = _extract_all_metrics(company_facts, INCOME_STATEMENT_CONCEPTS, target_years)
    balance = _extract_all_metrics(company_facts, BALANCE_SHEET_CONCEPTS, target_years)
    cash = _extract_all_metrics(company_facts, CASH_FLOW_CONCEPTS, target_years)
    additional = _extract_all_metrics(company_facts, ADDITIONAL_CONCEPTS, target_years)

    # Collect all periods found
    periods: set[str] = set()
    for stmt in [income, balance, cash, additional]:
        for metric, data in stmt.items():
            if data is None:
                continue
            if isinstance(data, dict):
                # Check if it's a single fact dict or a period-keyed dict
                if "period" in data:
                    # Single fact (legacy latest mode)
                    periods.add(data["period"])
                else:
                    # Period-keyed dict (multi-period or specified mode)
                    for period_key, fact in data.items():
                        if fact is not None and isinstance(fact, dict) and "period" in fact:
                            periods.add(fact["period"])

    # Count metrics extracted
    extracted_count = 0
    for stmt in [income, balance, cash, additional]:
        for metric, data in stmt.items():
            if data is None:
                continue
            if isinstance(data, dict):
                if "period" in data:
                    extracted_count += 1
                else:
                    extracted_count += sum(1 for f in data.values() if f is not None)

    metadata: dict[str, Any] = {
        "extraction_source": "SEC XBRL CompanyFacts",
        "cik": cik,
        "total_metrics_attempted": (
            len(INCOME_STATEMENT_CONCEPTS)
            + len(BALANCE_SHEET_CONCEPTS)
            + len(CASH_FLOW_CONCEPTS)
            + len(ADDITIONAL_CONCEPTS)
        ),
        "metrics_extracted": extracted_count,
    }

    # Only include annual periods (FY YYYY) — exclude quarterly (Q1-FY, Q2-FY, etc.)
    # Quarterly facts leak in when a concept only has quarterly data for a year.
    # We only want annual periods for consistent metric calculation.
    annual_periods = sorted(
        [p for p in periods if p.startswith("FY") and "Q" not in p],
        key=lambda p: int(p.replace("FY", ""))
    )
    sorted_periods = annual_periods

    return FinancialStatements(
        company={
            "name": company_name,
            "ticker": ticker,
            "cik": cik,
        },
        periods=sorted_periods,
        income_statement=income,
        balance_sheet=balance,
        cash_flow=cash,
        additional=additional,
        metadata=metadata,
    )
