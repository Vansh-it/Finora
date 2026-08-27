"""Filing retriever.

Receives a company CIK and period parameters, then selects the
relevant SEC filings (10-K, 10-Q) for that company and period.

Output is a structured document registry. No financial extraction happens here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from lib.sec_client import get_company_submissions


# ── Data classes ──────────────────────────────────────────────────────────────
@dataclass
class Document:
    """A single SEC filing document."""
    document_id: str = ""
    form: str = ""
    filing_date: str = ""
    report_period: str = ""
    accession_number: str = ""
    primary_document: str = ""
    source: str = "SEC EDGAR"
    source_url: str = ""
    status: str = "available"

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_id": self.document_id,
            "form": self.form,
            "filing_date": self.filing_date,
            "report_period": self.report_period,
            "accession_number": self.accession_number,
            "primary_document": self.primary_document,
            "source": self.source,
            "source_url": self.source_url,
            "status": self.status,
        }


@dataclass
class DocumentRegistry:
    """Structured registry of SEC documents for a research session."""
    company: dict = field(default_factory=dict)
    period: dict = field(default_factory=dict)
    documents: list[Document] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "company": self.company,
            "period": self.period,
            "documents": [d.to_dict() for d in self.documents],
        }


# ── Filing type definitions ──────────────────────────────────────────────────
_ANNUAL_FORMS = {"10-K", "10-K/A"}
_QUARTERLY_FORMS = {"10-Q", "10-Q/A"}
_RELEVANT_FORMS = _ANNUAL_FORMS | _QUARTERLY_FORMS


def _parse_date(date_str: str) -> Optional[datetime]:
    """Parse a date string in common SEC formats."""
    for fmt in ("%Y-%m-%d", "%Y%m%d"):
        try:
            return datetime.strptime(date_str, fmt)
        except (ValueError, TypeError):
            continue
    return None


def _extract_report_year(filing: dict) -> Optional[int]:
    """Extract the fiscal year from a filing's report date or filing date."""
    # Try reportPeriodOfCurrentDocument first
    report_date = filing.get("reportPeriodOfCurrentDocument", "")
    if report_date:
        dt = _parse_date(report_date)
        if dt:
            return dt.year

    # Fall back to filing date
    filing_date = filing.get("filingDate", "")
    if filing_date:
        dt = _parse_date(filing_date)
        if dt:
            return dt.year

    return None


def _build_accession_url(cik: str, accession_number: str) -> str:
    """Build the SEC EDGAR filing URL from accession number."""
    acc_clean = accession_number.replace("-", "").replace(" ", "")
    cik_clean = cik.lstrip("0")
    return f"https://www.sec.gov/Archives/edgar/data/{cik_clean}/{acc_clean}/"


def _make_document_id(index: int) -> str:
    """Generate a sequential document ID."""
    return f"sec_{str(index).zfill(3)}"


def retrieve_filings(
    cik: str,
    company_name: str,
    ticker: str,
    period_mode: str = "latest",
    start_year: Optional[int] = None,
    end_year: Optional[int] = None,
) -> DocumentRegistry:
    """Retrieve relevant SEC filings for a company and period.

    Parameters
    ----------
    cik : str
        10-digit SEC CIK.
    company_name : str
        Official company name.
    ticker : str
        Stock ticker symbol.
    period_mode : str
        "latest" or "specified".
    start_year : int | None
        Start fiscal year (for specified mode).
    end_year : int | None
        End fiscal year (for specified mode).

    Returns
    -------
    DocumentRegistry
        Registry with selected documents.

    Raises
    ------
    ValueError
        If no relevant filings are found.
    RuntimeError
        If SEC cannot be reached.
    """
    # Fetch submissions
    submissions = get_company_submissions(cik)

    # Extract the recent filings array
    filings_data = submissions.get("filings", {}).get("recent", [])
    if not filings_data:
        raise ValueError(
            f"No filing data found for CIK {cik} ({company_name})."
        )

    # Convert to list of dicts
    forms = filings_data.get("form", [])
    filing_dates = filings_data.get("filingDate", [])
    accession_numbers = filings_data.get("accessionNumber", [])
    primary_docs = filings_data.get("primaryDocument", [])
    report_periods = filings_data.get("reportPeriodOfCurrentDocument", [])

    all_filings: list[dict] = []
    for i in range(len(forms)):
        form = forms[i] if i < len(forms) else ""
        if form not in _RELEVANT_FORMS:
            continue
        all_filings.append({
            "form": form,
            "filing_date": filing_dates[i] if i < len(filing_dates) else "",
            "accession_number": accession_numbers[i] if i < len(accession_numbers) else "",
            "primary_document": primary_docs[i] if i < len(primary_docs) else "",
            "reportPeriodOfCurrentDocument": report_periods[i] if i < len(report_periods) else "",
        })

    if not all_filings:
        raise ValueError(
            f"No 10-K or 10-Q filings found for {company_name} (CIK: {cik})."
        )

    # Select relevant filings based on period mode
    if period_mode == "latest":
        selected = _select_latest(all_filings)
    else:
        selected = _select_specified(all_filings, start_year, end_year)

    if not selected:
        period_desc = (
            f"latest available"
            if period_mode == "latest"
            else f"FY{start_year}–FY{end_year}" if start_year != end_year
            else f"FY{start_year}"
        )
        raise ValueError(
            f"No relevant filings found for {company_name} for period {period_desc}."
        )

    # Build registry
    documents: list[Document] = []
    for i, filing in enumerate(selected, 1):
        acc_url = _build_accession_url(cik, filing["accession_number"])
        doc = Document(
            document_id=_make_document_id(i),
            form=filing["form"],
            filing_date=filing["filing_date"],
            report_period=filing.get("reportPeriodOfCurrentDocument", ""),
            accession_number=filing["accession_number"],
            primary_document=filing["primary_document"],
            source="SEC EDGAR",
            source_url=acc_url,
            status="available",
        )
        documents.append(doc)

    return DocumentRegistry(
        company={
            "name": company_name,
            "ticker": ticker,
            "cik": cik,
        },
        period={
            "mode": period_mode,
            "start_year": start_year,
            "end_year": end_year,
        },
        documents=documents,
    )


def _select_latest(filings: list[dict]) -> list[dict]:
    """Select the latest 10-K and latest 10-Q (if newer than the 10-K)."""
    latest_10k: Optional[dict] = None
    latest_10q: Optional[dict] = None

    for filing in filings:
        form = filing["form"]
        filing_date = filing["filing_date"]

        if form in _ANNUAL_FORMS:
            if latest_10k is None or filing_date > latest_10k["filing_date"]:
                latest_10k = filing

        elif form in _QUARTERLY_FORMS:
            if latest_10q is None or filing_date > latest_10q["filing_date"]:
                latest_10q = filing

    result: list[dict] = []
    if latest_10k:
        result.append(latest_10k)
    if latest_10q and latest_10k:
        # Only include 10-Q if it's newer than the 10-K
        if latest_10q["filing_date"] > latest_10k["filing_date"]:
            result.append(latest_10q)
    elif latest_10q:
        result.append(latest_10q)

    return result


def _select_specified(
    filings: list[dict],
    start_year: Optional[int],
    end_year: Optional[int],
) -> list[dict]:
    """Select filings relevant to the specified year range."""
    selected: list[dict] = []
    seen_10k_years: set[int] = set()
    seen_10q_periods: set[str] = set()

    for filing in filings:
        filing_date = filing["filing_date"]
        dt = _parse_date(filing_date)
        if dt is None:
            continue

        filing_year = dt.year
        form = filing["form"]

        # For specified mode, check if filing falls within range
        # We look at the filing year, not the report period year,
        # since the filing year is when the document was actually submitted.
        # But we also want filings whose report period falls in range.

        report_period = filing.get("reportPeriodOfCurrentDocument", "")
        report_dt = _parse_date(report_period)
        report_year = report_dt.year if report_dt else filing_year

        in_range = False
        if start_year is not None and end_year is not None:
            in_range = (start_year <= report_year <= end_year) or (start_year <= filing_year <= end_year)
        elif start_year is not None:
            in_range = report_year >= start_year or filing_year >= start_year
        elif end_year is not None:
            in_range = report_year <= end_year or filing_year <= end_year

        if not in_range:
            continue

        if form in _ANNUAL_FORMS:
            year_key = report_year
            if year_key not in seen_10k_years:
                seen_10k_years.add(year_key)
                selected.append(filing)

        elif form in _QUARTERLY_FORMS:
            # Use report period to avoid duplicate quarters
            period_key = report_period[:7] if report_period else filing_date[:7]
            if period_key not in seen_10q_periods:
                seen_10q_periods.add(period_key)
                selected.append(filing)

    # Sort by filing date (newest first)
    selected.sort(key=lambda f: f.get("filing_date", ""), reverse=True)
    return selected
