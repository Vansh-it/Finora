"""Company resolver.

Resolves a company name or ticker symbol to a normalized company object
with name, ticker, CIK, and exchange.

Uses the official SEC ticker-to-CIK mapping as the primary source.
Falls back to substring matching for partial company names.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from lib.sec_client import get_ticker_mapping


# ── Data class ────────────────────────────────────────────────────────────────
@dataclass
class Company:
    """Normalized company object."""
    name: str = ""
    ticker: str = ""
    cik: str = ""
    exchange: str = ""
    status: str = "resolved"

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "ticker": self.ticker,
            "cik": self.cik,
            "exchange": self.exchange,
            "status": self.status,
        }


# ── Alias map (common names → official names) ────────────────────────────────
_ALIASES: dict[str, str] = {
    "microsoft": "microsoft corporation",
    "apple": "apple inc",
    "nvidia": "nvidia corp",
    "amazon": "amazon com inc",
    "alphabet": "alphabet inc",
    "google": "alphabet inc",
    "meta": "meta platforms inc",
    "facebook": "meta platforms inc",
    "tesla": "tesla inc",
    "netflix": "netflix inc",
    "berkshire": "berkshire hathaway inc",
    "samsung": "samsung electronics co ltd",
    "tencent": "tencent holdings ltd",
    "alibaba": "alibaba group holding ltd",
    "oracle": "oracle corp",
    "salesforce": "salesforce inc",
    "adobe": "adobe inc",
    "intel": "intel corp",
    "amd": "advanced micro devices inc",
    "advanced micro devices": "advanced micro devices inc",
    "cisco": "cisco systems inc",
    "ibm": "international business machines corp",
    "johnson & johnson": "johnson & johnson",
    "jpmorgan": "jpmorgan chase & co",
    "visa": "visa inc",
    "mastercard": "mastercard inc",
    "walmart": "walmart inc",
    "disney": "walt disney co",
    "unitedhealth": "unitedhealth group inc",
    "costco": "costco wholesale corp",
    "nike": "nike inc",
    "uber": "uber technologies inc",
    "airbnb": "airbnb inc",
    "spotify": "spotify technology sa",
    "palantir": "palantir technologies inc",
    "crowdstrike": "crowdstrike holdings inc",
    "snowflake": "snowflake inc",
    "datadog": "datadog inc",
    "cloudflare": "cloudflare inc",
}


def _normalize(text: str) -> str:
    """Lowercase, strip, remove extra whitespace."""
    return re.sub(r"\s+", " ", text.strip().lower())


def _is_ticker(text: str) -> bool:
    """Heuristic: looks like a ticker if 1-5 uppercase alpha chars."""
    return bool(re.match(r"^[A-Za-z]{1,5}$", text.strip()))


def _cik_to_str(cik: int) -> str:
    """Convert numeric CIK to 10-digit zero-padded string."""
    return str(cik).zfill(10)


def _clean_company_name(name: str) -> str:
    """Clean up SEC company name for display."""
    # Remove common suffixes for cleaner display
    return name.strip()


def resolve_company(query: str) -> Company:
    """Resolve a company name or ticker to a normalized Company object.

    Parameters
    ----------
    query : str
        Company name (e.g. "Microsoft", "Microsoft Corporation")
        or ticker symbol (e.g. "MSFT").

    Returns
    -------
    Company
        Resolved company with name, ticker, CIK, exchange.

    Raises
    ------
    ValueError
        If the company cannot be resolved.
    RuntimeError
        If the SEC ticker mapping cannot be fetched.
    """
    if not query or not query.strip():
        raise ValueError("Company query must be a non-empty string")

    query_clean = query.strip()
    is_ticker = _is_ticker(query_clean)

    # Try aliases first for names
    lookup_name = _normalize(query_clean)
    aliased = _ALIASES.get(lookup_name)

    # Fetch the SEC ticker mapping
    try:
        ticker_map = get_ticker_mapping()
    except Exception as exc:
        raise RuntimeError(f"Cannot fetch SEC ticker mapping: {exc}")

    # ticker_map format: {"fields": [...], "data": [[cik, title, ticker, ...], ...]}
    # or sometimes: {"0": {"cik_str": ..., "ticker": ..., "title": ...}, ...}
    companies = _parse_ticker_map(ticker_map)

    # Strategy 1: Exact ticker match
    if is_ticker:
        ticker_upper = query_clean.upper()
        for company in companies:
            if company["ticker"] == ticker_upper:
                return Company(
                    name=company["name"],
                    ticker=company["ticker"],
                    cik=company["cik"],
                    exchange=company.get("exchange", ""),
                    status="resolved",
                )

    # Strategy 2: Exact name match (case-insensitive)
    target_name = aliased if aliased else lookup_name
    best_match: Optional[dict] = None
    best_score = 0

    for company in companies:
        company_lower = _normalize(company["name"])
        # Exact match
        if company_lower == target_name:
            return Company(
                name=company["name"],
                ticker=company["ticker"],
                cik=company["cik"],
                exchange=company.get("exchange", ""),
                status="resolved",
            )
        # Starts-with match (e.g. "microsoft" matches "microsoft corporation")
        if company_lower.startswith(target_name) or target_name.startswith(company_lower):
            score = len(target_name) / max(len(company_lower), 1)
            if score > best_score:
                best_score = score
                best_match = company

    if best_match and best_score > 0.5:
        return Company(
            name=best_match["name"],
            ticker=best_match["ticker"],
            cik=best_match["cik"],
            exchange=best_match.get("exchange", ""),
            status="resolved",
        )

    # Strategy 3: Substring match
    for company in companies:
        company_lower = _normalize(company["name"])
        if target_name in company_lower or company_lower in target_name:
            return Company(
                name=company["name"],
                ticker=company["ticker"],
                cik=company["cik"],
                exchange=company.get("exchange", ""),
                status="resolved",
            )

    raise ValueError(
        f"Could not resolve company: '{query_clean}'. "
        "Try using the exact company name or ticker symbol."
    )


def _parse_ticker_map(data: dict | list) -> list[dict]:
    """Parse SEC ticker mapping into a normalized list of company dicts.

    SEC provides the data in different formats depending on the endpoint.
    Handles both list-of-lists and dict-of-dicts formats.
    """
    companies: list[dict] = []

    if isinstance(data, dict):
        # Format: {"fields": [...], "data": [[...], ...]}
        if "data" in data and "fields" in data:
            fields = data["fields"]
            for row in data["data"]:
                company = {}
                for i, field_name in enumerate(fields):
                    if i < len(row):
                        company[field_name] = row[i]
                companies.append(_normalize_company_dict(company))
        # Format: {"0": {...}, "1": {...}, ...}
        else:
            for key, val in data.items():
                if isinstance(val, dict) and "ticker" in val:
                    companies.append(_normalize_company_dict(val))

    elif isinstance(data, list):
        # Format: [[cik, title, ticker, ...], ...]
        if data and isinstance(data[0], list):
            for row in data:
                if len(row) >= 3:
                    companies.append({
                        "cik": _cik_to_str(row[0]) if isinstance(row[0], int) else str(row[0]),
                        "name": str(row[1]),
                        "ticker": str(row[2]),
                        "exchange": str(row[3]) if len(row) > 3 else "",
                    })
        elif data and isinstance(data[0], dict):
            for item in data:
                companies.append(_normalize_company_dict(item))

    return companies


def _normalize_company_dict(d: dict) -> dict:
    """Normalize a company dict from SEC data to standard keys."""
    cik = d.get("cik_str") or d.get("cik") or d.get("CIK") or ""
    if isinstance(cik, int):
        cik = _cik_to_str(cik)
    elif isinstance(cik, str):
        cik = cik.zfill(10)

    ticker = d.get("ticker") or d.get("Ticker") or ""
    name = d.get("title") or d.get("name") or d.get("Title") or d.get("company_name") or ""

    return {
        "cik": str(cik),
        "name": str(name),
        "ticker": str(ticker),
        "exchange": str(d.get("exchange", "")),
    }
