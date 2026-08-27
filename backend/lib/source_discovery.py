"""Source discovery service.

Uses Tavily to discover authoritative public financial sources
for a resolved company. Combines SEC filing registry with
Tavily-discovered company sources into a unified trusted registry.

Tavily is a complementary layer — not a replacement for SEC data.
"""

from __future__ import annotations

import re
from typing import Any, Optional
from urllib.parse import urlparse

from lib.tavily_client import tavily_search


# ── Trust tiers ───────────────────────────────────────────────────────────────
TRUST_TIER_1 = 1  # Highest: SEC, official IR, annual reports, earnings
TRUST_TIER_2 = 2  # Acceptable: exchange pages, authoritative first-party
TRUST_TIER_3 = 3  # Low: blogs, social, SEO aggregators
TRUST_TIER_EXCLUDE = 0  # Excluded entirely

# ── Domains to always reject (Tier 3 → exclude) ─────────────────────────────
EXCLUDED_DOMAINS = {
    "linkedin.com",
    "reddit.com",
    "medium.com",
    "twitter.com",
    "x.com",
    "facebook.com",
    "instagram.com",
    "tiktok.com",
    "youtube.com",
    "quora.com",
    "pinterest.com",
    "threads.net",
    "mastodon.social",
}

# ── Patterns that indicate low-quality financial content ──────────────────────
EXCLUDED_URL_PATTERNS = [
    r"linkedin\.com/posts",
    r"reddit\.com/r/",
    r"medium\.com/@",
    r"seekingalpha\.com/user/",
    r"investorshub\.com",
    r"stocktwits\.com",
    r"wallstreetbets",
    r"motleyfool\.com/stock-advisor",
]

# ── Patterns that indicate official / high-quality sources ────────────────────
OFFICIAL_DOMAIN_PATTERNS = [
    r"investor\.",          # investor.microsoft.com
    r"investors\.",         # investors.apple.com
    r"ir\.",                # ir.amazon.com
    r"sec\.gov",
    r"sec\.gov/Archives",
    r"/investor",
    r"/investors",
    r"/investor-relations",
    r"/financials",
    r"/earnings",
    r"/annual-report",
    r"/quarterly-results",
]

# ── Content type keywords for source classification ──────────────────────────
SOURCE_TYPE_KEYWORDS = {
    "annual_report": ["annual report", "10-k", "annual review", "fiscal year"],
    "quarterly_earnings": ["quarterly", "10-q", "earnings release", "earnings report",
                           "quarterly results", "financial results"],
    "investor_presentation": ["investor presentation", "investor deck", "investor day",
                               "earnings call", "slide deck"],
    "press_release": ["press release", "news release", "announces"],
    "financial_statements": ["financial statement", "balance sheet", "income statement",
                              "cash flow statement"],
}


# ── Source data model ─────────────────────────────────────────────────────────
def _make_source(
    source_id: str,
    source_type: str,
    authority: str,
    provider: str,
    url: str,
    title: str,
    period: str,
    trust_tier: int,
    status: str = "verified",
    **extra: Any,
) -> dict:
    """Create a standardized source dict."""
    source = {
        "source_id": source_id,
        "source_type": source_type,
        "authority": authority,
        "provider": provider,
        "url": url,
        "title": title,
        "period": period,
        "trust_tier": trust_tier,
        "status": status,
    }
    source.update(extra)
    return source


# ── URL normalization for deduplication ──────────────────────────────────────
def _normalize_url(url: str) -> str:
    """Normalize a URL for deduplication."""
    url = url.rstrip("/").lower()
    # Remove tracking params
    parsed = urlparse(url)
    # Remove common tracking query params
    clean_qs = "&".join(
        q for q in (parsed.query or "").split("&")
        if not q.startswith(("utm_", "ref=", "source=", "fbclid=", "gclid="))
    )
    if clean_qs:
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}?{clean_qs}"
    return f"{parsed.scheme}://{parsed.netloc}{parsed.path}"


def _url_fingerprint(url: str) -> str:
    """Generate a fingerprint for deduplication."""
    normalized = _normalize_url(url)
    # Strip www prefix
    normalized = re.sub(r"://www\.", "://", normalized)
    return normalized


# ── Domain analysis ──────────────────────────────────────────────────────────
def _get_domain(url: str) -> str:
    """Extract the root domain from a URL."""
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    # Strip www prefix
    if domain.startswith("www."):
        domain = domain[4:]
    return domain


def _is_excluded_domain(domain: str) -> bool:
    """Check if a domain is in the exclusion list."""
    for excluded in EXCLUDED_DOMAINS:
        if domain == excluded or domain.endswith("." + excluded):
            return True
    return False


def _is_excluded_url(url: str) -> bool:
    """Check if a URL matches any exclusion pattern."""
    for pattern in EXCLUDED_URL_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True
    return False


def _is_official_domain(domain: str, url: str, company_name: str) -> bool:
    """Heuristically detect official company domains."""
    # Check SEC
    if "sec.gov" in domain:
        return True

    # Check URL patterns
    for pattern in OFFICIAL_DOMAIN_PATTERNS:
        if re.search(pattern, url, re.IGNORECASE):
            return True

    # Check if domain contains company name parts
    company_parts = company_name.lower().replace("inc.", "").replace("corp.", "")\
        .replace("corporation", "").replace("company", "").replace("inc", "")\
        .replace("corp", "").strip().split()

    for part in company_parts:
        if len(part) >= 3 and part in domain:
            return True

    return False


def _classify_source_type(title: str, url: str) -> str:
    """Classify a source into a type based on title/URL."""
    text = f"{title} {url}".lower()
    for source_type, keywords in SOURCE_TYPE_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return source_type
    return "general_financial"


def _determine_trust_tier(
    domain: str,
    url: str,
    title: str,
    company_name: str,
) -> int:
    """Determine the trust tier for a source."""
    # Excluded domains
    if _is_excluded_domain(domain):
        return TRUST_TIER_EXCLUDE

    # Excluded URL patterns
    if _is_excluded_url(url):
        return TRUST_TIER_EXCLUDE

    # SEC is Tier 1
    if "sec.gov" in domain:
        return TRUST_TIER_1

    # Official company domains are Tier 1
    if _is_official_domain(domain, url, company_name):
        return TRUST_TIER_1

    # Check for trusted financial data domains
    trusted_tier2_domains = {
        "macrotrends.net",
        "wisesheets.io",
        "companiesmarketcap.com",
        "stockanalysis.com",
        "gurufocus.com",
        "simplywall.st",
        "finbox.com",
    }
    for trusted in trusted_tier2_domains:
        if trusted in domain:
            return TRUST_TIER_2

    # Default: Tier 3 (low quality, will be filtered out)
    return TRUST_TIER_3


# ── Query generation ──────────────────────────────────────────────────────────
def _build_search_queries(
    company_name: str,
    ticker: str,
    period_mode: str,
    start_year: int | None,
    end_year: int | None,
) -> list[str]:
    """Generate efficient Tavily search queries.

    Uses minimal queries to preserve free-tier credits.
    Returns 2-3 well-targeted queries instead of many broad ones.
    """
    base = company_name.replace("Corporation", "").replace("Inc.", "").replace("Inc", "").strip()
    queries = []

    if period_mode == "latest":
        # Query 1: Investor relations + annual report
        queries.append(f"{base} investor relations annual report")
        # Query 2: Latest quarterly earnings
        queries.append(f"{base} latest quarterly earnings results")
    else:
        # Specified period
        years = []
        if start_year:
            years.append(start_year)
        if end_year and end_year != start_year:
            years.append(end_year)
        year_str = " ".join(str(y) for y in years)

        queries.append(f"{base} {year_str} annual report investor relations")
        queries.append(f"{base} {year_str} quarterly earnings results")

    return queries


# ── Main discovery function ──────────────────────────────────────────────────
def discover_sources(
    company_name: str,
    ticker: str,
    period_mode: str = "latest",
    start_year: int | None = None,
    end_year: int | None = None,
    sec_registry: Optional[dict] = None,
) -> dict:
    """Discover authoritative financial sources for a company.

    Combines SEC filing registry with Tavily-discovered company sources
    into a unified trusted source registry.

    Parameters
    ----------
    company_name : str
        Resolved company name (e.g. "Microsoft Corporation").
    ticker : str
        Company ticker (e.g. "MSFT").
    period_mode : str
        "latest" or "specified".
    start_year, end_year : int | None
        Fiscal year range (for specified mode).
    sec_registry : dict | None
        Existing SEC document registry (from filing_retriever).

    Returns
    -------
    dict
        Unified source registry with SEC + Tavily sources.
    """
    sources: list[dict] = []
    seen_fingerprints: set[str] = set()
    source_counter = 0

    # ── Step 1: Incorporate existing SEC sources ──────────────────────────
    if sec_registry and "documents" in sec_registry:
        for doc in sec_registry["documents"]:
            source_counter += 1
            url = doc.get("source_url", "")
            fp = _url_fingerprint(url)
            if fp and fp not in seen_fingerprints:
                seen_fingerprints.add(fp)
                period = _determine_period_label(doc, period_mode, start_year, end_year)
                sources.append(_make_source(
                    source_id=f"sec_{source_counter:03d}",
                    source_type=doc.get("form", "filing").lower(),
                    authority="regulatory",
                    provider="SEC EDGAR",
                    url=url,
                    title=f"{doc.get('form', 'Filing')} - {company_name}",
                    period=period,
                    trust_tier=TRUST_TIER_1,
                    accession_number=doc.get("accession_number", ""),
                    filing_date=doc.get("filing_date", ""),
                ))

    # ── Step 2: Tavily discovery ──────────────────────────────────────────
    queries = _build_search_queries(company_name, ticker, period_mode, start_year, end_year)

    for query in queries:
        try:
            result = tavily_search(query, max_results=5, search_depth="basic")
        except (RuntimeError, ValueError):
            # Tavily failure must NOT destroy a valid SEC-based operation
            continue

        for item in result.get("results", []):
            url = item.get("url", "")
            title = item.get("title", "")
            domain = _get_domain(url)

            # Determine trust tier
            trust = _determine_trust_tier(domain, url, title, company_name)

            # Skip excluded sources
            if trust == TRUST_TIER_EXCLUDE:
                continue

            # Skip low-quality (Tier 3)
            if trust >= TRUST_TIER_3:
                continue

            # Deduplication
            fp = _url_fingerprint(url)
            if fp in seen_fingerprints:
                continue
            seen_fingerprints.add(fp)

            source_counter += 1
            source_type = _classify_source_type(title, url)
            authority = "company_official" if trust == TRUST_TIER_1 else "third_party"
            provider = _infer_provider(domain, title)

            period = _infer_period_from_title(title, period_mode, start_year, end_year)

            sources.append(_make_source(
                source_id=f"tavily_{source_counter:03d}",
                source_type=source_type,
                authority=authority,
                provider=provider,
                url=url,
                title=title,
                period=period,
                trust_tier=trust,
                domain=domain,
            ))

    # ── Step 3: Build final registry ──────────────────────────────────────
    period_label = _build_period_label(period_mode, start_year, end_year)

    return {
        "company": {
            "name": company_name,
            "ticker": ticker,
        },
        "period": {
            "mode": period_mode,
            "start_year": start_year,
            "end_year": end_year,
            "label": period_label,
        },
        "sources": sources,
        "metadata": {
            "total_sources": len(sources),
            "sec_sources": sum(1 for s in sources if s["authority"] == "regulatory"),
            "company_sources": sum(1 for s in sources if s["authority"] == "company_official"),
            "third_party_sources": sum(1 for s in sources if s["authority"] == "third_party"),
            "queries_used": len(queries),
            "tavily_searches": len(queries),
        },
    }


# ── Helpers ──────────────────────────────────────────────────────────────────
def _determine_period_label(
    doc: dict,
    period_mode: str,
    start_year: int | None,
    end_year: int | None,
) -> str:
    """Determine period label for a document."""
    if period_mode == "latest":
        return "Latest"
    if start_year and end_year:
        if start_year == end_year:
            return f"FY{start_year}"
        return f"FY{start_year}–FY{end_year}"
    return "Unspecified"


def _build_period_label(
    period_mode: str,
    start_year: int | None,
    end_year: int | None,
) -> str:
    """Build a human-readable period label."""
    if period_mode == "latest":
        return "Latest available"
    if start_year and end_year:
        if start_year == end_year:
            return f"FY{start_year}"
        return f"FY{start_year}–FY{end_year}"
    return "Unspecified"


def _infer_provider(domain: str, title: str) -> str:
    """Infer a human-readable provider name from domain/title."""
    if "sec.gov" in domain:
        return "SEC EDGAR"
    # Remove www and common TLDs for display
    name = domain.split(".")[0].replace("www.", "")
    name = name.replace("-", " ").replace("_", " ").title()
    return name or domain


def _infer_period_from_title(
    title: str,
    period_mode: str,
    start_year: int | None,
    end_year: int | None,
) -> str:
    """Try to infer period from title text."""
    # Look for FY patterns
    fy_match = re.search(r"FY\s*(\d{4})", title)
    if fy_match:
        year = int(fy_match.group(1))
        return f"FY{year}"

    # Look for standalone year
    year_match = re.search(r"\b(20[2-3]\d)\b", title)
    if year_match:
        return f"FY{year_match.group(1)}"

    return _build_period_label(period_mode, start_year, end_year)
